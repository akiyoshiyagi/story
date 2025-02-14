import os
from typing import Dict, Any, List
from openai import AzureOpenAI
from ..models.evaluation_result import EvaluationResult
from ..config import get_settings
import logging
import json
import asyncio
import httpx
import traceback

settings = get_settings()

# カスタムヘッダーの設定
def get_headers():
    """APIリクエスト用のヘッダーを生成する"""
    settings = get_settings()
    api_key = settings.OPENAI_API_KEY or "test-api-key"
    return {
        "Authorization": f"Bearer {api_key}",
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

# HTTPクライアントの設定
async def get_http_client():
    """APIリクエスト用のHTTPクライアントを生成する"""
    return httpx.Client(
        headers=get_headers(),
        timeout=httpx.Timeout(
            connect=10.0,
            read=settings.OPENAI_TIMEOUT,
            write=10.0,
            pool=settings.OPENAI_TIMEOUT
        ),
        limits=httpx.Limits(
            max_keepalive_connections=5,
            max_connections=10,
            keepalive_expiry=30.0
        ),
        verify=True,
        follow_redirects=True
    )

# GPT4o-mini用のクライアント
async def get_lite_client():
    try:
        http_client = await get_http_client()
        client = AzureOpenAI(
            api_key=settings.OPENAI_LITE_API_KEY,
            api_version=settings.OPENAI_LITE_API_VERSION,
            base_url=settings.OPENAI_LITE_API_BASE_URL,
            default_headers=get_headers(),
            http_client=http_client,
            max_retries=settings.OPENAI_MAX_RETRIES
        )
        logging.info(f"\n=== Liteクライアント初期化成功 ===")
        logging.info(f"エンドポイント: {settings.OPENAI_LITE_API_BASE_URL}")
        logging.info(f"APIバージョン: {settings.OPENAI_LITE_API_VERSION}")
        return client
    except Exception as e:
        logging.error(f"\n=== Liteクライアント初期化エラー ===")
        logging.error(f"エラータイプ: {type(e).__name__}")
        logging.error(f"エラー内容: {str(e)}")
        raise

# GPT4o sub用のクライアント
async def get_client():
    try:
        http_client = await get_http_client()
        client = AzureOpenAI(
            api_key=settings.OPENAI_API_KEY,
            api_version=settings.OPENAI_API_VERSION,
            base_url=settings.OPENAI_API_BASE_URL,
            default_headers=get_headers(),
            http_client=http_client,
            max_retries=settings.OPENAI_MAX_RETRIES
        )
        logging.info(f"\n=== メインクライアント初期化成功 ===")
        logging.info(f"エンドポイント: {settings.OPENAI_API_BASE_URL}")
        logging.info(f"APIバージョン: {settings.OPENAI_API_VERSION}")
        return client
    except Exception as e:
        logging.error(f"\n=== メインクライアント初期化エラー ===")
        logging.error(f"エラータイプ: {type(e).__name__}")
        logging.error(f"エラー内容: {str(e)}")
        raise

class EvaluationError(Exception):
    """評価処理に関するエラーを表すカスタム例外クラス"""
    def __init__(self, message: str, error_type: str, details: str):
        self.message = message
        self.error_type = error_type
        self.details = details
        super().__init__(message)

def create_error_evaluation(error: Exception) -> EvaluationResult:
    """エラー情報から評価結果オブジェクトを生成する"""
    if isinstance(error, EvaluationError):
        feedback = (
            f"評価中に{error.error_type}が発生しました。\n"
            f"詳細: {error.details}\n"
            "対応方法:\n"
            "• しばらく待ってから再試行してください\n"
            "• 文書の長さを調整してみてください\n"
            "• 問題が続く場合は管理者に連絡してください"
        )
    else:
        feedback = (
            f"予期せぬエラーが発生しました。\n"
            f"エラーの種類: {type(error).__name__}\n"
            f"エラーの詳細: {str(error)}\n"
            "対応方法:\n"
            "• 該当箇所の評価を再度実行してください\n"
            "• 問題が続く場合は管理者に連絡してください"
        )

    return EvaluationResult(
        category_id="ERROR",
        category_name="エラー",
        priority=999,  # エラーは最低優先度
        locations=[],  # 空のロケーションリスト
        score=0.0,
        feedback=feedback,
        target_text="",  # エラー時は対象テキストなし
        position=None,
        details=[{
            "error_type": type(error).__name__,
            "error_message": str(error),
            "is_evaluation_error": isinstance(error, EvaluationError)
        }]
    )

async def evaluate_document(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Azure OpenAI APIを使用して文書を評価する"""
    try:
        logging.info("\n=== 文書評価プロセスを開始 ===")
        logging.info(f"リクエストデータ: {json.dumps({k: str(v)[:100] + '...' if isinstance(v, str) and len(str(v)) > 100 else v for k, v in request_data.items()}, ensure_ascii=False)}")

        # 使用するクライアントを選択（デフォルトはGPT4o sub）
        use_lite = request_data.get('use_lite', False)
        
        # クライアントの初期化
        api_key = settings.OPENAI_LITE_API_KEY if use_lite else settings.OPENAI_API_KEY
        api_version = settings.OPENAI_LITE_API_VERSION if use_lite else settings.OPENAI_API_VERSION
        base_url = settings.OPENAI_LITE_API_BASE_URL if use_lite else settings.OPENAI_API_BASE_URL
        
        logging.info(f"\n=== クライアント初期化設定 ===")
        logging.info(f"APIバージョン: {api_version}")
        logging.info(f"ベースURL: {base_url}")
        
        selected_client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            base_url=base_url
        )
        
        model_name = request_data.get('model')
        if not model_name:
            model_name = settings.OPENAI_LITE_API_LLM_MODEL_NAME if use_lite else settings.OPENAI_API_LLM_MODEL_NAME
            logging.info(f"モデル名が指定されていないため、デフォルトのモデルを使用: {model_name}")

        # メッセージの検証
        if 'messages' not in request_data or not request_data['messages']:
            raise EvaluationError(
                message="メッセージが指定されていません",
                error_type="入力エラー",
                details="評価用のメッセージが空または存在しません"
            )

        # トークン数とtemperatureの設定
        max_tokens = request_data.get('max_tokens', settings.OPENAI_MAX_TOKENS)
        temperature = request_data.get('temperature', settings.OPENAI_TEMPERATURE)

        logging.info(f"\n=== API呼び出し設定 ===")
        logging.info(f"使用モデル: {model_name}")
        logging.info(f"最大トークン数: {max_tokens}")
        logging.info(f"Temperature: {temperature}")
        logging.info(f"メッセージ数: {len(request_data['messages'])}")

        try:
            # Azure OpenAI APIを呼び出し
            response = selected_client.chat.completions.create(
                model=model_name,
                messages=request_data['messages'],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=settings.OPENAI_TIMEOUT,
                presence_penalty=0.0,
                frequency_penalty=0.0,
                stream=False
            )

            if not response or not response.choices:
                raise EvaluationError(
                    message="APIレスポンスが無効です",
                    error_type="APIエラー",
                    details="APIからの応答が空または無効な形式です"
                )

            result = response.choices[0].message.content
            if not result or not result.strip():
                raise EvaluationError(
                    message="生成されたコンテンツが空です",
                    error_type="コンテンツエラー",
                    details="APIは応答しましたが、生成されたテキストが空でした"
                )

            logging.info("\n=== API呼び出し成功 ===")
            logging.info(f"生成されたコンテンツ長: {len(result)}")
            logging.info(f"トークン使用量: {response.usage.total_tokens}")
            logging.info(f"プロンプトトークン: {response.usage.prompt_tokens}")
            logging.info(f"完了トークン: {response.usage.completion_tokens}")

            return {
                'result': result,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }

        except Exception as api_error:
            error_type = "APIエラー"
            error_details = str(api_error)
            
            if "rate limit" in str(api_error).lower():
                error_type = "レート制限エラー"
                error_details = "APIの呼び出し回数制限に達しました。しばらく待ってから再試行してください。"
            elif "timeout" in str(api_error).lower():
                error_type = "タイムアウトエラー"
                error_details = "API呼び出しがタイムアウトしました。ネットワーク接続を確認してください。"
            elif "token" in str(api_error).lower():
                error_type = "トークン制限エラー"
                error_details = "トークン数が制限を超えています。文書の長さを調整してください。"
            elif "authentication" in str(api_error).lower() or "unauthorized" in str(api_error).lower():
                error_type = "認証エラー"
                error_details = "APIキーまたは認証情報が無効です。設定を確認してください。"
            
            logging.error(f"\n=== API呼び出しエラー ===")
            logging.error(f"エラー種別: {error_type}")
            logging.error(f"エラー詳細: {error_details}")
            logging.error(f"元のエラー: {str(api_error)}")
            
            raise EvaluationError(
                message=f"API呼び出しエラー: {str(api_error)}",
                error_type=error_type,
                details=error_details
            )

    except EvaluationError:
        raise

    except Exception as e:
        logging.error(f"\n=== 予期せぬエラー ===")
        logging.error(f"種別: {type(e).__name__}")
        logging.error(f"詳細: {str(e)}")
        raise EvaluationError(
            message="予期せぬエラーが発生しました",
            error_type="システムエラー",
            details=str(e)
        )

# デバッグ用のリクエスト情報ログ出力
async def log_request_info(client: AzureOpenAI, model_name: str, messages: List[Dict[str, str]]):
    try:
        logging.info("\n=== リクエスト情報 ===")
        logging.info(f"エンドポイント: {client.base_url}")
        logging.info(f"モデル名: {model_name}")
        logging.info(f"ヘッダー: {json.dumps(get_headers(), ensure_ascii=False, indent=2)}")
        logging.info(f"メッセージ数: {len(messages)}")
        logging.info(f"最初のメッセージ: {json.dumps(messages[0] if messages else {}, ensure_ascii=False)}")
    except Exception as e:
        logging.error(f"リクエスト情報のログ出力中にエラー: {str(e)}")

# クライアントの接続テスト（改善版）
async def test_client_connection(client: AzureOpenAI, model_name: str) -> bool:
    """クライアントの接続をテストする（改善版）"""
    try:
        # 接続テスト用の簡単なメッセージ
        test_message = [{"role": "user", "content": "テスト"}]
        
        # リクエスト情報をログ出力
        await log_request_info(client, model_name, test_message)
        
        # 直接completions APIを呼び出し
        response = client.chat.completions.create(
            model=model_name,
            messages=test_message,
            max_tokens=10,
            temperature=0.0,
            timeout=30.0
        )
        
        if response and response.choices:
            logging.info("API接続テスト成功")
            return True
            
        logging.error("API接続テスト失敗: レスポンスが無効です")
        return False
        
    except Exception as e:
        logging.error("\n=== API接続テスト失敗 ===")
        logging.error(f"エラータイプ: {type(e).__name__}")
        logging.error(f"エラーメッセージ: {str(e)}")
        
        if hasattr(e, 'response'):
            logging.error("\n=== エラーレスポンスの詳細 ===")
            logging.error(f"ステータスコード: {getattr(e.response, 'status_code', 'N/A')}")
            logging.error(f"レスポンスヘッダー: {getattr(e.response, 'headers', {})}")
            logging.error(f"レスポンス本文: {getattr(e.response, 'text', '')}")
        
        return False

async def call_openai_api(messages: List[Dict[str, str]], temperature: float = 0.7, use_lite: bool = False) -> str:
    try:
        logging.info("\n=== OpenAI API リクエスト開始 ===")
        logging.info(f"使用モデル: {'GPT4o-mini' if use_lite else 'GPT4o sub'}")
        logging.info(f"メッセージ数: {len(messages)}")
        logging.info(f"Temperature: {temperature}")

        if not messages:
            raise EvaluationError(
                message="メッセージが空です",
                error_type="入力エラー",
                details="評価用のメッセージが指定されていません"
            )

        # クライアントの初期化
        api_key = settings.OPENAI_LITE_API_KEY if use_lite else settings.OPENAI_API_KEY
        api_version = settings.OPENAI_LITE_API_VERSION if use_lite else settings.OPENAI_API_VERSION
        base_url = settings.OPENAI_LITE_API_BASE_URL if use_lite else settings.OPENAI_API_BASE_URL
        model_name = settings.OPENAI_LITE_API_LLM_MODEL_NAME if use_lite else settings.OPENAI_API_LLM_MODEL_NAME

        logging.info("\n=== クライアント初期化設定 ===")
        logging.info(f"APIバージョン: {api_version}")
        logging.info(f"ベースURL: {base_url}")
        logging.info(f"モデル名: {model_name}")

        selected_client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            base_url=base_url
        )

        # リトライ設定
        max_retries = settings.OPENAI_MAX_RETRIES
        base_delay = 2
        max_delay = 60

        for attempt in range(max_retries):
            try:
                logging.info(f"\n試行 {attempt + 1}/{max_retries}")

                # OpenAI APIの呼び出し
                response = selected_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=settings.OPENAI_MAX_TOKENS,
                    timeout=settings.OPENAI_TIMEOUT
                )

                if not response or not response.choices:
                    raise EvaluationError(
                        message="APIレスポンスが無効です",
                        error_type="APIエラー",
                        details="APIからの応答が空または無効な形式です"
                    )

                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise EvaluationError(
                        message="生成されたコンテンツが空です",
                        error_type="コンテンツエラー",
                        details="APIは応答しましたが、生成されたテキストが空でした"
                    )

                logging.info("\n=== API呼び出し成功 ===")
                logging.info(f"生成されたコンテンツ長: {len(content)}")
                if hasattr(response, 'usage'):
                    logging.info(f"トークン使用量: {response.usage.total_tokens}")

                return content

            except Exception as e:
                error_type = "APIエラー"
                error_details = str(e)
                delay = min(base_delay * (2 ** attempt), max_delay)

                if "rate limit" in str(e).lower():
                    error_type = "レート制限エラー"
                    error_details = "APIの呼び出し回数制限に達しました"
                elif "timeout" in str(e).lower():
                    error_type = "タイムアウトエラー"
                    error_details = "API呼び出しがタイムアウトしました"
                elif "token" in str(e).lower():
                    error_type = "トークン制限エラー"
                    error_details = "トークン数が制限を超えています"
                elif "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                    error_type = "認証エラー"
                    error_details = "APIキーまたは認証情報が無効です"
                elif "not found" in str(e).lower():
                    error_type = "エンドポイントエラー"
                    error_details = "APIエンドポイントが見つかりません"

                logging.error(f"\n=== 試行 {attempt + 1} 失敗 ===")
                logging.error(f"エラー種別: {error_type}")
                logging.error(f"エラー内容: {error_details}")

                if attempt < max_retries - 1:
                    logging.info(f"{delay}秒後に再試行します...")
                    await asyncio.sleep(delay)
                else:
                    raise EvaluationError(
                        message=f"OpenAI API呼び出しが{max_retries}回失敗しました",
                        error_type=error_type,
                        details=error_details
                    )

    except EvaluationError:
        raise

    except Exception as e:
        logging.error(f"\n=== OpenAI API 致命的エラー ===")
        logging.error(f"エラー種別: {type(e).__name__}")
        logging.error(f"エラー内容: {str(e)}")
        
        raise EvaluationError(
            message="予期せぬエラーが発生しました",
            error_type="システムエラー",
            details=f"エラーの種類: {type(e).__name__}\nエラーの詳細: {str(e)}"
        )

def parse_openai_response(response: Dict[str, Any]) -> List[EvaluationResult]:
    try:
        logging.info("\n=== 評価結果のパース開始 ===")
        
        # レスポンスの基本的な検証
        if not response or 'choices' not in response:
            raise EvaluationError(
                message="無効なレスポンス形式",
                error_type="パースエラー",
                details="必要なフィールドが存在しません"
            )
            
        evaluation_text = response['choices'][0]['message']['content']
        if not evaluation_text:
            raise EvaluationError(
                message="評価テキストが空です",
                error_type="パースエラー",
                details="APIからの応答テキストが空でした"
            )
            
        logging.info(f"パース対象テキスト:\n{evaluation_text}")
        
        try:
            # 余分な空白や改行を削除
            evaluation_text = evaluation_text.strip()
            
            # コードブロックマーカーの除去
            if evaluation_text.startswith('```'):
                evaluation_text = '\n'.join(evaluation_text.split('\n')[1:-1])
            
            # JSONとしてパースを試みる
            try:
                json_data = json.loads(evaluation_text)
            except json.JSONDecodeError as e:
                logging.error(f"JSONパースエラー: {str(e)}")
                logging.error(f"パース対象テキスト:\n{evaluation_text}")
                
                # 特殊文字や制御文字を除去して再試行
                cleaned_text = ''.join(char for char in evaluation_text if ord(char) >= 32)
                try:
                    json_data = json.loads(cleaned_text)
                except json.JSONDecodeError:
                    raise EvaluationError(
                        message="JSONパースエラー",
                        error_type="パースエラー",
                        details=f"応答のJSONパースに失敗: {str(e)}"
                    )
            
            # 必要なフィールドの存在確認と型チェック
            if not isinstance(json_data, dict):
                raise EvaluationError(
                    message="無効な応答形式",
                    error_type="パースエラー",
                    details="応答がJSON形式ではありません"
                )
            
            # 評価結果のリストを格納する配列
            evaluation_results = []
            
            # 単一の評価結果か複数の評価結果かを判定
            if isinstance(json_data.get('evaluations'), list):
                # 複数の評価結果の場合
                evaluations = json_data['evaluations']
            else:
                # 単一の評価結果の場合は配列に変換
                evaluations = [json_data]
            
            # 各評価結果をパース
            for evaluation in evaluations:
                category = evaluation.get('category')
                if not category:
                    continue
                
                # スコアの取得と検証
                try:
                    score = float(evaluation.get('score', 0.0))
                    if not 0.0 <= score <= 1.0:
                        raise ValueError("スコアは0から1の範囲である必要があります")
                except (TypeError, ValueError) as e:
                    continue
                
                # フィードバックの取得と形式統一
                feedback = evaluation.get('feedback', [])
                if isinstance(feedback, str):
                    feedback = [feedback]
                elif not isinstance(feedback, list):
                    feedback = [str(feedback)]
                
                # 改善提案の取得と統合
                suggestions = evaluation.get('improvement_suggestions', [])
                if isinstance(suggestions, str):
                    suggestions = [suggestions]
                elif not isinstance(suggestions, list):
                    suggestions = [str(suggestions)]
                
                # フィードバックと改善提案を統合
                all_feedback = []
                for item in feedback:
                    if item and not item.startswith('•'):
                        all_feedback.append(f"• {item}")
                    else:
                        all_feedback.append(item)
                
                if suggestions:
                    all_feedback.append("【改善提案】")
                    for item in suggestions:
                        if item and not item.startswith('•'):
                            all_feedback.append(f"• {item}")
                        else:
                            all_feedback.append(item)
                
                feedback_text = '\n'.join(all_feedback)
                
                # 評価結果オブジェクトを作成（各評価結果を個別に保持）
                result = EvaluationResult(
                    category_id=category,
                    category_name=category,  # カテゴリ名は後で設定される
                    priority=0,  # 優先度は後で設定される
                    locations=[{
                        "location": evaluation.get('target_text', '全体'),
                        "comments": [{
                            "criteria_id": category,
                            "content": feedback_text,
                            "score": score
                        }]
                    }],
                    score=score,
                    feedback=feedback_text,
                    target_text=evaluation.get('target_text', ''),
                    position=None  # 位置情報は後で設定される
                )
                
                evaluation_results.append(result)
            
            return evaluation_results
            
        except Exception as e:
            logging.error(f"評価結果のパース中にエラー: {str(e)}")
            logging.error(f"エラー詳細: {traceback.format_exc()}")
            raise EvaluationError(
                message="評価結果のパースに失敗",
                error_type="パースエラー",
                details=f"評価結果の解析中に予期せぬエラーが発生: {str(e)}"
            )
        
    except EvaluationError as e:
        logging.error(f"評価結果のパースでエラー: {e.error_type} - {e.details}")
        return [create_error_evaluation(e)]

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