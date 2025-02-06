import pytest
import json
from app.services.evaluation_service import EvaluationService
from app.services.openai_service import parse_openai_response
from app.models.evaluation import EvaluationResult
from typing import Dict, Any, List

# 非同期テストのデフォルトスコープを設定
pytest.asyncio_fixture_scope = "function"

# テストデータ
SAMPLE_DOCUMENT = {
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

EDGE_CASE_DOCUMENT = {
    "title": "",  # 空のタイトル
    "summary": "  ",  # 空白のみのサマリー
    "full_text": "\n\n\n",  # 改行のみの本文
    "paragraphs": []  # 空の段落リスト
}

ERROR_CASE_DOCUMENT = {
    "title": None,  # 無効なタイトル
    "summary": 123,  # 無効な型のサマリー
    "full_text": {"invalid": "type"},  # 無効な型の本文
    "paragraphs": None  # 無効な段落リスト
}

@pytest.fixture
def evaluation_service():
    """EvaluationServiceのインスタンスを提供するフィクスチャ"""
    return EvaluationService()

@pytest.mark.asyncio
async def test_basic_evaluation(evaluation_service):
    """基本的な評価機能のテスト"""
    print("\n=== 基本的な評価機能のテスト ===")
    
    try:
        result = await evaluation_service.evaluate_document(
            full_text=SAMPLE_DOCUMENT["full_text"],
            summary=SAMPLE_DOCUMENT["summary"],
            paragraphs=SAMPLE_DOCUMENT["paragraphs"],
            title=SAMPLE_DOCUMENT["title"]
        )
        
        assert result is not None, "評価結果がNoneです"
        assert "evaluations" in result, "evaluationsが結果に含まれていません"
        assert "totalScore" in result, "totalScoreが結果に含まれていません"
        assert isinstance(result["totalScore"], float), "totalScoreが数値ではありません"
        assert 0 <= result["totalScore"] <= 1, "totalScoreが0-1の範囲外です"
        
        print("テスト成功: 基本的な評価機能")
        
    except Exception as e:
        print(f"テスト失敗: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_edge_cases(evaluation_service):
    """エッジケースのテスト"""
    print("\n=== エッジケースのテスト ===")
    
    try:
        result = await evaluation_service.evaluate_document(
            full_text=EDGE_CASE_DOCUMENT["full_text"],
            summary=EDGE_CASE_DOCUMENT["summary"],
            paragraphs=EDGE_CASE_DOCUMENT["paragraphs"],
            title=EDGE_CASE_DOCUMENT["title"]
        )
        
        assert result is not None, "エッジケースの評価結果がNoneです"
        assert result["totalScore"] == 0.0, "空の入力に対するスコアが0ではありません"
        assert len(result["evaluations"]) == 0, "空の入力に対して評価が生成されています"
        
        print("テスト成功: エッジケース")
        
    except Exception as e:
        print(f"テスト失敗: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_error_handling(evaluation_service):
    """エラーハンドリングのテスト"""
    print("\n=== エラーハンドリングのテスト ===")
    
    try:
        result = await evaluation_service.evaluate_document(
            full_text=ERROR_CASE_DOCUMENT["full_text"],
            summary=ERROR_CASE_DOCUMENT["summary"],
            paragraphs=ERROR_CASE_DOCUMENT["paragraphs"],
            title=ERROR_CASE_DOCUMENT["title"]
        )
        
        assert result is not None, "エラーケースの評価結果がNoneです"
        assert "error" in result, "エラー情報が含まれていません"
        assert result["totalScore"] == 0.0, "エラー時のスコアが0ではありません"
        
        print("テスト成功: エラーハンドリング")
        
    except Exception as e:
        print(f"テスト失敗: {str(e)}")
        raise

def test_openai_response_parsing():
    """OpenAI APIレスポンスのパース機能のテスト"""
    print("\n=== OpenAI APIレスポンスのパース機能のテスト ===")

    valid_response = {
        "choices": [{
            "message": {
                "content": """カテゴリ: テストカテゴリ
スコア: 85
フィードバック:
- フィードバック1
- フィードバック2
改善提案:
- 改善提案1
- 改善提案2"""
            }
        }]
    }

    try:
        results = parse_openai_response(valid_response)
        assert len(results) == 1, "評価結果が1つ返されるべきです"
        
        result = results[0]
        assert isinstance(result, EvaluationResult), "結果はEvaluationResultのインスタンスであるべきです"
        assert result.criteria_id == "テストカテゴリ", "カテゴリIDが正しくありません"
        assert result.score == 0.85, "スコアが正しくありません"
        assert "フィードバック1" in result.feedback, "フィードバックが正しくありません"
        
        print("テスト成功: OpenAI APIレスポンスのパース")
        
    except Exception as e:
        print(f"テスト失敗: {str(e)}")
        raise

def test_score_calculation(evaluation_service):
    """スコア計算機能のテスト"""
    print("\n=== スコア計算機能のテスト ===")
    
    test_evaluations = [
        {
            "categoryId": "FULL_TEXT_RHETORIC",
            "score": 0.8,
            "criteriaId": "test1"
        },
        {
            "categoryId": "SUMMARY_LOGIC_FLOW",
            "score": 0.8,
            "criteriaId": "test2"
        },
        {
            "categoryId": "DETAIL_RHETORIC",
            "score": 0.8,
            "criteriaId": "test3"
        }
    ]
    
    try:
        score = evaluation_service.calculate_average_score(test_evaluations)
        assert 0 <= score <= 1, "スコアが0-1の範囲外です"
        assert isinstance(score, float), "スコアが数値ではありません"
        
        # すべてのスコアが0.8の場合、重み付けがあっても最終スコアは0.8になるはずです
        assert abs(score - 0.8) < 0.01, "スコアの計算が正しくありません"
        
        print("テスト成功: スコア計算")
        
    except Exception as e:
        print(f"テスト失敗: {str(e)}")
        raise

if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        service = EvaluationService()
        
        print("\n=== テスト実行開始 ===")
        
        # 基本機能のテスト
        await test_basic_evaluation(service)
        
        # エッジケースのテスト
        await test_edge_cases(service)
        
        # エラーハンドリングのテスト
        await test_error_handling(service)
        
        # OpenAI APIレスポンスのパースのテスト
        test_openai_response_parsing()
        
        # スコア計算のテスト
        test_score_calculation(service)
        
        print("\n=== すべてのテストが完了しました ===")
    
    asyncio.run(run_tests()) 