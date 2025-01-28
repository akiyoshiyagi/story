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

            # システムプロンプトを設定
            system_prompt = """あなたはビジネス文書の評価と改善提案を行う専門家です。
以下の観点で文書を評価し、具体的なフィードバックと改善提案を提供してください：

1. 論理構造の評価
2. 文章の明確さと簡潔さ
3. ビジネス文書としての適切性
4. 用語の一貫性
5. 文の接続と流れ

各評価は以下の形式で提供してください：
カテゴリ: [評価カテゴリ名]
スコア: [0-1の数値]
優先度: [1-3の整数、1が最も高い]
対象文: [評価対象の文章]
フィードバック:
- [具体的な問題点1]
- [具体的な問題点2]
改善提案:
- [具体的な修正案1]
- [具体的な修正案2]"""

            # 評価用のプロンプトを構築
            evaluation_prompt = f"以下の文書を評価してください：\n\nタイトル：{title}\n\n"
            if summary:
                evaluation_prompt += f"サマリー：\n{summary}\n\n"
            evaluation_prompt += f"本文：\n{full_text}"

            # Azure OpenAI APIを呼び出し
            logger.debug("Calling Azure OpenAI API")
            try:
                response = await self.client.chat.completions.create(
                    model=settings.OPENAI_API_LLM_MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    max_tokens=settings.OPENAI_MAX_TOKENS,
                    temperature=settings.OPENAI_TEMPERATURE
                )
                
                # レスポンスから評価テキストを取得
                evaluation_text = response.choices[0].message.content
                logger.debug(f"Received evaluation text: {evaluation_text}")
                
                # 評価テキストを解析
                evaluations = self._parse_evaluation_text(evaluation_text)
                
                if not evaluations:
                    raise ValueError("評価結果が見つかりませんでした")

                # 総合スコアを計算
                total_score = self._calculate_total_score(evaluations)
                logger.debug(f"Evaluation complete. Total score: {total_score}")

                # レスポンスの形式を修正
                response_data = {
                    "total_score": total_score,
                    "evaluations": [eval.to_dict() for eval in evaluations]
                }
                logger.debug(f"Sending response: {response_data}")
                return response_data

            except Exception as api_error:
                logger.error(f"OpenAI API error: {str(api_error)}", exc_info=True)
                raise Exception(f"OpenAI APIでエラーが発生: {str(api_error)}")

        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}", exc_info=True)
            raise ValueError(str(ve))
        except Exception as e:
            logger.error(f"Error during document evaluation: {str(e)}", exc_info=True)
            raise Exception(f"文書評価中にエラーが発生: {str(e)}")

    def _parse_evaluation_text(self, evaluation_text: str) -> List[EvaluationResult]:
        """評価テキストを解析してEvaluationResultのリストを返す"""
        try:
            evaluations = []
            current_evaluation = {
                'category': '',
                'score': 0.0,
                'priority': 3,
                'target_sentence': '',
                'feedback': [],
                'improvement_suggestions': []
            }
            
            for line in evaluation_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('カテゴリ:'):
                    if current_evaluation.get('category'):
                        if self._is_valid_evaluation(current_evaluation):
                            evaluations.append(EvaluationResult(**current_evaluation))
                        current_evaluation = {
                            'category': '',
                            'score': 0.0,
                            'priority': 3,
                            'target_sentence': '',
                            'feedback': [],
                            'improvement_suggestions': []
                        }
                    current_evaluation['category'] = line.split(':', 1)[1].strip()
                elif line.startswith('スコア:'):
                    score_str = line.split(':', 1)[1].strip()
                    try:
                        score = float(score_str)
                        if 0 <= score <= 1:
                            current_evaluation['score'] = score
                        else:
                            current_evaluation['score'] = 0.0
                            logger.warning(f"Invalid score value: {score_str}, using default 0.0")
                    except ValueError:
                        current_evaluation['score'] = 0.0
                        logger.warning(f"Could not parse score: {score_str}, using default 0.0")
                elif line.startswith('優先度:'):
                    priority_str = line.split(':', 1)[1].strip()
                    try:
                        priority = int(priority_str)
                        if 1 <= priority <= 3:
                            current_evaluation['priority'] = priority
                        else:
                            current_evaluation['priority'] = 3
                            logger.warning(f"Invalid priority value: {priority_str}, using default 3")
                    except ValueError:
                        current_evaluation['priority'] = 3
                        logger.warning(f"Could not parse priority: {priority_str}, using default 3")
                elif line.startswith('対象文:'):
                    current_evaluation['target_sentence'] = line.split(':', 1)[1].strip()
                elif line.startswith('フィードバック:'):
                    current_evaluation['feedback'] = []
                elif line.startswith('改善提案:'):
                    current_evaluation['improvement_suggestions'] = []
                elif line.startswith('- '):
                    if current_evaluation.get('improvement_suggestions') is not None:
                        current_evaluation['improvement_suggestions'].append(line[2:])
                    elif current_evaluation.get('feedback') is not None:
                        current_evaluation['feedback'].append(line[2:])
            
            # 最後の評価を追加
            if self._is_valid_evaluation(current_evaluation):
                evaluations.append(EvaluationResult(**current_evaluation))
            
            if not evaluations:
                logger.warning("No valid evaluations found in the response")
                return []
                
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
            
        weights = {1: 1.0, 2: 0.7, 3: 0.3}  # 優先度ごとの重み
        
        weighted_sum = sum(eval.score * weights.get(eval.priority, 0.5) for eval in evaluations)
        total_weight = sum(weights.get(eval.priority, 0.5) for eval in evaluations)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0

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