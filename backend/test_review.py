import requests
import json

# テストデータ
test_data = {
    "title": "テスト文書",
    "summary": "これはテスト用のサマリーです。重要なポイントを簡潔にまとめています。",
    "full_text": """これはテスト用の文書です。

まず、最初のポイントについて説明します。このポイントは非常に重要です。

次に、2つ目のポイントについて説明します。このポイントも同様に重要です。

最後に、まとめとして全体を振り返ります。""",
    "paragraphs": [
        "これはテスト用のサマリーです。重要なポイントを簡潔にまとめています。",
        "まず、最初のポイントについて説明します。このポイントは非常に重要です。",
        "次に、2つ目のポイントについて説明します。このポイントも同様に重要です。",
        "最後に、まとめとして全体を振り返ります。"
    ]
}

# APIリクエストを送信
response = requests.post(
    "http://localhost:8000/api/review",
    headers={"Content-Type": "application/json"},
    json=test_data
)

# レスポンスを表示
print("\n=== APIレスポンス ===")
print(f"ステータスコード: {response.status_code}")
if response.ok:
    result = response.json()
    print("\n=== 評価結果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
else:
    print(f"エラー: {response.text}") 