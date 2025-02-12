"""
評価処理を管理するサービス
"""
import logging
import asyncio
import sys
import json
import traceback
from typing import List, Dict, Any, Optional, Tuple
from .text_analyzer import TextAnalyzer
from ..prompt_template.prompt import EVALUATION_CRITERIA, EVALUATION_PROMPT_TEMPLATE, SYSTEM_PROMPT, get_evaluation_text, identify_target_type
from openai import AsyncAzureOpenAI
from ..models.evaluation_result import EvaluationResult
from ..config import get_settings, CRITERIA_MAPPING
from ..models.evaluation_result import LocationComments, Comment, Position
from ..models.criteria_info import CriteriaInfo
from .openai_service import call_openai_api, parse_openai_response, EvaluationError

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# コンソールハンドラの設定
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

# フォーマッタの設定
formatter = logging.Formatter('''
%(asctime)s - %(name)s - %(levelname)s
%(message)s
''')
console_handler.setFormatter(formatter)

# 既存のハンドラをクリア
logger.handlers.clear()

# ハンドラの追加
logger.addHandler(console_handler)

# 親ロガーからの伝播を防止
logger.propagate = False

settings = get_settings()

class EvaluationService:
    """文書評価サービス"""
    
    def __init__(self):
        """評価サービスの初期化"""
        self.text_analyzer = TextAnalyzer()
        # Azure OpenAI APIクライアントを非同期クライアントとして初期化
        self.client = AsyncAzureOpenAI(
            api_key=settings.OPENAI_API_KEY,
            api_version=settings.OPENAI_API_VERSION,
            base_url=settings.OPENAI_API_BASE_URL,
            timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES
        )
        logger.debug("EvaluationService initialized with Azure OpenAI client")
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # エラー情報の初期化
        self.error_details = {
            "last_error": None,
            "error_count": 0,
            "category_errors": {}
        }

    async def evaluate_document(
        self,
        full_text: str,
        summary: str,
        paragraphs: list[str],
        title: str
    ) -> Dict[str, Any]:
        """
        文書を評価する

        Args:
            full_text (str): 評価対象の文書テキスト全体
            summary (str): サマリー
            paragraphs (list[str]): 段落のリスト
            title (str): タイトル

        Returns:
            Dict[str, Any]: 評価結果を含む辞書
        """
        try:
            self.logger.info("\n=== 文書評価プロセスを開始 ===")
            
            # エラー情報をリセット
            self.error_details = {
                "last_error": None,
                "error_count": 0,
                "category_errors": {}
            }
            
            # 入力値の検証と前処理
            validation_result = self._validate_input(full_text, summary, paragraphs, title)
            if validation_result.get("error"):
                return self._create_error_response(validation_result["error"])

            self.logger.info(f"タイトル: {title}")
            self.logger.debug(f"サマリー: {summary[:100]}...")
            self.logger.debug(f"段落数: {len(paragraphs)}")
            self.logger.debug(f"本文長: {len(full_text)}")

            # 入力値の検証
            if not full_text.strip() or not title.strip():
                self.logger.warning("空の文書またはタイトルが入力されました")
                return {
                    "evaluations": [],
                    "categories": [],
                    "categoryScores": [],
                    "totalScore": 0.0,
                    "totalJudgment": "NG",
                    "error": "空の文書またはタイトルは評価できません"
                }

            if not isinstance(paragraphs, list):
                self.logger.error("入力値の型が不正: paragraphsはリストである必要があります")
                raise ValueError("paragraphsはリスト形式である必要があります")

            # 文書構造の作成
            document_structure = {
                "title": title.strip(),
                "summary": summary.strip() if isinstance(summary, str) else "",
                "story": "\n".join(p.strip() for p in paragraphs if isinstance(p, str) and p.strip()),
                "body": full_text.strip(),
                "structure": {
                    "summary": [summary.strip()] if isinstance(summary, str) and summary.strip() else [],
                    "story": [p.strip() for p in paragraphs if isinstance(p, str) and p.strip()],
                    "relationships": []
                }
            }

            self.logger.debug("\n=== 文書構造の確認 ===")
            self.logger.debug(f"タイトル長: {len(document_structure['title'])}")
            self.logger.debug(f"サマリー長: {len(document_structure['summary'])}")
            self.logger.debug(f"ストーリー長: {len(document_structure['story'])}")
            self.logger.debug(f"本文長: {len(document_structure['body'])}")
            self.logger.debug(f"ストーリー段落数: {len(document_structure['structure']['story'])}")

            # カテゴリを優先順位でソート
            sorted_categories = sorted(
                CRITERIA_MAPPING.items(),
                key=lambda x: x[1].priority
            )

            self.logger.debug("\n=== 評価カテゴリの確認 ===")
            self.logger.debug(f"カテゴリ数: {len(sorted_categories)}")
            for category_id, category_info in sorted_categories:
                self.logger.debug(f"カテゴリ: {category_id}, 優先度: {category_info.priority}")

            # 評価結果の構造を作成
            result = {
                "evaluations": [],
                "categories": [],
                "categoryScores": []
            }

            self.logger.info("\n=== 評価基準ごとの評価を開始 ===")

            for category_id, category_info in sorted_categories:
                self.logger.debug(f"\n▼ カテゴリ評価開始: {category_info.display_name}")
                self.logger.debug(f"優先順位: {category_info.priority}")
                self.logger.debug(f"評価基準: {', '.join(category_info.criteria_ids)}")
                
                try:
                    # 該当箇所の特定と評価の実行
                    locations = await self._evaluate_category(category_id, category_info, document_structure)
                    
                    if locations:
                        self.logger.debug(f"評価結果件数: {len(locations)}")
                
                        # カテゴリ情報を追加
                        category_data = {
                            "id": category_id,
                            "name": category_info.display_name,
                            "priority": category_info.priority
                        }
                        result["categories"].append(category_data)

                        # 評価結果を追加
                        category_evaluations = []
                        
                        self.logger.debug(f"\n--- 評価結果の詳細 ---")
                        for location in locations:
                            for comment in location.comments:
                                evaluation_data = {
                                    "categoryId": category_id,
                                    "criteriaId": comment.criteria_id,
                                    "score": comment.score,
                                    "feedback": comment.content,
                                    "location": location.location
                                }
                                result["evaluations"].append(evaluation_data)
                                category_evaluations.append(evaluation_data)
                                
                                self.logger.debug(f"\n[評価基準: {comment.criteria_id}]")
                                self.logger.debug(f"スコア: {comment.score * 100:.1f}点")
                                self.logger.debug(f"フィードバック: {comment.content}")
                                self.logger.debug(f"評価対象: {location.location}")

                        # カテゴリごとの平均スコアと判定を計算
                        category_score_data = self._calculate_category_score(category_evaluations, category_info)
                        result["categoryScores"].append(category_score_data)
                        
                        self.logger.info(f"\n▼ カテゴリ評価結果")
                        self.logger.info(f"カテゴリ: {category_score_data['categoryName']}")
                        self.logger.info(f"平均スコア: {category_score_data['score']}点")
                        self.logger.info(f"判定: {category_score_data['judgment']}")
                    else:
                        self.logger.warning(f"カテゴリ {category_id} の評価結果が空です")

                except Exception as e:
                    self.error_details["error_count"] += 1
                    self.error_details["category_errors"][category_id] = {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "traceback": traceback.format_exc()
                    }
                    self.logger.error(f"カテゴリ '{category_info.display_name}' の評価中にエラーが発生: {str(e)}")
                    continue

            # 総合評価の計算
            total_score = self.calculate_average_score(result["evaluations"])
            result["totalScore"] = total_score
            result["totalJudgment"] = "OK" if total_score >= 0.8 else "NG"

            self.logger.info("\n=== 評価完了 ===")
            self.logger.info(f"総合スコア: {total_score * 100:.1f}点")
            self.logger.info(f"総合判定: {result['totalJudgment']}")
            self.logger.info(f"評価結果数: {len(result['evaluations'])}")
            self.logger.info(f"カテゴリ数: {len(result['categories'])}")
            self.logger.info(f"カテゴリスコア数: {len(result['categoryScores'])}")

            return result

        except Exception as e:
            error_info = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc(),
                "error_details": self.error_details
            }
            
            self.logger.error("文書評価中に致命的なエラーが発生:")
            self.logger.error(json.dumps(error_info, ensure_ascii=False, indent=2))
            
            return {
                "evaluations": [],
                "categories": [],
                "categoryScores": [],
                "totalScore": 0.0,
                "totalJudgment": "NG",
                "error": str(e),
                "error_details": error_info
            }

    def _validate_input(self, full_text: str, summary: str, paragraphs: list[str], title: str) -> Dict[str, Any]:
        """入力値を検証する"""
        try:
            if not isinstance(full_text, str):
                return {"error": f"full_textは文字列である必要があります。現在の型: {type(full_text)}"}
            if not isinstance(summary, str):
                return {"error": f"summaryは文字列である必要があります。現在の型: {type(summary)}"}
            if not isinstance(paragraphs, list) or not all(isinstance(p, str) for p in (paragraphs or [])):
                return {"error": f"paragraphsは文字列のリストである必要があります。現在の型: {type(paragraphs)}"}
            if not isinstance(title, str) and title is not None:
                return {"error": f"titleは文字列またはNoneである必要があります。現在の型: {type(title)}"}
                
            if not full_text.strip() or not title.strip():
                return {"error": "空の文書またはタイトルは評価できません"}
                
            return {"success": True}
            
        except Exception as e:
            return {"error": f"入力値の検証中にエラーが発生: {str(e)}"}

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """エラーレスポンスを生成する"""
        return {
            "evaluations": [],
            "categories": [],
            "categoryScores": [],
            "totalScore": 0.0,
            "totalJudgment": "NG",
            "error": error_message,
            "error_details": self.error_details
        }

    async def _evaluate_category(self, category_id: str, category_info: CriteriaInfo, document_structure: Dict[str, str]) -> List[LocationComments]:
        """カテゴリごとの評価を実行する"""
        try:
            self.logger.debug(f"\n=== カテゴリ {category_id} の評価を開始します ===")
            
            # 評価処理の実行
            location_comments = []
            
            for criteria_id in category_info.criteria_ids:
                try:
                    # 評価基準の情報を取得
                    criteria = next(
                        (c for c in EVALUATION_CRITERIA if c["name"] == criteria_id),
                        None
                    )
                    
                    if not criteria:
                        raise ValueError(f"評価基準 {criteria_id} が見つかりません")
                    
                    self.logger.debug(f"評価基準の説明: {criteria['description'][:100]}...")
                    
                    # 評価対象のテキストを取得
                    target_type = identify_target_type(document_structure)
                    target_text = get_evaluation_text(document_structure, target_type)
                    
                    if not target_text:
                        self.logger.warning(f"評価基準 {criteria_id} の評価対象テキストが空です")
                        return [LocationComments(
                            location="エラー",
                            comments=[Comment(
                                criteria_id=criteria_id,
                                content="• 評価対象のテキストが空です\n• 文書の内容を確認してください",
                                score=0.0
                            )]
                        )]

                    # 評価メッセージを準備
                    try:
                        messages = [
                            {
                                "role": "system",
                                "content": SYSTEM_PROMPT
                            },
                            {
                                "role": "user",
                                "content": f"""
以下の評価基準に基づいて、提供されたテキストを評価し、結果を指定された形式で返してください。

【評価基準】
{criteria['description']}

【評価対象テキスト】
{target_text}

【出力形式】
以下のJSON形式で出力してください：

{{
    "category": "{criteria_id}",
    "score": 評価スコア（0から1の小数）,
    "feedback": [
        "評価コメント1",
        "評価コメント2",
        ...
    ],
    "target_text": "評価対象の具体的な文章（問題がある場合）",
    "improvement_suggestions": [
        "改善提案1",
        "改善提案2",
        ...
    ]
}}

【注意事項】
1. 評価結果は必ず上記のJSON形式で返してください
2. scoreは0から1の小数値で、1が最高評価です
3. 問題がない場合はscoreを1.0とし、feedbackに「問題なし」を含めてください
4. target_textは問題がある場合のみ設定し、問題がない場合は空文字列としてください
5. JSON形式を厳密に守り、余分な説明は含めないでください
"""
                            }
                        ]

                        if not messages:
                            raise ValueError("評価メッセージの準備に失敗しました")

                        # OpenAI APIを呼び出して評価を実行
                        response = await call_openai_api(messages)
                        if not response:
                            raise ValueError("APIからの応答が空です")

                        # 評価結果をパース
                        evaluation_results = parse_openai_response({
                            'choices': [{'message': {'content': response}}]
                        })

                        if not evaluation_results:
                            raise ValueError("評価結果のパースに失敗しました")

                        # 評価結果をLocationCommentsに変換
                        for result in evaluation_results:
                            # 評価対象テキストの位置を特定
                            target_location = result.target_text or "全体"
                            
                            location_comments.append(LocationComments(
                                location=target_location,
                                comments=[Comment(
                                    criteria_id=criteria_id,
                                    content=result.feedback,
                                    score=result.score
                                )]
                            ))

                        self.logger.info(f"評価完了: カテゴリ={criteria_id}")
                        self.logger.debug(f"評価結果数: {len(location_comments)}")

                    except Exception as e:
                        self.logger.error(f"評価処理中にエラー発生: {str(e)}")
                        error_message = (
                            f"• 評価中にエラーが発生しました\n"
                            f"• エラーの種類: {type(e).__name__}\n"
                            f"• エラーの詳細: {str(e)}\n"
                            f"• 対応方法:\n"
                            f"  - しばらく待ってから再試行してください\n"
                            f"  - 文書の長さを調整してみてください\n"
                            f"  - 問題が続く場合は管理者に連絡してください"
                        )
                        location_comments.append(LocationComments(
                            location="エラー",
                            comments=[Comment(
                                criteria_id=criteria_id,
                                content=error_message,
                                score=0.0
                            )]
                        ))

                except Exception as e:
                    self.logger.error(f"評価基準 {criteria_id} の評価中にエラー: {str(e)}")
                    error_message = (
                        f"• 予期せぬエラーが発生しました\n"
                        f"• エラーの種類: {type(e).__name__}\n"
                        f"• エラーの詳細: {str(e)}\n"
                        f"• 対応方法:\n"
                        f"  - 評価を再度実行してください\n"
                        f"  - 問題が続く場合は管理者に連絡してください"
                    )
                    location_comments.append(LocationComments(
                        location="エラー",
                        comments=[Comment(
                            criteria_id=criteria_id,
                            content=error_message,
                            score=0.0
                        )]
                    ))
            
            return location_comments
            
        except Exception as e:
            self.logger.error(f"カテゴリ {category_id} の評価中に致命的なエラー: {str(e)}")
            raise

    def _get_appropriate_section_text(
        self,
        document_structure: Dict[str, str],
        section_type: str,
        target_text: Optional[str] = None
    ) -> str:
        """適切なセクションのテキストを取得する"""
        try:
            # target_textが指定され、かつ文書内に存在する場合はそれを使用
            if target_text:
                for section in ['summary', 'story', 'body']:
                    if document_structure.get(section) and target_text in document_structure[section]:
                        return target_text

            # target_textが見つからない場合は、評価対象タイプに応じたテキストを取得
            target_type = identify_target_type(document_structure)
            return get_evaluation_text(document_structure, target_type) or "文書の内容を確認してください"
            
        except Exception as e:
            self.logger.error(f"適切なセクションテキストの取得中にエラー: {str(e)}")
            return "文書の内容を確認してください"

    def _split_document(self, document_text: str) -> List[Dict]:
        """
        文書を評価単位で分割する（実装は省略）
        
        Args:
            document_text (str): 分割対象の文書テキスト
            
        Returns:
            List[Dict]: 分割された文書の各部分（identifier と text を含む）
        """
        # TODO: 実際の分割ロジックを実装
        return [{"identifier": "全文", "text": document_text}]

    def _verify_text_exists(self, target_text: str, document_structure: Dict[str, str]) -> bool:
        """
        対象文が文書内に存在するか確認

        Args:
            target_text (str): 確認する文章
            document_structure (Dict[str, str]): 文書構造

        Returns:
            bool: 文書内に存在すればTrue
        """
        for section in ["summary", "story", "body"]:
            if section in document_structure and target_text in document_structure[section]:
                return True
        return False

    def _parse_evaluation_text(
        self,
        evaluation_text: str,
        criteria_id: str,
        priority: int,
        applicable_to: List[str],
        document_structure: Dict[str, str]
    ) -> List[EvaluationResult]:
        """
        評価テキストを解析して評価結果のリストを生成する

        Args:
            evaluation_text (str): 評価テキスト
            criteria_id (str): 評価基準ID
            priority (int): 優先度
            applicable_to (List[str]): 適用対象
            document_structure (Dict[str, str]): 文書構造

        Returns:
            List[EvaluationResult]: 評価結果のリスト
        """
        try:
            self.logger.debug(f"\n=== 評価テキストの解析開始: {criteria_id} ===")
            self.logger.debug(f"評価テキスト:\n{evaluation_text}")

            # "問題なし"の場合の処理
            if "問題なし" in evaluation_text:
                self.logger.debug(f"{criteria_id}: 問題なしと判定")
                result = EvaluationResult(
                    category_id=criteria_id,
                    category_name=self._get_category_name(criteria_id),
                    priority=priority,
                    locations=[{
                        "location": "全体",
                        "comments": [{
                            "criteria_id": criteria_id,
                            "content": "• 問題は見つかりませんでした\n• 評価基準を満たしています",
                            "score": 1.0
                        }]
                    }],
                    score=1.0,
                    feedback="• 問題は見つかりませんでした\n• 評価基準を満たしています",
                    target_text="",
                    position=None
                )
                self.logger.debug(f"問題なしの評価結果:\n{json.dumps(result.dict(), ensure_ascii=False, indent=2)}")
                return [result]

            # 問題がある場合の処理
            sections = [s.strip() for s in evaluation_text.split("---") if s.strip()]
            self.logger.debug(f"検出されたセクション数: {len(sections)}")
            
            if not sections:
                self.logger.warning("評価結果のセクションが見つかりません")
                return [self._create_error_evaluation(
                    criteria_id,
                    "評価結果のセクションが見つかりません"
                )]
            
            results = []
            for i, section in enumerate(sections, 1):
                self.logger.debug(f"\n--- セクション {i} の処理開始 ---")
                self.logger.debug(f"セクション内容:\n{section}")
                
                # 対象文の抽出
                target_text = ""
                if "対象文：" in section:
                    target_text = section.split("対象文：")[1].split("\n")[0].strip()

                # 問題の重要度と内容の抽出
                severity = "中程度"  # デフォルト
                if "問題あり：" in section:
                    problem_line = section.split("問題あり：")[1].split("\n")[0].strip()
                    if "重大" in problem_line:
                        severity = "重大"
                    elif "軽微" in problem_line:
                        severity = "軽微"

                # フィードバックの収集
                feedback_parts = []
                
                # 問題概要の追加
                if "問題あり：" in section:
                    problem_desc = section.split("問題あり：")[1].split("\n")[0].strip()
                    feedback_parts.append(f"• {problem_desc}")

                # 詳細な説明の追加
                if "説明：" in section:
                    explanation = section.split("説明：")[1].split("\n")[0].strip()
                    feedback_parts.append(f"• {explanation}")

                # 改善提案の追加
                if "改善案：" in section:
                    suggestions = section.split("改善案：")[1].split("\n")[0].strip()
                    feedback_parts.append(f"• 改善提案: {suggestions}")

                # スコアの計算
                score = 1.0  # デフォルト値
                if severity == "重大":
                    score = 0.3
                elif severity == "中程度":
                    score = 0.6
                elif severity == "軽微":
                    score = 0.8

                # 位置情報の取得
                position = None
                if target_text:
                    position = self._find_text_position(target_text, document_structure)
                    self.logger.debug(f"位置情報: {position}")

                # フィードバックの結合
                feedback = "\n".join(feedback_parts)
                self.logger.debug(f"生成されたフィードバック:\n{feedback}")

                # 評価結果の生成
                result = EvaluationResult(
                    category_id=criteria_id,
                    category_name=self._get_category_name(criteria_id),
                    priority=priority,
                    locations=[{
                        "location": target_text or "全体",
                        "comments": [{
                            "criteria_id": criteria_id,
                            "content": feedback,
                            "score": score
                        }]
                    }],
                    score=score,
                    feedback=feedback,
                    target_text=target_text,
                    position=position
                )
                results.append(result)

            return results

        except Exception as e:
            self.logger.error(f"評価テキストのパース中にエラー発生: {str(e)}")
            return [self._create_error_evaluation(
                criteria_id,
                f"評価結果の解析に失敗しました: {str(e)}"
            )]

    def calculate_average_score(self, evaluations: List[Dict[str, Any]]) -> float:
        """
        評価結果の平均スコアを計算する
        
        Args:
            evaluations (List[Dict[str, Any]]): 評価結果のリスト
            
        Returns:
            float: 平均スコア（0.0-1.0の範囲）
        """
        if not evaluations:
            return 0.0
        
        valid_scores = []
        total_evaluations = len(evaluations)
        error_count = 0
        
        for eval in evaluations:
            if eval.get('error'):
                error_count += 1
                continue
                
            score = eval.get('score', 0.0)
            if isinstance(score, (int, float)):
                valid_scores.append(float(score))
        
        # すべての評価がエラーの場合は0.0を返す
        if error_count == total_evaluations:
            return 0.0
            
        # エラー以外の評価の平均値を計算
        return float(sum(valid_scores) / len(valid_scores)) if valid_scores else 0.0

    def _calculate_category_score(self, evaluations: List[Dict[str, Any]], category_info: CriteriaInfo) -> Dict[str, Any]:
        """
        カテゴリごとの評価スコアを計算する
        
        Args:
            evaluations (List[Dict[str, Any]]): カテゴリ内の評価結果
            category_info (CriteriaInfo): カテゴリ情報
            
        Returns:
            Dict[str, Any]: カテゴリスコア情報
        """
        if not evaluations:
            return {
                "categoryId": category_info.id,
                "categoryName": category_info.display_name,
                "score": 0.0,
                "judgment": "NG"
            }
        
        valid_scores = []
        total_evaluations = len(evaluations)
        error_count = 0
        
        for eval in evaluations:
            if eval.get('error'):
                error_count += 1
                continue
                
            score = eval.get('score', 0.0)
            if isinstance(score, (int, float)):
                valid_scores.append(float(score))
        
        # すべての評価がエラーの場合は0.0を返す
        if error_count == total_evaluations:
            average_score = 0.0
        else:
            # エラー以外の評価の平均値を計算
            average_score = float(sum(valid_scores) / len(valid_scores)) if valid_scores else 0.0
        
        return {
            "categoryId": category_info.id,
            "categoryName": category_info.display_name,
            "score": average_score,
            "judgment": "OK" if average_score >= 0.8 else "NG"
        }

    def _create_evaluation_result(self, category: str, score: float, feedback: str, text_position: Optional[Tuple[int, int]] = None) -> EvaluationResult:
        """
        評価結果オブジェクトを作成する
        
        Args:
            category: 評価カテゴリ
            score: スコア
            feedback: フィードバック
            text_position: テキスト内の位置（開始位置、終了位置）
            
        Returns:
            評価結果オブジェクト
        """
        position = Position(text_position[0], text_position[1]) if text_position else None
        
        return EvaluationResult(
            category=category,
            score=score,
            feedback=feedback,
            position=position
        ) 

    def _generate_evaluation_prompt(self, criteria: Dict[str, Any], document_structure: Dict[str, str]) -> str:
        # Implementation of _generate_evaluation_prompt method
        pass

    def _parse_evaluation_response(self, response: Dict[str, Any], category_id: str, criteria_id: str) -> EvaluationResult:
        # Implementation of _parse_evaluation_response method
        pass

    async def _prepare_evaluation_messages(self, criteria_id: str, target_text: str) -> List[Dict[str, str]]:
        """
        評価用のメッセージを準備する

        Args:
            criteria_id (str): 評価基準ID
            target_text (str): 評価対象テキスト

        Returns:
            List[Dict[str, str]]: 評価用メッセージのリスト
        """
        try:
            self.logger.debug(f"\n=== 評価メッセージの準備開始 ===")
            self.logger.debug(f"評価基準ID: {criteria_id}")
            self.logger.debug(f"評価対象テキスト長: {len(target_text)}")

            if not target_text:
                self.logger.error("評価対象テキストが空です")
                raise ValueError("評価対象テキストが空です")

            # 評価基準を取得
            criteria = next(
                (c for c in EVALUATION_CRITERIA if c["name"] == criteria_id),
                None
            )
            
            if not criteria:
                self.logger.error(f"評価基準 {criteria_id} が見つかりません")
                raise ValueError(f"評価基準 {criteria_id} が見つかりません")

            self.logger.debug(f"評価基準の説明: {criteria['description'][:100]}...")
            self.logger.debug(f"評価プロンプトの使用: {criteria_id}")

            # 評価用のメッセージを作成
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"""
以下の評価基準とプロンプトに基づいて、提供されたテキストを評価し、結果を指定された形式で返してください。

【評価基準】
{criteria['description']}

【評価プロンプト】
{criteria['prompt']}

【評価対象テキスト】
{target_text}

【出力形式】
以下のJSON形式で出力してください：

{{
    "category": "{criteria_id}",
    "score": 評価スコア（0から1の小数）,
    "feedback": [
        "評価コメント1",
        "評価コメント2",
        ...
    ],
    "target_text": "評価対象の具体的な文章（問題がある場合）",
    "improvement_suggestions": [
        "改善提案1",
        "改善提案2",
        ...
    ]
}}

【注意事項】
1. 評価結果は必ず上記のJSON形式で返してください
2. scoreは0から1の小数値で、1が最高評価です
3. 問題がない場合はscoreを1.0とし、feedbackに「問題なし」を含めてください
4. target_textは問題がある場合のみ設定し、問題がない場合は空文字列としてください
5. JSON形式を厳密に守り、余分な説明は含めないでください
6. 評価プロンプトに記載された具体的な評価項目に基づいて評価を行ってください
"""
                }
            ]
            
            self.logger.debug(f"評価メッセージを準備完了: 基準={criteria_id}, テキスト長={len(target_text)}")
            self.logger.debug(f"メッセージ数: {len(messages)}")
            return messages
            
        except Exception as e:
            self.logger.error(f"評価メッセージの準備中にエラーが発生: {str(e)}")
            self.logger.error(f"エラータイプ: {type(e).__name__}")
            self.logger.error(f"エラー詳細: {traceback.format_exc()}")
            raise ValueError(f"評価メッセージの準備に失敗: {str(e)}") 