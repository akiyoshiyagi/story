"""
評価サービスのテストモジュール
"""
import pytest
import json
import os
from app.services.evaluation_service import EvaluationService
from app.services.openai_service import parse_openai_response
from app.models.evaluation_result import EvaluationResult
from app.prompt_template.prompt import EVALUATION_TARGETS
from typing import Dict, Any, List

# 非同期テストのデフォルトスコープを設定
pytest.asyncio_fixture_scope = "function"

@pytest.fixture(autouse=True)
def setup_test_env():
    """テスト用の環境変数を設定するフィクスチャ"""
    # 元の環境変数を保存
    original_env = {
        "AZURE_OPENAI_API_KEY": os.environ.get("AZURE_OPENAI_API_KEY"),
        "AZURE_OPENAI_ENDPOINT": os.environ.get("AZURE_OPENAI_ENDPOINT"),
        "OPENAI_API_VERSION": os.environ.get("OPENAI_API_VERSION"),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "OPENAI_API_TYPE": os.environ.get("OPENAI_API_TYPE"),
        "OPENAI_API_BASE_URL": os.environ.get("OPENAI_API_BASE_URL"),
        "OPENAI_API_LLM_MODEL_NAME": os.environ.get("OPENAI_API_LLM_MODEL_NAME")
    }
    
    # テスト用の環境変数を設定
    os.environ["AZURE_OPENAI_API_KEY"] = "test-api-key"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test-endpoint.azure.openai.com"
    os.environ["OPENAI_API_VERSION"] = "2024-02-15-preview"
    os.environ["OPENAI_API_KEY"] = "test-api-key"
    os.environ["OPENAI_API_TYPE"] = "azure"
    os.environ["OPENAI_API_BASE_URL"] = "https://test-endpoint.azure.openai.com"
    os.environ["OPENAI_API_LLM_MODEL_NAME"] = "gpt-4"
    
    yield
    
    # テスト後に元の環境変数を復元
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)

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

# 新しい評価対象タイプのテストデータ
EVALUATION_TARGET_TEST_DATA = {
    "FULL_SUMMARY_AND_STORY": {
        "title": "サマリーとストーリーのテスト",
        "summary": "これはサマリーです。",
        "full_text": "これは全文です。",
        "paragraphs": ["これはストーリー1です。", "これはストーリー2です。"]
    },
    "FULL_SUMMARY": {
        "title": "サマリーのみのテスト",
        "summary": "これはサマリー1です。\nこれはサマリー2です。",
        "full_text": "これは全文です。",
        "paragraphs": []
    },
    "CONSECUTIVE_SUMMARY": {
        "title": "連続するサマリーのテスト",
        "summary": "これはサマリー1です。\nこれはサマリー2です。\nこれはサマリー3です。",
        "full_text": "これは全文です。",
        "paragraphs": []
    }
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
async def test_evaluation_target_types(evaluation_service):
    """新しい評価対象タイプのテスト"""
    print("\n=== 評価対象タイプのテスト ===")
    
    for target_type, test_data in EVALUATION_TARGET_TEST_DATA.items():
        print(f"\nテスト対象: {target_type}")
        try:
            result = await evaluation_service.evaluate_document(
                full_text=test_data["full_text"],
                summary=test_data["summary"],
                paragraphs=test_data["paragraphs"],
                title=test_data["title"]
            )
            
            assert result is not None, f"{target_type}の評価結果がNoneです"
            assert "evaluations" in result, f"{target_type}のevaluationsが結果に含まれていません"
            assert "totalScore" in result, f"{target_type}のtotalScoreが結果に含まれていません"
            
            print(f"テスト成功: {target_type}")
            
        except Exception as e:
            print(f"テスト失敗 ({target_type}): {str(e)}")
            raise

@pytest.mark.asyncio
async def test_error_recovery(evaluation_service):
    """エラーからの回復機能のテスト"""
    print("\n=== エラー回復機能のテスト ===")
    
    try:
        # エラーを含む評価を実行
        result = await evaluation_service.evaluate_document(
            full_text="",  # 空の本文でエラーを発生させる
            summary=SAMPLE_DOCUMENT["summary"],
            paragraphs=SAMPLE_DOCUMENT["paragraphs"],
            title=SAMPLE_DOCUMENT["title"]
        )
        
        assert result is not None, "エラー時の評価結果がNoneです"
        assert "error" in result, "エラー情報が含まれていません"
        assert result["totalScore"] == 0.0, "エラー時のスコアが0ではありません"
        assert len(result["evaluations"]) == 0, "エラー時に評価が生成されています"
        
        # 正常なデータで評価を実行
        result = await evaluation_service.evaluate_document(
            full_text=SAMPLE_DOCUMENT["full_text"],
            summary=SAMPLE_DOCUMENT["summary"],
            paragraphs=SAMPLE_DOCUMENT["paragraphs"],
            title=SAMPLE_DOCUMENT["title"]
        )
        
        assert result is not None, "回復後の評価結果がNoneです"
        assert "evaluations" in result, "回復後のevaluationsが結果に含まれていません"
        assert result["totalScore"] > 0.0, "回復後のスコアが0です"
        
        print("テスト成功: エラー回復機能")
        
    except Exception as e:
        print(f"テスト失敗: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_partial_evaluation_failure(evaluation_service):
    """一部の評価が失敗した場合のテスト"""
    print("\n=== 部分的評価失敗のテスト ===")
    
    try:
        # 一部の評価基準でエラーが発生する状況を作成
        document = {
            **SAMPLE_DOCUMENT,
            "paragraphs": [""]  # 空の段落を含める
        }
        
        result = await evaluation_service.evaluate_document(
            full_text=document["full_text"],
            summary=document["summary"],
            paragraphs=document["paragraphs"],
            title=document["title"]
        )
        
        assert result is not None, "部分的失敗時の評価結果がNoneです"
        assert "evaluations" in result, "部分的失敗時のevaluationsが結果に含まれていません"
        
        # エラーを含む評価と成功した評価の両方が存在することを確認
        has_error = False
        has_success = False
        for evaluation in result["evaluations"]:
            if "error" in evaluation:
                has_error = True
            else:
                has_success = True
        
        assert has_error and has_success, "部分的な失敗が正しく処理されていません"
        
        print("テスト成功: 部分的評価失敗")
        
    except Exception as e:
        print(f"テスト失敗: {str(e)}")
        raise

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
                "content": json.dumps({
                    "category": "テストカテゴリ",
                    "score": 0.85,
                    "feedback": ["フィードバック1", "フィードバック2"],
                    "improvement_suggestions": ["改善提案1", "改善提案2"],
                    "target_text": "テスト対象テキスト"
                })
            }
        }]
    }

    try:
        results = parse_openai_response(valid_response)
        assert len(results) == 1, "評価結果が1つ返されるべきです"
        
        result = results[0]
        assert isinstance(result, EvaluationResult), "結果はEvaluationResultのインスタンスであるべきです"
        assert result.category_id == "テストカテゴリ", "カテゴリIDが正しくありません"
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
        
        # 新しい評価対象タイプのテスト
        await test_evaluation_target_types(service)
        
        # エラー回復機能のテスト
        await test_error_recovery(service)
        
        # 部分的評価失敗のテスト
        await test_partial_evaluation_failure(service)
        
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