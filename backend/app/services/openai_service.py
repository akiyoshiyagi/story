import os
from typing import Dict, Any, List
from openai import AzureOpenAI
from ..models.evaluation import EvaluationResult
from ..config import get_settings

settings = get_settings()

# GPT4o-mini用のクライアント
lite_client = AzureOpenAI(
    api_key=settings.OPENAI_LITE_API_KEY,
    api_version=settings.OPENAI_LITE_API_VERSION,
    azure_endpoint=settings.OPENAI_LITE_API_BASE_URL,
    timeout=settings.OPENAI_TIMEOUT,
    max_retries=settings.OPENAI_MAX_RETRIES
)

# GPT4o sub用のクライアント
client = AzureOpenAI(
    api_key=settings.OPENAI_API_KEY,
    api_version=settings.OPENAI_API_VERSION,
    azure_endpoint=settings.OPENAI_API_BASE_URL,
    timeout=settings.OPENAI_TIMEOUT,
    max_retries=settings.OPENAI_MAX_RETRIES
)

async def evaluate_document(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Azure OpenAI APIを使用して文書を評価する
    
    Args:
        request_data: OpenAI APIリクエストデータ
        
    Returns:
        評価結果を含む辞書
    """
    try:
        # 使用するクライアントを選択（デフォルトはGPT4o sub）
        use_lite = request_data.get('use_lite', False)
        selected_client = lite_client if use_lite else client
        model_name = request_data.get('model')

        # Azure OpenAI APIを呼び出し
        response = selected_client.chat.completions.create(
            model=model_name,
            messages=request_data['messages'],
            max_tokens=request_data['max_tokens'],
            temperature=request_data['temperature']
        )

        # レスポンスから評価結果を抽出
        result = response.choices[0].message.content

        return {
            'result': result,
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
        }

    except Exception as e:
        raise Exception(f"Azure OpenAI API評価中にエラーが発生: {str(e)}")

def parse_openai_response(response: Dict[str, Any]) -> List[EvaluationResult]:
    """
    OpenAI APIのレスポンスを解析して評価結果に変換する
    
    Args:
        response: OpenAI APIレスポンス
        
    Returns:
        評価結果のリスト
    """
    try:
        # レスポンスから評価テキストを取得
        evaluation_text = response['choices'][0]['message']['content']
        
        # 評価テキストを解析して構造化データに変換
        # この部分は、OpenAI APIの出力形式に応じて適切に実装する必要があります
        evaluations = []
        
        # 評価テキストを行ごとに処理
        current_evaluation = {}
        for line in evaluation_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('カテゴリ:'):
                if current_evaluation:
                    evaluations.append(EvaluationResult(**current_evaluation))
                    current_evaluation = {}
                current_evaluation['category'] = line.split(':', 1)[1].strip()
            elif line.startswith('スコア:'):
                score_str = line.split(':', 1)[1].strip()
                current_evaluation['score'] = float(score_str)
            elif line.startswith('優先度:'):
                priority_str = line.split(':', 1)[1].strip()
                current_evaluation['priority'] = int(priority_str)
            elif line.startswith('対象文:'):
                current_evaluation['target_sentence'] = line.split(':', 1)[1].strip()
            elif line.startswith('フィードバック:'):
                current_evaluation['feedback'] = []
            elif line.startswith('改善提案:'):
                current_evaluation['improvement_suggestions'] = []
            elif current_evaluation.get('feedback') is not None and not line.startswith('改善提案:'):
                current_evaluation['feedback'].append(line)
            elif current_evaluation.get('improvement_suggestions') is not None:
                current_evaluation['improvement_suggestions'].append(line)
        
        # 最後の評価を追加
        if current_evaluation:
            evaluations.append(EvaluationResult(**current_evaluation))
        
        return evaluations

    except Exception as e:
        raise Exception(f"OpenAI APIレスポンスの解析中にエラーが発生: {str(e)}")

def calculate_total_score(evaluations: List[EvaluationResult]) -> float:
    """
    評価結果から総合スコアを計算する
    
    Args:
        evaluations: 評価結果のリスト
        
    Returns:
        総合スコア（0-1の範囲）
    """
    if not evaluations:
        return 0.0
        
    # 優先度に基づいて重み付けを行う
    weights = {1: 1.0, 2: 0.7, 3: 0.3}  # 優先度ごとの重み
    
    weighted_sum = sum(eval.score * weights.get(eval.priority, 0.5) for eval in evaluations)
    total_weight = sum(weights.get(eval.priority, 0.5) for eval in evaluations)
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0 