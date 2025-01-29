"""
評価処理を管理するサービス
"""
import logging
from typing import List, Dict, Any
from .text_analyzer import TextAnalyzer
from ..prompt_template.prompt import EVALUATION_CRITERIA, EVALUATION_PROMPT_TEMPLATE
from openai import AsyncAzureOpenAI
from ..models.evaluation import EvaluationResult
from ..config import get_settings

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
            full_text: 評価対象の文書テキスト全体
            summary: サマリー
            paragraphs: 段落のリスト
            title: タイトル
            
        Returns:
            評価結果を含む辞書
        """
        try:
            logger.debug(f"Starting document evaluation. Title: {title}")
            
            if not full_text or not title:
                raise ValueError("文書本文とタイトルは必須です")

            # 文章ごとの評価結果を格納する辞書
            evaluations_by_text = {}
            
            # 文書構造を作成
            document_structure = {
                "title": title,
                "summary": summary,
                "story": "\n".join(paragraphs),
                "body": full_text
            }

            # 各評価基準に対して評価を実行
            for criteria in EVALUATION_CRITERIA:
                # 評価対象範囲のテキストを取得
                target_text = self._get_evaluation_text(document_structure, criteria.get("applicable_to", []))
                
                # 評価プロンプトを構築
                evaluation_prompt = f"""
# 評価基準：{criteria["name"]}

{criteria["description"]}

# 評価対象テキスト：
{target_text}

# 評価指示
上記の評価基準に基づいて、評価対象テキストの各段落を必ず個別に分析し、以下の形式で結果を出力してください：

1. 問題が見つからない場合：
「問題なし」とだけ出力してください。

2. 問題が見つかった場合は、各段落について必ず以下の形式で出力してください：

対象文：[問題のある段落の冒頭部分]
問題あり：[問題の概要]
問題点：
- [具体的な問題点1]
- [具体的な問題点2]
改善提案：
- [具体的な改善案1]
- [具体的な改善案2]

---

各段落の評価は必ず上記の形式で出力し、段落ごとに「---」で区切ってください。
それ以外の説明は含めないでください。
"""

                try:
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
                    
                    # レスポンスから評価結果を解析
                    evaluation_results = self._parse_evaluation_text(
                        response.choices[0].message.content,
                        criteria["name"],
                        criteria["priority"]
                    )
                    
                    # 各評価結果を対象文ごとにグループ化
                    for eval_result in evaluation_results:
                        target_text = eval_result.target_sentence
                        if target_text not in evaluations_by_text:
                            evaluations_by_text[target_text] = []
                        evaluations_by_text[target_text].append(eval_result)

                except Exception as api_error:
                    logger.error(f"Error evaluating criteria {criteria['name']}: {str(api_error)}", exc_info=True)
                    # エラーが発生した場合は、最低評価を追加
                    error_eval = EvaluationResult(
                        category=criteria["name"],
                        score=0.0,
                        priority=criteria["priority"],
                        target_sentence=target_text[:100] + "...",  # 長すぎる場合は省略
                        feedback=[f"評価中にエラーが発生しました: {str(api_error)}"],
                        improvement_suggestions=["文章を見直し、再評価を行ってください"]
                    )
                    if error_eval.target_sentence not in evaluations_by_text:
                        evaluations_by_text[error_eval.target_sentence] = []
                    evaluations_by_text[error_eval.target_sentence].append(error_eval)

            if not evaluations_by_text:
                raise ValueError("評価結果が見つかりませんでした")

            # 各文章について最高優先度の評価のみを選択
            final_evaluations = []
            for target_text, evals in evaluations_by_text.items():
                if evals:
                    # 優先度でソート（昇順）し、最高優先度の評価を選択
                    evals.sort(key=lambda x: x.priority)
                    final_evaluations.append(evals[0])

            # 総合スコアを計算
            total_score = self._calculate_total_score(final_evaluations)
            logger.debug(f"Evaluation complete. Total score: {total_score}")

            # レスポンスの形式を修正
            response_data = {
                "total_score": total_score,
                "evaluations": [eval.to_dict() for eval in final_evaluations]
            }
            logger.debug(f"Sending response: {response_data}")
            return response_data

        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}", exc_info=True)
            raise ValueError(str(ve))
        except Exception as e:
            logger.error(f"Error during document evaluation: {str(e)}", exc_info=True)
            raise Exception(f"文書評価中にエラーが発生: {str(e)}")

    def _get_evaluation_text(self, document_structure: Dict[str, str], applicable_to: List[str]) -> str:
        """
        評価対象範囲に応じたテキストを取得する
        
        Args:
            document_structure: 文書構造を表す辞書
            applicable_to: 評価対象範囲のリスト
            
        Returns:
            評価対象テキスト（セクション区切り付き）
        """
        text_parts = []
        
        if "SUMMARY_ONLY" in applicable_to or "SUMMARY_AND_STORY" in applicable_to:
            summary = document_structure.get("summary", "").strip()
            if summary:
                text_parts.append(f"[サマリー]\n{summary}")
        
        if "SUMMARY_AND_STORY" in applicable_to or "STORY_AND_BODY" in applicable_to:
            story = document_structure.get("story", "").strip()
            if story:
                # 段落ごとに分割して番号を付与
                paragraphs = story.split("\n")
                numbered_paragraphs = []
                for i, para in enumerate(paragraphs, 1):
                    if para.strip():
                        numbered_paragraphs.append(f"[本文段落{i}]\n{para.strip()}")
                if numbered_paragraphs:
                    text_parts.append("\n\n".join(numbered_paragraphs))
        
        if "FULL_DOCUMENT" in applicable_to:
            body = document_structure.get("body", "").strip()
            if body:
                text_parts.append(f"[全文]\n{body}")
        
        return "\n\n---\n\n".join(filter(None, text_parts))

    def _parse_evaluation_text(
        self,
        evaluation_text: str,
        category_name: str,
        priority: int
    ) -> List[EvaluationResult]:
        """
        評価テキストを解析してEvaluationResultのリストを返す
        
        Args:
            evaluation_text: OpenAI APIからの評価テキスト
            category_name: 評価カテゴリ名
            priority: 評価の優先度
            
        Returns:
            List[EvaluationResult]: 評価結果のリスト
        """
        try:
            evaluations = []
            
            # 問題なしの場合は高評価で返す
            if "問題なし" in evaluation_text:
                return [EvaluationResult(
                    category=category_name,
                    score=1.0,
                    priority=priority,
                    target_sentence="",
                    feedback=["すべての評価基準を満たしています"],
                    improvement_suggestions=[]
                )]
            
            # 段落ごとの評価結果を分割
            paragraph_evaluations = evaluation_text.split("---")
            
            for paragraph_eval in paragraph_evaluations:
                if not paragraph_eval.strip():
                    continue
                
                lines = paragraph_eval.strip().split('\n')
                current_evaluation = {
                    "category": category_name,
                    "score": 0.5,
                    "priority": priority,
                    "target_sentence": "",
                    "feedback": [],
                    "improvement_suggestions": []
                }
                
                # セクション識別子を探す（[サマリー]、[本文段落N]、[全文]）
                section_identifier = ""
                for line in lines:
                    if line.strip().startswith("[") and line.strip().endswith("]"):
                        section_identifier = line.strip()
                        break
                
                current_section = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # セクション識別子はスキップ
                    if line.startswith("[") and line.endswith("]"):
                        continue
                    
                    # 対象文の特定
                    if line.startswith("対象文："):
                        current_evaluation["target_sentence"] = f"{section_identifier} {line.split('：', 1)[1].strip()}"
                    
                    # 問題ありの指摘
                    elif line.startswith("問題あり："):
                        problem_text = line.split("：", 1)[1].strip()
                        current_evaluation["feedback"].append(problem_text)
                    
                    # 問題点の詳細
                    elif line.startswith("問題点："):
                        current_section = "feedback"
                    
                    # 改善提案
                    elif line.startswith("改善提案："):
                        current_section = "improvement"
                    
                    # 箇条書きの処理
                    elif line.startswith("- ") or line.startswith("・"):
                        point_text = line[2:] if line.startswith("- ") else line[1:]
                        if point_text.strip():
                            if current_section == "feedback":
                                current_evaluation["feedback"].append(point_text.strip())
                            elif current_section == "improvement":
                                current_evaluation["improvement_suggestions"].append(point_text.strip())
                
                # 有効な評価結果のみを追加
                if current_evaluation["target_sentence"] and (current_evaluation["feedback"] or current_evaluation["improvement_suggestions"]):
                    evaluations.append(EvaluationResult(**current_evaluation))
            
            # 評価結果がない場合は、デフォルトの評価を追加
            if not evaluations:
                evaluations.append(EvaluationResult(
                    category=category_name,
                    score=1.0,
                    priority=priority,
                    target_sentence="",
                    feedback=["評価基準に関する問題は見つかりませんでした"],
                    improvement_suggestions=[]
                ))
            
            return evaluations
            
        except Exception as e:
            logger.error(f"Error parsing evaluation text: {str(e)}", exc_info=True)
            raise Exception(f"評価テキストの解析中にエラーが発生: {str(e)}")

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
            
        # 優先度に基づいて重み付けを行う
        weights = {1: 1.0, 2: 0.7, 3: 0.3}  # 優先度ごとの重み
        
        # 各文章に対する評価を優先度でグループ化
        evaluations_by_target = {}
        for eval in evaluations:
            if eval.target_sentence not in evaluations_by_target:
                evaluations_by_target[eval.target_sentence] = []
            evaluations_by_target[eval.target_sentence].append(eval)
        
        # 各文章グループで最高優先度の評価のみを使用
        weighted_scores = []
        for target_evals in evaluations_by_target.values():
            # 優先度でソート（昇順）
            target_evals.sort(key=lambda x: x.priority)
            if target_evals:  # 最高優先度（最小値）の評価を使用
                eval = target_evals[0]
                weighted_scores.append(eval.score * weights.get(eval.priority, 0.5))
        
        # 全体の平均を計算
        return sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.0

    async def _evaluate_single_criteria(
        self, 
        criteria: Dict[str, str],
        tagged_sections: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        単一の評価基準で評価を実行
        
        Args:
            criteria: 評価基準の情報
            tagged_sections: タグ付けされた文書セクション
            
        Returns:
            評価結果を含む辞書
        """
        evaluation_results = []
        logger.debug(f"Evaluating criteria: {criteria['name']}")
        
        # 各文章を個別に評価
        for tag, text in tagged_sections.items():
            if tag.startswith(("Summary", "Story")):  # SummaryとStoryのみを評価
                try:
                    # 評価プロンプトを構築
                    evaluation_prompt = f"""
以下の文章を「{criteria['name']}」の観点で評価してください。

評価対象文章：
{text}

評価基準：
{criteria['description']}

以下の形式で評価結果を提供してください：
カテゴリ: {criteria['name']}
スコア: [0-1の数値]
優先度: {criteria['priority']}
対象文: [評価対象の文章]
フィードバック:
- [具体的な問題点]
改善提案:
- [具体的な修正案]
"""

                    # OpenAI APIを呼び出し
                    logger.debug(f"Calling Azure OpenAI API for tag: {tag}")
                    response = await self.client.chat.completions.create(
                        model=settings.OPENAI_API_LLM_MODEL_NAME,
                        messages=[
                            {"role": "system", "content": "あなたはビジネス文書の評価専門家です。"},
                            {"role": "user", "content": evaluation_prompt}
                        ],
                        max_tokens=settings.OPENAI_MAX_TOKENS,
                        temperature=settings.OPENAI_TEMPERATURE
                    )

                    # レスポンスを解析
                    evaluation = self._parse_single_evaluation(response.choices[0].message.content)
                    
                    result = {
                        "tag": tag,
                        "text": text,
                        "evaluation": evaluation
                    }
                    evaluation_results.append(result)
                    logger.debug(f"Evaluation complete for tag: {tag}")

                except Exception as e:
                    logger.error(f"Error evaluating tag {tag}: {str(e)}", exc_info=True)
                    # エラーが発生した場合は、最低評価を返す
                    result = {
                        "tag": tag,
                        "text": text,
                        "evaluation": {
                            "category": criteria["name"],
                            "score": 0.0,
                            "priority": criteria["priority"],
                            "target_sentence": text,
                            "feedback": [f"評価中にエラーが発生しました: {str(e)}"],
                            "improvement_suggestions": ["文章を見直し、再評価を行ってください"]
                        }
                    }
                    evaluation_results.append(result)

        # 評価結果が空の場合
        if not evaluation_results:
            logger.warning(f"No evaluation results for criteria: {criteria['name']}")
            return {
                "category": criteria["name"],
                "score": 0.0,
                "evaluation_results": []
            }

        # 全体のスコアを計算（最も低いスコアを採用）
        min_score = min(result["evaluation"]["score"] for result in evaluation_results)
        logger.debug(f"Calculated score for criteria {criteria['name']}: {min_score}")
        return {
            "category": criteria["name"],
            "score": min_score,
            "evaluation_results": evaluation_results
        }

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