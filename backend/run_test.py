import json
from fastapi.testclient import TestClient
from app.main import app

def run_test():
    # テストクライアントを作成
    client = TestClient(app)
    
    # テストデータを読み込む
    with open('test_data.json', 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    print("\n=== テストデータ ===")
    print(f"タイトル: {test_data['title']}")
    print(f"サマリー: {test_data['summary']}")
    print(f"段落数: {len(test_data['paragraphs'])}")
    
    # APIリクエストを送信
    print("\n=== APIリクエスト送信 ===")
    response = client.post("/api/review", json=test_data)
    
    print(f"ステータスコード: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n=== 評価結果 ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"エラー: {response.text}")

if __name__ == "__main__":
    run_test() 