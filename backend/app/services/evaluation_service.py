"""
評価処理を管理するサービス
"""
import logging
import asyncio
import sys
from typing import List, Dict, Any, Optional
from .text_analyzer import TextAnalyzer
from ..prompt_template.prompt import EVALUATION_CRITERIA, EVALUATION_PROMPT_TEMPLATE
from openai import AsyncAzureOpenAI
from ..models.evaluation import EvaluationResult
from ..config import get_settings, CRITERIA_MAPPING
from ..models.evaluation_result import LocationComments, Comment
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
        self.logger.info("文書評価を開始します")

        try:
            # 入力値の検証
            if not full_text or not title:
                raise ValueError("文書本文とタイトルは必須です")

            if not isinstance(paragraphs, list):
                raise ValueError("paragraphsはリスト形式である必要があります")

            if not all(isinstance(p, str) for p in paragraphs):
                raise ValueError("すべての段落はテキスト形式である必要があります")

            # 空の段落を除外
            paragraphs = [p for p in paragraphs if p and p.strip()]
            if not paragraphs:
                raise ValueError("有効な段落が見つかりません")

            # 文書構造の作成
            document_structure = {
                "title": title,
                "summary": summary.strip() if summary else "",
                "story": "\n\n".join(paragraphs),
                "body": full_text
            }

            self.logger.debug(f"文書構造: タイトル「{title}」")
            self.logger.debug(f"サマリー文字数: {len(document_structure['summary'])}")
            self.logger.debug(f"本文文字数: {len(document_structure['body'])}")

            # カテゴリを優先順位でソート
            sorted_categories = sorted(
                CRITERIA_MAPPING.items(),
                key=lambda x: x[1].priority
            )

            # 評価結果の構造を作成
            result = {
                "evaluations": [],
                "categories": [],
                "categoryScores": []  # カテゴリごとのスコアと判定を追加
            }

            for category_id, category_info in sorted_categories:
                self.logger.info(f"カテゴリ '{category_info.display_name}' (優先順位: {category_info.priority}) の評価を開始します")
                
                try:
                    # 該当箇所の特定と評価の実行
                    locations = await self._evaluate_category(document_structure, category_id, category_info)
                    
                    # カテゴリ情報を追加
                    category_data = {
                        "id": category_id,
                        "name": category_info.display_name,
                        "priority": category_info.priority
                    }
                    result["categories"].append(category_data)

                    # 評価結果を追加
                    category_evaluations = []
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

                    # カテゴリごとの平均スコアと判定を計算
                    if category_evaluations:
                        category_score = sum(eval["score"] for eval in category_evaluations) / len(category_evaluations)
                        result["categoryScores"].append({
                            "categoryId": category_id,
                            "categoryName": category_info.display_name,
                            "score": round(category_score * 100, 1),  # パーセント表示に変換
                            "judgment": "OK" if category_score >= 0.8 else "NG"  # 80%以上でOK
                        })
                    else:
                        # 評価結果がない場合のデフォルト値
                        result["categoryScores"].append({
                            "categoryId": category_id,
                            "categoryName": category_info.display_name,
                            "score": 0.0,
                            "judgment": "NG"
                        })

                    self.logger.info(f"カテゴリ '{category_info.display_name}' の評価が完了しました")
                    
                except Exception as e:
                    self.logger.error(f"カテゴリ '{category_info.display_name}' の評価中にエラーが発生しました: {str(e)}")
                    continue

            # 総合スコアを計算
            total_score = self._calculate_average_score(result["evaluations"])
            result["totalScore"] = round(total_score * 100, 1)  # パーセント表示に変換
            result["totalJudgment"] = "OK" if total_score >= 0.8 else "NG"  # 80%以上でOK

            return result

        except Exception as e:
            self.logger.error(f"文書評価中にエラーが発生しました: {str(e)}")
            return {
                "evaluations": [],
                "categories": [],
                "categoryScores": [],
                "totalScore": 0.0,
                "totalJudgment": "NG",
                "error": str(e)
            }

    async def _evaluate_category(self, document_structure: Dict[str, str], category_id: str, category_info: CriteriaInfo) -> List[LocationComments]:
        """
        カテゴリごとの評価を実行

        Args:
            document_structure (Dict[str, str]): 文書構造
            category_id (str): カテゴリID
            category_info (CriteriaInfo): カテゴリ情報

        Returns:
            List[LocationComments]: 該当箇所ごとのコメントリスト
        """
        location_comments = []
        self.logger.debug(f"カテゴリ {category_id} の評価を開始します")

        try:
            # 評価対象のテキストを取得
            target_text = self._get_evaluation_text(
                document_structure,
                category_info.applicable_to
            )
            self.logger.debug(f"評価対象テキスト:\n{target_text}")

            # 各評価基準で評価を実行
            for criteria_id in category_info.criteria_ids:
                try:
                    self.logger.debug(f"評価基準 {criteria_id} の評価を開始します")
                    evaluation = await self._evaluate_single_criteria(
                        criteria_id=criteria_id,
                        document_structure={"text": target_text}
                    )
                    
                    if evaluation and not isinstance(evaluation, Exception):
                        self.logger.debug(f"評価結果: {evaluation}")
                        location_comments.append(LocationComments(
                            location=category_id,
                            comments=[Comment(
                                criteria_id=criteria_id,
                                content=evaluation.feedback,
                                score=evaluation.score
                            )]
                        ))
                    else:
                        self.logger.warning(f"評価基準 {criteria_id} の評価結果が無効です: {evaluation}")
                
                except Exception as e:
                    self.logger.error(f"評価基準 {criteria_id} の評価中にエラーが発生: {str(e)}")
                    continue

            self.logger.debug(f"カテゴリ {category_id} の評価結果: {location_comments}")
            return location_comments

        except Exception as e:
            self.logger.error(f"カテゴリ {category_id} の評価中にエラーが発生: {str(e)}")
            return []

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

    async def _evaluate_single_criteria(self, criteria_id: str, document_structure: Dict[str, str]) -> Any:
        """
        単一の評価基準で評価を実行
        
        Args:
            criteria_id: 評価基準ID
            document_structure: 文書構造
            
        Returns:
            評価結果
        """
        try:
            # 評価基準の情報を取得
            criteria = next(
                (c for c in EVALUATION_CRITERIA if c['name'] == criteria_id),
                None
            )
            
            if not criteria:
                raise ValueError(f"評価基準 {criteria_id} が見つかりません")

            # 評価対象のテキストを取得
            target_text = self._get_evaluation_text(
                document_structure,
                criteria.get('applicable_to', ['FULL_DOCUMENT'])
            )

            self.logger.debug(f"評価基準 {criteria_id} の評価を開始します")
            self.logger.debug(f"評価対象テキスト:\n{target_text}")

            # 評価プロンプトを構築
            evaluation_prompt = f"""
# 評価基準：{criteria['name']}

{criteria['description']}

# 評価対象テキスト：
{target_text}

# 評価指示
上記の評価基準に基づいて、評価対象テキストを厳密に分析してください。
以下の点に特に注意して評価を行ってください：

1. 接続詞の使用：
   - 同じ種類の接続詞が近接して使用されていないか
   - 不必要な接続詞の重複がないか
   - 「しかし」「ただし」「一方」などの転換の接続詞の使用が適切か

2. 文章構造：
   - 箇条書きやナンバリングが重複していないか
   - 「まず」「次に」「最後に」などの順序を表す表現が適切か
   - 同じ内容を異なる形式で重複して説明していないか

3. 論理展開：
   - 各段落の関係性が明確か
   - 前後の文脈が整合しているか
   - 不要な繰り返しがないか

結果は以下の形式で出力してください：

1. 問題が見つからない場合：
「問題なし」とだけ出力してください。

2. 問題が見つかった場合は、各問題について必ず以下の形式で出力してください：

対象文：[問題のある部分の冒頭部分]
問題あり：[問題の概要]
問題点：
- [具体的な問題点1]
- [具体的な問題点2]
改善提案：
- [具体的な改善案1]
- [具体的な改善案2]

---

各問題は必ず上記の形式で出力し、問題ごとに「---」で区切ってください。
それ以外の説明は含めないでください。
"""

            self.logger.debug(f"評価プロンプト:\n{evaluation_prompt}")

            # Azure OpenAI APIを呼び出し
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_API_LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "あなたはビジネス文書の評価専門家です。与えられた評価基準に厳密に従って評価を行い、指定された形式で結果を出力してください。"},
                    {"role": "user", "content": evaluation_prompt}
                ],
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE
            )

            evaluation_text = response.choices[0].message.content
            self.logger.debug(f"OpenAI APIからの応答:\n{evaluation_text}")

            # レスポンスから評価結果を解析
            evaluation_results = self._parse_evaluation_text(
                evaluation_text,
                criteria['name'],
                criteria.get('priority', 1),
                criteria.get('applicable_to', ['FULL_DOCUMENT'])
            )

            self.logger.debug(f"解析された評価結果: {evaluation_results}")

            return evaluation_results[0] if evaluation_results else None

        except Exception as e:
            self.logger.error(f"Error evaluating criteria {criteria_id}: {str(e)}", exc_info=True)
            return e

    def _get_evaluation_text(self, document_structure: Dict[str, str], applicable_to: List[str]) -> str:
        """
        評価対象範囲に応じたテキストを取得する
        
        Args:
            document_structure: 文書構造を表す辞書
            applicable_to: 評価対象範囲のリスト
            
        Returns:
            評価対象テキスト（セクション区切り付き）
        """
        logger.debug(f"Getting evaluation text for applicable_to: {applicable_to}")
        text_parts = []

        # サマリーセクションの処理
        def get_summary_section():
            summary = document_structure.get("summary", "").strip()
            if summary:
                return f"[サマリー]\n{summary}"
            return ""

        # ストーリーセクションの処理
        def get_story_section():
            story = document_structure.get("story", "").strip()
            if story:
                story_parts = []
                for i, paragraph in enumerate(story.split("\n\n"), 1):
                    if paragraph.strip():
                        story_parts.append(f"[本文段落{i}]\n{paragraph.strip()}")
                return "\n\n".join(story_parts)
            return ""

        # 全文セクションの処理
        def get_body_section():
            body = document_structure.get("body", "").strip()
            if body:
                return f"[全文]\n{body}"
            return ""

        # applicable_toが空の場合は全てのセクションを対象とする
        if not applicable_to:
            logger.debug("No applicable_to specified, using FULL_DOCUMENT")
            applicable_to = ["FULL_DOCUMENT"]

        # FULL_DOCUMENTの場合
        if "FULL_DOCUMENT" in applicable_to:
            logger.debug("Processing FULL_DOCUMENT")
            # サマリー、ストーリー、全文の順に追加
            summary_text = get_summary_section()
            if summary_text:
                text_parts.append(summary_text)
                logger.debug("Added summary section for FULL_DOCUMENT")
            
            story_text = get_story_section()
            if story_text:
                text_parts.append(story_text)
                logger.debug("Added story section for FULL_DOCUMENT")
            
            body_text = get_body_section()
            if body_text:
                text_parts.append(body_text)
                logger.debug("Added body section for FULL_DOCUMENT")

        # SUMMARY_ONLYの場合
        elif "SUMMARY_ONLY" in applicable_to:
            logger.debug("Processing SUMMARY_ONLY")
            summary_text = get_summary_section()
            if summary_text:
                text_parts.append(summary_text)
                logger.debug("Added summary section for SUMMARY_ONLY")

        # STORY_AND_BODYの場合
        elif "STORY_AND_BODY" in applicable_to:
            logger.debug("Processing STORY_AND_BODY")
            story_text = get_story_section()
            if story_text:
                text_parts.append(story_text)
                logger.debug("Added story section for STORY_AND_BODY")
            body_text = get_body_section()
            if body_text:
                text_parts.append(body_text)
                logger.debug("Added body section for STORY_AND_BODY")

        # SUMMARY_AND_STORYの場合
        elif "SUMMARY_AND_STORY" in applicable_to:
            logger.debug("Processing SUMMARY_AND_STORY")
            summary_text = get_summary_section()
            if summary_text:
                text_parts.append(summary_text)
                logger.debug("Added summary section for SUMMARY_AND_STORY")
            story_text = get_story_section()
            if story_text:
                text_parts.append(story_text)
                logger.debug("Added story section for SUMMARY_AND_STORY")

        # 結果をログ出力
        result = "\n\n".join(text_parts)
        logger.debug(f"Generated evaluation text ({len(result)} chars):")
        logger.debug(result[:200] + "..." if len(result) > 200 else result)
        
        return result

    def _parse_evaluation_text(self, evaluation_text: str, criteria_id: str, priority: int, applicable_to: List[str]) -> List[EvaluationResult]:
        """
        評価テキストを解析して評価結果を生成する

        Args:
            evaluation_text (str): 評価テキスト
            criteria_id (str): 評価基準ID
            priority (int): 優先順位
            applicable_to (List[str]): 適用範囲

        Returns:
            List[EvaluationResult]: 評価結果のリスト
        """
        try:
            self.logger.debug(f"評価テキストの解析開始: {criteria_id}")
            self.logger.debug(f"評価テキスト:\n{evaluation_text}")
            results = []

            # 「問題なし」の場合の処理
            if "問題なし" in evaluation_text:
                self.logger.debug(f"{criteria_id}: 問題なしと判定")
                return [EvaluationResult(
                    criteria_id=criteria_id,
                    score=1.0,
                    feedback="問題は見つかりませんでした。",
                    category=applicable_to[0] if applicable_to else "FULL_DOCUMENT"
                )]

            # 問題がある場合の処理
            sections = evaluation_text.split("---")
            total_issues = 0
            feedback_parts = []
            issue_weights = {
                "重大": 0.4,  # 重大な問題は0.4点減点
                "中程度": 0.2,  # 中程度の問題は0.2点減点
                "軽微": 0.1   # 軽微な問題は0.1点減点
            }

            for section in sections:
                if not section.strip():
                    continue

                self.logger.debug(f"セクションの解析: {section}")

                # 問題点の抽出
                if "問題あり" in section:
                    current_feedback = []
                    issue_severity = "中程度"  # デフォルトの重要度

                    # 問題の概要を追加
                    if "問題あり：" in section:
                        problem_summary = section.split("問題あり：")[1].split("\n")[0].strip()
                        # 重要度の判定
                        if "重大な" in problem_summary or "深刻な" in problem_summary:
                            issue_severity = "重大"
                        elif "軽微な" in problem_summary or "小さな" in problem_summary:
                            issue_severity = "軽微"
                        current_feedback.append(problem_summary)
                        total_issues += issue_weights[issue_severity]

                    # 問題点の特定
                    if "問題点：" in section:
                        problem_points = section.split("問題点：")[1].split("改善提案：")[0]
                        points = [p.strip("- ").strip() for p in problem_points.split("\n") if p.strip() and p.strip("- ")]
                        if points:
                            current_feedback.extend(points)

                    # 改善提案の特定
                    if "改善提案：" in section:
                        suggestions = section.split("改善提案：")[1]
                        suggestions_list = [s.strip("- ").strip() for s in suggestions.split("\n") if s.strip() and s.strip("- ")]
                        if suggestions_list:
                            current_feedback.append("改善案: " + "、".join(suggestions_list))

                    if current_feedback:
                        feedback_parts.extend(current_feedback)

            # スコアの計算（問題の重要度に応じた減点）
            score = max(0.0, 1.0 - total_issues)
            feedback = "。".join(feedback_parts) if feedback_parts else "評価基準に基づく問題は検出されませんでした。"

            result = EvaluationResult(
                criteria_id=criteria_id,
                score=score,
                feedback=feedback,
                category=applicable_to[0] if applicable_to else "FULL_DOCUMENT"
            )
            self.logger.debug(f"生成された評価結果: {result}")
            results.append(result)

            if not results:
                self.logger.warning(f"{criteria_id}: 評価結果を解析できませんでした")
                return [EvaluationResult(
                    criteria_id=criteria_id,
                    score=0.0,
                    feedback="評価結果を解析できませんでした。",
                    category=applicable_to[0] if applicable_to else "FULL_DOCUMENT"
                )]

            return results

        except Exception as e:
            self.logger.error(f"評価テキストの解析中にエラーが発生: {str(e)}")
            return [EvaluationResult(
                criteria_id=criteria_id,
                score=0.0,
                feedback=f"評価テキストの解析中にエラーが発生しました: {str(e)}",
                category=applicable_to[0] if applicable_to else "FULL_DOCUMENT"
            )]

    def _is_valid_evaluation(self, evaluation: Dict[str, Any]) -> bool:
        """評価結果が有効かどうかをチェック"""
        return (
            evaluation.get('category') and
            isinstance(evaluation.get('score'), (int, float)) and
            isinstance(evaluation.get('priority'), int) and
            evaluation.get('target_sentence') and
            isinstance(evaluation.get('feedback'), list) and
            isinstance(evaluation.get('improvement_suggestions'), list)
        )

    def _calculate_total_score(self, evaluations: List[EvaluationResult]) -> float:
        """総合スコアを計算"""
        if not evaluations:
            return 0.0
            
        # 各文章に対する評価を優先度でグループ化
        evaluations_by_target = {}
        for eval in evaluations:
            if eval.target_sentence not in evaluations_by_target:
                evaluations_by_target[eval.target_sentence] = []
            evaluations_by_target[eval.target_sentence].append(eval)
        
        # 各文章グループで最高優先度の評価のみを使用
        scores = []
        for target_evals in evaluations_by_target.values():
            # 優先度でソート（昇順）
            target_evals.sort(key=lambda x: x.priority)
            if target_evals:  # 最高優先度（最小値）の評価を使用
                eval = target_evals[0]
                scores.append(eval.score)
        
        # 全体の平均を計算（重み付けなし）
        return sum(scores) / len(scores) if scores else 0.0

    def _parse_single_evaluation(self, evaluation_text: str) -> Dict[str, Any]:
        """
        単一の評価結果テキストを解析する
        
        Args:
            evaluation_text: OpenAI APIからの評価テキスト
            
        Returns:
            解析された評価結果
        """
        result = {
            "category": "",
            "score": 0.0,
            "priority": 3,
            "target_sentence": "",
            "feedback": [],
            "improvement_suggestions": []
        }

        current_section = None
        
        for line in evaluation_text.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line.startswith('カテゴリ:'):
                result['category'] = line.split(':', 1)[1].strip()
            elif line.startswith('スコア:'):
                try:
                    result['score'] = float(line.split(':', 1)[1].strip())
                except ValueError:
                    result['score'] = 0.0
            elif line.startswith('優先度:'):
                try:
                    result['priority'] = int(line.split(':', 1)[1].strip())
                except ValueError:
                    result['priority'] = 3
            elif line.startswith('対象文:'):
                result['target_sentence'] = line.split(':', 1)[1].strip()
            elif line.startswith('フィードバック:'):
                current_section = 'feedback'
            elif line.startswith('改善提案:'):
                current_section = 'improvement_suggestions'
            elif line.startswith('- '):
                if current_section == 'feedback':
                    result['feedback'].append(line[2:])
                elif current_section == 'improvement_suggestions':
                    result['improvement_suggestions'].append(line[2:])

        return result

    @staticmethod
    def _group_feedback_by_location(evaluation_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        タグごとにフィードバックをグループ化
        
        Args:
            evaluation_results (List[Dict[str, Any]]): 評価結果のリスト
            
        Returns:
            List[Dict[str, Any]]: グループ化されたフィードバック
        """
        grouped = {}
        
        for result in evaluation_results:
            for eval_result in result.get("evaluation_results", []):
                tag = eval_result["tag"]
                if tag not in grouped:
                    grouped[tag] = {
                        "tag": tag,
                        "text": eval_result["text"],
                        "feedback": []
                    }
                grouped[tag]["feedback"].append({
                    "category": result["category"],
                    "evaluation": eval_result["evaluation"]
                })
        
        return list(grouped.values())

    def _calculate_average_score(self, evaluations: List[Dict[str, Any]]) -> float:
        """
        評価結果の平均スコアを計算する

        Args:
            evaluations (List[Dict[str, Any]]): 評価結果のリスト

        Returns:
            float: 平均スコア
        """
        if not evaluations:
            return 0.0
            
        scores = [eval["score"] for eval in evaluations]
        return sum(scores) / len(scores) 