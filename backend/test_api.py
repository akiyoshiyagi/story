import requests
import json
from app.config import get_settings

settings = get_settings()

def test_health():
    """ヘルスチェックエンドポイントのテスト"""
    response = requests.get("http://127.0.0.1:8001/api/health")
    print("Health Check Response:", response.json())

def test_openai_lite():
    """GPT4o-miniを使用したテスト"""
    url = "http://127.0.0.1:8001/api/openai/evaluate"
    payload = {
        "model": settings.OPENAI_LITE_API_LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": "あなたは文書評価の専門家です。"},
            {"role": "user", "content": "これはテストメッセージです。"}
        ],
        "max_tokens": settings.OPENAI_MAX_TOKENS,
        "temperature": settings.OPENAI_TEMPERATURE,
        "use_lite": True
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print("\nGPT4o-mini Test Response:")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")
        if hasattr(response, 'text'):
            print(f"Response text: {response.text}")

def test_openai_sub():
    """GPT4o subを使用したテスト"""
    url = "http://127.0.0.1:8001/api/openai/evaluate"
    payload = {
        "model": settings.OPENAI_API_LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": "あなたは文書評価の専門家です。"},
            {"role": "user", "content": "これはテストメッセージです。"}
        ],
        "max_tokens": settings.OPENAI_MAX_TOKENS,
        "temperature": settings.OPENAI_TEMPERATURE,
        "use_lite": False
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print("\nGPT4o sub Test Response:")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")
        if hasattr(response, 'text'):
            print(f"Response text: {response.text}")

if __name__ == "__main__":
    # ヘルスチェック
    test_health()
    
    print("\nテスト設定:")
    print(f"LITE API URL: {settings.OPENAI_LITE_API_BASE_URL}")
    print(f"LITE Model: {settings.OPENAI_LITE_API_LLM_MODEL_NAME}")
    print(f"SUB API URL: {settings.OPENAI_API_BASE_URL}")
    print(f"SUB Model: {settings.OPENAI_API_LLM_MODEL_NAME}")
    
    # OpenAI APIテスト
    test_openai_lite()
    test_openai_sub() 