"""
評価カテゴリの情報を定義するモデル
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class CriteriaInfo:
    """評価カテゴリの情報を保持するクラス"""
    id: str
    display_name: str
    priority: int
    criteria_ids: List[str]
    max_score: float  # 評価カテゴリの最大点数
    criteria_weights: Dict[str, float] = field(default_factory=dict)  # 評価基準ごとの重み付け

    def __post_init__(self):
        """
        インスタンス生成後の初期化処理
        criteria_weightsが空の場合は、均等な重み付けを設定
        """
        if not self.criteria_weights:
            # 各評価基準に均等な重みを設定
            weight = 1.0 / len(self.criteria_ids) if self.criteria_ids else 0.0
            self.criteria_weights = {criteria_id: weight for criteria_id in self.criteria_ids} 