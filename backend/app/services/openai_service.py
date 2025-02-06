import os
from typing import Dict, Any, List
from openai import AzureOpenAI
from ..models.evaluation import EvaluationResult
from ..config import get_settings
import logging
import json

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
        response = await selected_client.chat.completions.acreate(
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
        List[EvaluationResult]: 評価結果のリスト
    """
    try:
        # レスポンスの基本的な検証
        if not response or 'choices' not in response:
            raise ValueError("無効なレスポンス形式です")

        # 評価テキストを取得
        evaluation_text = response['choices'][0]['message']['content']
        if not evaluation_text:
            raise ValueError("評価テキストが空です")

        # 評価結果を格納するリスト
        evaluations = []

        # 評価テキストを解析
        current_evaluation = {}
        current_section = None

        for line in evaluation_text.split('\n'):
            line = line.strip()
            if not line:
                continue

            # 新しい評価セクションの開始を検出
            if line.startswith('カテゴリ:'):
                if current_evaluation:
                    # 前の評価を保存
                    evaluations.append(EvaluationResult(
                        criteria_id=current_evaluation.get('category', 'UNKNOWN'),
                        score=current_evaluation.get('score', 0.0),
                        feedback=current_evaluation.get('feedback', ''),
                        category=current_evaluation.get('category', 'UNKNOWN')
                    ))
                current_evaluation = {
                    'category': line.split(':', 1)[1].strip(),
                    'feedback': [],
                    'score': 0.0
                }
                current_section = 'category'

            elif line.startswith('スコア:'):
                try:
                    score_str = line.split(':', 1)[1].strip().rstrip('%')
                    current_evaluation['score'] = float(score_str) / 100
                except ValueError:
                    current_evaluation['score'] = 0.0
                current_section = 'score'

            elif line.startswith('フィードバック:'):
                current_section = 'feedback'
            elif line.startswith('改善提案:'):
                current_section = 'improvement'
            else:
                # 現在のセクションに応じてテキストを追加
                if current_section in ['feedback', 'improvement']:
                    if 'feedback' not in current_evaluation:
                        current_evaluation['feedback'] = []
                    current_evaluation['feedback'].append(line.strip('- ').strip())

        # 最後の評価を追加
        if current_evaluation:
            # フィードバックをテキストに変換
            feedback_text = '\n'.join(current_evaluation.get('feedback', []))
            evaluations.append(EvaluationResult(
                criteria_id=current_evaluation.get('category', 'UNKNOWN'),
                score=current_evaluation.get('score', 0.0),
                feedback=feedback_text,
                category=current_evaluation.get('category', 'UNKNOWN')
            ))

        return evaluations

    except Exception as e:
        logging.error(f"OpenAI APIレスポンスの解析中にエラーが発生: {str(e)}")
        # エラーが発生した場合でもデフォルトの評価結果を返す
        return [EvaluationResult(
            criteria_id="ERROR",
            score=0.0,
            feedback=f"評価結果の解析中にエラーが発生しました: {str(e)}",
            category="ERROR"
        )]

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
        
    # 単純な平均値を計算
    total_score = sum(eval.score for eval in evaluations)
    return total_score / len(evaluations) if evaluations else 0.0

async def call_openai_api(messages: List[Dict[str, str]], temperature: float = 0.7, use_lite: bool = False) -> str:
    """
    OpenAI APIを呼び出す
    
    Args:
        messages: メッセージのリスト
        temperature: 生成の多様性を制御するパラメータ
        use_lite: GPT4o-miniを使用するかどうか
        
    Returns:
        生成されたテキスト
    """
    try:
        logging.info("=== OpenAI API リクエスト ===")
        logging.info(f"メッセージ数: {len(messages)}")
        logging.info(f"Temperature: {temperature}")
        logging.info("最初のメッセージ:")
        logging.info(json.dumps(messages[0], ensure_ascii=False, indent=2))

        selected_client = lite_client if use_lite else client
        model_name = settings.OPENAI_LITE_API_LLM_MODEL_NAME if use_lite else settings.OPENAI_API_LLM_MODEL_NAME

        response = await selected_client.chat.completions.acreate(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=settings.OPENAI_MAX_TOKENS
        )

        logging.info("\n=== OpenAI API レスポンス ===")
        logging.info(f"モデル: {response.model}")
        logging.info(f"使用トークン: {response.usage.total_tokens}")
        logging.info(f"プロンプトトークン: {response.usage.prompt_tokens}")
        logging.info(f"完了トークン: {response.usage.completion_tokens}")
        
        content = response.choices[0].message.content
        logging.info("\n=== 生成されたコンテンツ ===")
        logging.info(content)
        
        return content
    except Exception as e:
        logging.error(f"OpenAI API呼び出し中にエラーが発生しました: {str(e)}")
        raise 