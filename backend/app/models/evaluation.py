"""
評価結果を表現するモデル
"""
from pydantic import BaseModel

class EvaluationResult(BaseModel):
    """評価結果モデル"""
    criteria_id: str
    score: float
    feedback: str
    category: str

    def to_dict(self) -> dict:
        """
        評価結果を辞書形式に変換
        
        Returns:
            dict: 評価結果の辞書表現
        """
        return {
            "criteria_id": self.criteria_id,
            "score": self.score,
            "feedback": self.feedback,
            "category": self.category
        }

    class Config:
        """設定クラス"""
        json_schema_extra = {
            "example": {
                "criteria_id": "前回討議振り返り評価",
                "score": 0.8,
                "feedback": "前回討議の振り返りが不十分です。",
                "category": "SUMMARY_ONLY"
            }
        } 