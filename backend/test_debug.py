import asyncio
import logging
from app.services.evaluation_service import EvaluationService
from app.services.openai_service import evaluate_document

# ロギングの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_evaluation():
    try:
        print("\n=== テスト開始 ===")
        service = EvaluationService()
        
        # テストデータ
        test_data = {
            "full_text": "これはテストです。",
            "summary": "テストの要約です。",
            "paragraphs": ["これはテストです。"],
            "title": "テスト文書"
        }
        
        print("\n=== 評価実行 ===")
        result = await service.evaluate_document(
            full_text=test_data["full_text"],
            summary=test_data["summary"],
            paragraphs=test_data["paragraphs"],
            title=test_data["title"]
        )
        
        print("\n=== 評価結果 ===")
        print(result)
        
    except Exception as e:
        print(f"\n=== エラー発生 ===")
        print(f"エラー種別: {type(e).__name__}")
        print(f"エラー内容: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_evaluation()) 