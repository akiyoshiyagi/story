"""
評価結果を表現するモデル
"""
from pydantic import BaseModel
from typing import List, Dict, Optional

class Comment(BaseModel):
    """
    評価基準ごとのコメント
    """
    criteria_id: str
    content: str
    score: float

class LocationComments(BaseModel):
    """
    該当箇所ごとのコメントグループ
    """
    location: str  # テキスト内の該当箇所（例：段落番号や文章の範囲）
    comments: List[Comment]

class Position(BaseModel):
    """
    テキスト内の位置情報
    """
    start: int  # テキスト内の開始位置
    end: int    # テキスト内の終了位置

class EvaluationResult(BaseModel):
    """
    カテゴリごとの評価結果
    """
    category_id: str
    category_name: str
    priority: int
    locations: List[LocationComments]
    score: float
    feedback: str
    position: Optional[Position] = None  # 問題のある箇所の位置情報
    details: Optional[List[Dict]] = None

    def to_dict(self) -> Dict:
        """
        評価結果を辞書形式に変換
        
        Returns:
            Dict: 評価結果の辞書表現
        """
        result = {
            "category_id": self.category_id,
            "category_name": self.category_name,
            "priority": self.priority,
            "score": self.score,
            "feedback": self.feedback,
            "locations": [loc.dict() for loc in self.locations]
        }
        if self.position:
            result["position"] = self.position.dict()
        if self.details:
            result["details"] = self.details
        return result

    class Config:
        """設定クラス"""
        json_schema_extra = {
            "example": {
                "category_id": "FULL_TEXT_RHETORIC",
                "category_name": "全文の修辞",
                "priority": 1,
                "score": 0.8,
                "feedback": "文章の明確さを改善できます",
                "locations": [
                    {
                        "location": "段落1",
                        "comments": [
                            {
                                "criteria_id": "CLARITY",
                                "content": "文章の明確さを改善できます",
                                "score": 0.8
                            },
                            {
                                "criteria_id": "CONCISENESS",
                                "content": "より簡潔な表現を検討してください",
                                "score": 0.7
                            }
                        ]
                    }
                ]
            }
        } 