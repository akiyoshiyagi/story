from dataclasses import dataclass
from typing import List

@dataclass
class EvaluationResult:
    """文書評価の結果を表すデータクラス"""
    category: str
    score: float
    priority: int
    target_sentence: str
    feedback: List[str]
    improvement_suggestions: List[str]

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            'category': self.category,
            'score': self.score,
            'priority': self.priority,
            'target_sentence': self.target_sentence,
            'feedback': self.feedback,
            'improvement_suggestions': self.improvement_suggestions
        } 