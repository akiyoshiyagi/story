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

def test_document_review():
    """文書評価エンドポイントのテスト"""
    url = "http://127.0.0.1:8001/api/review"
    payload = {
        "title": "テスト文書",
        "full_text": "これは文書の本文です。\n\n複数の段落があります。\n\nこれは3段落目です。",
        "summary": "これはテストのサマリーです。",
        "story": "これはテストのストーリーです。\n\nこれは2段落目です。",
        "paragraphs": [
            "これはテストのストーリーです。",
            "これは2段落目です。",
            "これは3段落目です。"
        ]
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        print("\n文書評価テストのリクエスト:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        
        response = requests.post(url, json=payload, headers=headers)
        print("\n文書評価テストのレスポンス:")
        print(f"Status Code: {response.status_code}")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        
        if response.status_code != 200:
            print(f"\nエラーレスポンス:")
            print(response.text)
    except Exception as e:
        print(f"\nエラー発生: {str(e)}")
        if hasattr(response, 'text'):
            print(f"レスポンステキスト: {response.text}")

def test_document_review_complex():
    """複雑なケースの文書評価テスト"""
    url = "http://127.0.0.1:8001/api/review"
    payload = {
        "title": "複雑なテストケース",
        "full_text": "前回の会議では、課題Aについて議論しました。\n\nしかしながら、その一方で、さらに、加えて、新たな問題が発生しています。\n\nまず第一に、コストの問題があります。次に、人材の問題があります。最後に、時間の制約があります。\n\n1. 予算超過\n2. リソース不足\n3. スケジュール遅延",
        "summary": "前回の会議での課題Aの議論を踏まえ、新たに3つの問題（コスト、人材、時間）が発生しており、対応が必要です。",
        "story": "課題Aについては、前回の会議で詳細な議論を行いました。\n\nその結果、以下の3つの新たな問題が明らかになりました。\n\nまず第一に、予算が当初の見積もりを20%超過しています。\n次に、必要な専門人材が2名不足しています。\n最後に、これらの影響でスケジュールが1ヶ月遅延する見込みです。",
        "paragraphs": [
            "課題Aについては、前回の会議で詳細な議論を行いました。",
            "その結果、以下の3つの新たな問題が明らかになりました。",
            "まず第一に、予算が当初の見積もりを20%超過しています。",
            "次に、必要な専門人材が2名不足しています。",
            "最後に、これらの影響でスケジュールが1ヶ月遅延する見込みです。"
        ]
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        print("\n複雑なケースの文書評価テストのリクエスト:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        
        response = requests.post(url, json=payload, headers=headers)
        print("\n複雑なケースの文書評価テストのレスポンス:")
        print(f"Status Code: {response.status_code}")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        
        if response.status_code != 200:
            print(f"\nエラーレスポンス:")
            print(response.text)
    except Exception as e:
        print(f"\nエラー発生: {str(e)}")
        if hasattr(response, 'text'):
            print(f"レスポンステキスト: {response.text}")

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
    
    # 文書評価テスト（シンプルケース）
    test_document_review()
    
    # 文書評価テスト（複雑ケース）
    test_document_review_complex() 