"""
評価処理を管理するサービス
"""
import logging
import asyncio
import sys
import json
from typing import List, Dict, Any, Optional, Tuple
from .text_analyzer import TextAnalyzer
from ..prompt_template.prompt import EVALUATION_CRITERIA, EVALUATION_PROMPT_TEMPLATE
from openai import AsyncAzureOpenAI
from ..models.evaluation import EvaluationResult
from ..config import get_settings, CRITERIA_MAPPING
from ..models.evaluation_result import LocationComments, Comment, Position
from ..models.criteria_info import CriteriaInfo

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
            azure_endpoint=settings.OPENAI_API_BASE_URL,
            timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES
        )
        logger.debug("EvaluationService initialized with Azure OpenAI client")
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)

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
        self.logger.info("\n=== 文書評価プロセスを開始 ===")
        self.logger.info(f"タイトル: {title}")
        self.logger.debug(f"サマリー: {summary[:100]}...")
        self.logger.debug(f"段落数: {len(paragraphs)}")
        self.logger.debug(f"本文長: {len(full_text)}")

        try:
            # 入力値の検証
            if not isinstance(full_text, str) or not isinstance(title, str):
                self.logger.error("入力値の型が不正: full_textとtitleは文字列である必要があります")
                raise ValueError("文書本文とタイトルは文字列である必要があります")

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
                    else:
                        self.logger.warning(f"カテゴリ {category_id} の評価結果が空です")
                    
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

                except Exception as e:
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
            self.logger.error(f"文書評価中にエラーが発生: {str(e)}", exc_info=True)
            return {
                "evaluations": [],
                "categories": [],
                "categoryScores": [],
                "totalScore": 0.0,
                "totalJudgment": "NG",
                "error": str(e)
            }

    async def _evaluate_category(self, category_id: str, category_info: CriteriaInfo, document_structure: Dict[str, str]) -> List[LocationComments]:
        location_comments = []
        self.logger.debug(f"\n=== カテゴリ {category_id} の評価を開始します ===")
        self.logger.debug(f"カテゴリ名: {category_info.display_name}")
        self.logger.debug(f"優先度: {category_info.priority}")
        self.logger.debug(f"評価基準: {category_info.criteria_ids}")
        self.logger.debug(f"評価対象範囲: {category_info.applicable_to}")

        try:
            # 評価対象のテキストを取得
            target_text = self._get_evaluation_text(
                document_structure,
                category_info.applicable_to
            )
            self.logger.debug(f"評価対象テキスト長: {len(target_text)}")
            self.logger.debug(f"評価対象テキストサンプル: {target_text[:200]}...")

            if not target_text:
                self.logger.warning(f"カテゴリ {category_id} の評価対象テキストが空です")
                return [LocationComments(
                    location=category_id,
                    comments=[Comment(
                        criteria_id=category_info.criteria_ids[0],
                        content="• 評価対象テキストが空です\n• 文書の内容を確認してください",
                        score=0.0
                    )]
                )]

            # document_structureを正しい形式で作成
            evaluation_doc_structure = {
                "title": document_structure.get("title", ""),
                "summary": document_structure.get("summary", ""),
                "story": document_structure.get("story", ""),
                "body": target_text,
                "structure": document_structure.get("structure", {})
            }

            self.logger.debug("\n=== 評価用文書構造の確認 ===")
            self.logger.debug(f"タイトル長: {len(evaluation_doc_structure['title'])}")
            self.logger.debug(f"サマリー長: {len(evaluation_doc_structure['summary'])}")
            self.logger.debug(f"ストーリー長: {len(evaluation_doc_structure['story'])}")
            self.logger.debug(f"本文長: {len(evaluation_doc_structure['body'])}")

            # 各評価基準で評価を実行
            for criteria_id in category_info.criteria_ids:
                try:
                    self.logger.debug(f"\n--- 評価基準 {criteria_id} の評価開始 ---")
                    evaluations = await self._evaluate_single_criteria(
                        criteria_id=criteria_id,
                        document_structure=evaluation_doc_structure
                    )
                    
                    if evaluations:
                        self.logger.debug(f"評価結果数: {len(evaluations)}")
                        for evaluation in evaluations:
                            if evaluation and isinstance(evaluation, EvaluationResult):
                                self.logger.debug(f"評価結果:")
                                self.logger.debug(f"スコア: {evaluation.score}")
                                self.logger.debug(f"フィードバック: {evaluation.feedback}")
                                
                                # 既存のLocationCommentsを探す
                                location_comment = next(
                                    (lc for lc in location_comments if lc.location == category_id),
                                    None
                                )
                                
                                if location_comment:
                                    # 既存のLocationCommentsにコメントを追加
                                    location_comment.comments.append(Comment(
                                        criteria_id=criteria_id,
                                        content=evaluation.feedback,
                                        score=evaluation.score
                                    ))
                                else:
                                    # 新しいLocationCommentsを作成
                                    location_comments.append(LocationComments(
                                        location=category_id,
                                        comments=[Comment(
                                            criteria_id=criteria_id,
                                            content=evaluation.feedback,
                                            score=evaluation.score
                                        )]
                                    ))
                    else:
                        self.logger.warning(f"評価基準 {criteria_id} の評価結果が空です")
                        location_comments.append(LocationComments(
                            location=category_id,
                            comments=[Comment(
                                criteria_id=criteria_id,
                                content="• 評価結果が生成できませんでした\n• 該当箇所の評価を再度実行してください",
                                score=0.0
                            )]
                        ))
                
                except Exception as e:
                    self.logger.error(f"評価基準 {criteria_id} の評価中にエラーが発生: {str(e)}", exc_info=True)
                    location_comments.append(LocationComments(
                        location=category_id,
                        comments=[Comment(
                            criteria_id=criteria_id,
                            content="• 評価中にエラーが発生しました\n• 該当箇所の評価を再度実行してください",
                            score=0.0
                        )]
                    ))

            self.logger.debug(f"\n=== カテゴリ {category_id} の評価完了 ===")
            self.logger.debug(f"生成されたコメント数: {len(location_comments)}")
            
            # 評価結果が空の場合のデフォルト値を設定
            if not location_comments:
                self.logger.warning(f"カテゴリ {category_id} の評価結果が空のため、デフォルト値を設定します")
                return [LocationComments(
                    location=category_id,
                    comments=[Comment(
                        criteria_id=category_info.criteria_ids[0],
                        content="• 評価結果が生成できませんでした\n• 該当箇所の評価を再度実行してください",
                        score=0.0
                    )]
                )]
                
            return location_comments

        except Exception as e:
            self.logger.error(f"カテゴリ {category_id} の評価中にエラーが発生: {str(e)}", exc_info=True)
            return [LocationComments(
                location=category_id,
                comments=[Comment(
                    criteria_id=category_info.criteria_ids[0],
                    content="• 評価中にエラーが発生しました\n• 該当箇所の評価を再度実行してください",
                    score=0.0
                )]
            )]

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

    async def _evaluate_single_criteria(self, criteria_id: str, document_structure: Dict[str, str]) -> List[EvaluationResult]:
        try:
            # 評価基準の情報を取得
            criteria = next(
                (c for c in EVALUATION_CRITERIA if c['id'] == criteria_id),
                None
            )
            
            if not criteria:
                self.logger.error(f"評価基準 {criteria_id} が見つかりません")
                return [EvaluationResult(
                    criteria_id=criteria_id,
                    category=criteria_id,
                    score=0.0,
                    feedback="• 評価基準が見つかりません\n• システム管理者に連絡してください",
                    target_text="",
                    position=None
                )]

            # 評価基準の説明が存在することを確認
            if 'description' not in criteria:
                self.logger.error(f"評価基準 {criteria_id} の説明が見つかりません")
                return [EvaluationResult(
                    criteria_id=criteria_id,
                    category=criteria_id,
                    score=0.0,
                    feedback="• 評価基準の説明が定義されていません\n• システム管理者に連絡してください",
                    target_text="",
                    position=None
                )]

            # 評価対象のテキストを取得
            target_text = self._get_evaluation_text(
                document_structure,
                criteria.get('applicable_to', ['FULL_DOCUMENT'])
            )
            
            if not target_text:
                self.logger.warning("評価対象テキストが空です")
                return [EvaluationResult(
                    criteria_id=criteria_id,
                    category=criteria_id,
                    score=0.0,
                    feedback="• 評価対象のテキストが空です\n• 文書の内容を確認してください",
                    target_text="",
                    position=None
                )]

            self.logger.debug(f"\n=== 評価基準 {criteria_id} の評価開始 ===")
            self.logger.debug(f"評価対象テキスト:\n{target_text}")
            self.logger.debug(f"評価基準の詳細:\n{json.dumps(criteria, ensure_ascii=False, indent=2)}")

            # 評価プロンプトを構築
            evaluation_prompt = EVALUATION_PROMPT_TEMPLATE.format(
                criteria_name=criteria.get('name', criteria_id),
                criteria_description=criteria['description'],
                target_text=target_text
            )

            # Azure OpenAI APIを呼び出し
            try:
                response = await self.client.chat.completions.create(
                    model=self.settings.OPENAI_API_LLM_MODEL_NAME,
                    messages=[
                        {"role": "system", "content": "あなたはビジネス文書の評価専門家です。与えられた評価基準に厳密に従って評価を行い、指定された形式で結果を出力してください。"},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    max_tokens=self.settings.OPENAI_MAX_TOKENS,
                    temperature=self.settings.OPENAI_TEMPERATURE
                )

                if not response.choices:
                    self.logger.error("OpenAI APIからの応答が空です")
                    return [EvaluationResult(
                        criteria_id=criteria_id,
                        category=criteria_id,
                        score=0.0,
                        feedback="• APIからの応答が空です\n• 再度評価を実行してください",
                        target_text="",
                        position=None
                    )]

                evaluation_text = response.choices[0].message.content
                self.logger.debug(f"OpenAI APIからの応答:\n{evaluation_text}")

                if not evaluation_text:
                    self.logger.error("評価テキストが空です")
                    return [EvaluationResult(
                        criteria_id=criteria_id,
                        category=criteria_id,
                        score=0.0,
                        feedback="• 評価結果が空です\n• 再度評価を実行してください",
                        target_text="",
                        position=None
                    )]

                # レスポンスから評価結果を解析
                evaluation_results = self._parse_evaluation_text(
                    evaluation_text,
                    criteria_id,
                    criteria.get('priority', 1),
                    criteria.get('applicable_to', ['FULL_DOCUMENT']),
                    document_structure
                )

                if not evaluation_results:
                    self.logger.warning(f"評価基準 {criteria_id} の評価結果が空です")
                    return [EvaluationResult(
                        criteria_id=criteria_id,
                        category=criteria_id,
                        score=1.0,
                        feedback="• 問題は見つかりませんでした\n• 評価基準を満たしています",
                        target_text="",
                        position=None
                    )]

                self.logger.debug(f"解析された評価結果:\n{json.dumps([result.dict() for result in evaluation_results], ensure_ascii=False, indent=2)}")
                return evaluation_results

            except Exception as api_error:
                self.logger.error(f"OpenAI API呼び出し中にエラーが発生: {str(api_error)}")
                return [EvaluationResult(
                    criteria_id=criteria_id,
                    category=criteria_id,
                    score=0.0,
                    feedback="• OpenAI APIでエラーが発生しました\n• 再度評価を実行してください",
                    target_text="",
                    position=None
                )]

        except Exception as e:
            self.logger.error(f"評価基準 {criteria_id} の評価中にエラーが発生: {str(e)}", exc_info=True)
            return [EvaluationResult(
                criteria_id=criteria_id,
                category=criteria_id,
                score=0.0,
                feedback="• 評価中にエラーが発生しました\n• 該当箇所の評価を再度実行してください",
                target_text="",
                position=None
            )]

    def _get_evaluation_text(self, document_structure: Dict[str, str], applicable_to: List[str]) -> str:
        """
        評価対象範囲のテキストを取得する

        Args:
            document_structure (Dict[str, str]): 文書構造
            applicable_to (List[str]): 評価対象範囲の指定

        Returns:
            str: 評価対象のテキスト
        """
        target_text = ""
        
        if "FULL_DOCUMENT" in applicable_to:
            # サマリ、ストーリー、ボディ、詳細を対象に評価
            target_text = f"""
            【サマリー】
            {document_structure.get('summary', '')}
            
            【ストーリー】
            {document_structure.get('story', '')}
            
            【本文】
            {document_structure.get('body', '')}
            """
        
        elif "SUMMARY_ONLY" in applicable_to:
            # サマリのまとまりに対して評価
            target_text = f"""
            【サマリー】
            {document_structure.get('summary', '')}
            """
        
        elif "SUMMARY_AND_STORY" in applicable_to:
            # サマリとストーリーのまとまりに対して評価
            target_text = f"""
            【サマリー】
            {document_structure.get('summary', '')}
            
            【ストーリー】
            {document_structure.get('story', '')}
            
            【文章構造の関連性】
            サマリーとストーリーの各段落は、同じ番号の段落同士が対応関係にあります。
            """
        
        elif "STORY_AND_BODY" in applicable_to:
            # ストーリーとボディのまとまりに対して評価
            target_text = f"""
            【ストーリー】
            {document_structure.get('story', '')}
            
            【本文】
            {document_structure.get('body', '')}
            
            【文章構造の関連性】
            ストーリーとボディの各段落は、同じ番号の段落同士が対応関係にあります。
            """
        
        return target_text.strip()

    def _find_text_position(self, target_text: str, document_structure: Optional[Dict[str, str]] = None) -> Optional[Tuple[int, int]]:
        """
        対象テキストの位置を特定する

        Args:
            target_text (str): 検索対象のテキスト
            document_structure (Optional[Dict[str, str]]): 文書構造。Noneの場合は空の辞書を使用

        Returns:
            Optional[Tuple[int, int]]: テキストの開始位置と終了位置のタプル。見つからない場合はNone
        """
        try:
            if not target_text:
                self.logger.warning("検索対象のテキストが空です")
                return None

            # document_structureが指定されていない場合は空の辞書を使用
            doc_structure = document_structure or {}
            
            # 各セクションごとに位置を計算
            current_position = 0
            
            # サマリーセクションの処理
            summary = doc_structure.get("summary", "").strip()
            if summary:
                if target_text in summary:
                    start_pos = summary.find(target_text)
                    return (current_position + start_pos, current_position + start_pos + len(target_text))
                current_position += len(summary) + 2  # 改行文字分を加算
            
            # ストーリーセクションの処理
            story = doc_structure.get("story", "").strip()
            if story:
                if target_text in story:
                    start_pos = story.find(target_text)
                    return (current_position + start_pos, current_position + start_pos + len(target_text))
                current_position += len(story) + 2
            
            # 本文セクションの処理
            body = doc_structure.get("body", "").strip()
            if body:
                if target_text in body:
                    start_pos = body.find(target_text)
                    return (current_position + start_pos, current_position + start_pos + len(target_text))
            
            self.logger.warning(f"テキスト '{target_text[:50]}...' が文書内で見つかりませんでした")
            return None
            
        except Exception as e:
            self.logger.error(f"テキスト位置の特定中にエラーが発生: {str(e)}")
            return None

    def _get_category_name(self, category_id: str) -> str:
        """
        カテゴリIDに対応する表示名を取得

        Args:
            category_id (str): カテゴリID

        Returns:
            str: カテゴリの表示名。未知のカテゴリIDの場合はIDをそのまま返す
        """
        try:
            return CRITERIA_MAPPING[category_id].display_name
        except KeyError:
            self.logger.warning(f"未知のカテゴリID: {category_id}")
            return category_id

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
        try:
            self.logger.debug(f"\n=== 評価テキストの解析開始: {criteria_id} ===")
            self.logger.debug(f"評価テキスト:\n{evaluation_text}")

            # 「問題なし」の場合の処理
            if "問題なし" in evaluation_text:
                self.logger.debug(f"{criteria_id}: 問題なしと判定")
                result = EvaluationResult(
                    criteria_id=criteria_id,
                    category=criteria_id,  # カテゴリIDを設定
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
                return [EvaluationResult(
                    criteria_id=criteria_id,
                    category=criteria_id,  # カテゴリIDを設定
                    score=0.5,
                    feedback="• 評価結果が不明確です\n• 該当箇所の評価を再度実行してください",
                    target_text="",
                    position=None
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
                    problem_summary = section.split("問題あり：")[1].split("\n")[0].strip()
                    feedback_parts.append(f"【{severity}】{problem_summary}")

                # 問題点の追加
                if "問題点：" in section:
                    points = section.split("問題点：")[1].split("改善提案：")[0]
                    points = [p.strip("- ").strip() for p in points.split("\n") if p.strip() and p.strip("- ")]
                    if points:
                        feedback_parts.append("【問題点】")
                        feedback_parts.extend(points)

                # 改善提案の追加
                if "改善提案：" in section:
                    suggestions = section.split("改善提案：")[1].split("---")[0]
                    suggestions = [s.strip("- ").strip() for s in suggestions.split("\n") if s.strip() and s.strip("- ")]
                    if suggestions:
                        feedback_parts.append("【改善提案】")
                        feedback_parts.extend(suggestions)

                # スコアの計算
                issue_weights = {"重大": 0.6, "中程度": 0.3, "軽微": 0.1}
                score = max(0.0, 1.0 - issue_weights[severity])

                # 位置情報の取得
                position = self._find_text_position(target_text, document_structure) if target_text else None

                result = EvaluationResult(
                    criteria_id=criteria_id,
                    category=criteria_id,  # カテゴリIDを設定
                    score=score,
                    feedback="\n".join(feedback_parts) if feedback_parts else "問題は見つかりませんでした",
                    target_text=target_text,
                    position=Position(start=position[0], end=position[1]) if position else None
                )
                self.logger.debug(f"セクション {i} の評価結果:\n{json.dumps(result.dict(), ensure_ascii=False, indent=2)}")
                results.append(result)

            if not results:
                self.logger.warning("評価結果が生成されませんでした")
                return [EvaluationResult(
                    criteria_id=criteria_id,
                    category=criteria_id,  # カテゴリIDを設定
                    score=0.5,
                    feedback="• 評価結果を生成できませんでした\n• 該当箇所の評価を再度実行してください",
                    target_text="",
                    position=None
                )]

            self.logger.debug(f"\n=== 評価テキストの解析完了 ===")
            self.logger.debug(f"生成された評価結果数: {len(results)}")
            return results

        except Exception as e:
            self.logger.error(f"評価テキストの解析中にエラーが発生: {str(e)}", exc_info=True)
            return [EvaluationResult(
                criteria_id=criteria_id,
                category=criteria_id,  # カテゴリIDを設定
                score=0.0,
                feedback="• 評価中にエラーが発生しました\n• 該当箇所の評価を再度実行してください",
                target_text="",
                position=None
            )]

    def calculate_average_score(self, evaluations: List[Dict[str, Any]]) -> float:
        """
        評価結果の平均スコアを計算する

        Args:
            evaluations (List[Dict[str, Any]]): 評価結果のリスト

        Returns:
            float: 平均スコア（0-1の範囲）
        """
        try:
            self.logger.debug("\n=== スコア計算開始 ===")
            self.logger.debug(f"評価結果数: {len(evaluations)}")
            
            if not evaluations:
                self.logger.warning("評価結果が空のため、スコアは0.0とします")
                return 0.0
            
            # カテゴリごとの重み付け
            category_weights = {
                'FULL_TEXT_RHETORIC': 1.0,      # 文章全体の修辞
                'SUMMARY_LOGIC_FLOW': 1.2,      # サマリーの論理展開
                'SUMMARY_INTERNAL_LOGIC': 1.1,   # サマリーの内部論理
                'SUMMARY_STORY_LOGIC': 1.2,      # サマリーとストーリーの論理
                'STORY_INTERNAL_LOGIC': 1.1,     # ストーリーの内部論理
                'DETAIL_RHETORIC': 0.8           # 詳細の修辞
            }
            
            # カテゴリごとのスコアを集計
            category_scores = {}
            category_counts = {}
            
            for eval in evaluations:
                if isinstance(eval.get("score"), (int, float)):
                    category_id = eval.get("categoryId", "unknown")
                    score = float(eval["score"])
                    
                    if category_id not in category_scores:
                        category_scores[category_id] = 0.0
                        category_counts[category_id] = 0
                    
                    category_scores[category_id] += score
                    category_counts[category_id] += 1
            
            # カテゴリごとの平均スコアを計算
            weighted_scores = []
            total_weight = 0.0
            
            for category_id, total_score in category_scores.items():
                count = category_counts[category_id]
                if count > 0:
                    avg_score = total_score / count
                    weight = category_weights.get(category_id, 1.0)
                    weighted_scores.append(avg_score * weight)
                    total_weight += weight
            
            # 重み付き平均を計算
            if total_weight > 0:
                final_score = sum(weighted_scores) / total_weight
                self.logger.debug(f"計算された最終スコア: {final_score}")
                return min(max(final_score, 0.0), 1.0)
            
            self.logger.warning("有効なスコアが見つからないため、スコアは0.0とします")
            return 0.0
            
        except Exception as e:
            self.logger.error(f"スコア計算中にエラーが発生: {str(e)}")
            return 0.0

    def _calculate_category_score(self, evaluations: List[Dict[str, Any]], category_info: CriteriaInfo) -> Dict[str, Any]:
        """
        カテゴリごとの評価スコアを計算する

        Args:
            evaluations (List[Dict[str, Any]]): カテゴリの評価結果リスト
            category_info (CriteriaInfo): カテゴリ情報

        Returns:
            Dict[str, Any]: カテゴリスコアデータ
        """
        if not evaluations:
            return {
                "categoryId": category_info.id,
                "categoryName": category_info.display_name,
                "score": 0.0,
                "judgment": "NG"
            }

        # 重み付けを考慮したスコア計算
        total_weight = 0.0
        weighted_score = 0.0

        for evaluation in evaluations:
            criteria_id = evaluation["criteriaId"]
            score = evaluation["score"]
            weight = category_info.criteria_weights.get(criteria_id, 1.0)
            
            weighted_score += score * weight
            total_weight += weight

        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0.0

        return {
            "categoryId": category_info.id,
            "categoryName": category_info.display_name,
            "score": round(final_score * 100, 1),
            "judgment": "OK" if final_score >= 0.8 else "NG"
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

    def _parse_evaluation_text(self, evaluation_text: str, criteria_id: str, priority: int, applicable_to: List[str], document_structure: Dict[str, str]) -> List[EvaluationResult]:
        # Implementation of _parse_evaluation_text method
        pass

    def _parse_evaluation_response(self, response: Dict[str, Any], category_id: str, criteria_id: str) -> EvaluationResult:
        # Implementation of _parse_evaluation_response method
        pass 