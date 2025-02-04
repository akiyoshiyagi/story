"""
評価カテゴリの情報を定義するモデル
"""
from dataclasses import dataclass
from typing import List

@dataclass
class CriteriaInfo:
    """評価カテゴリの情報を保持するクラス"""
    display_name: str
    priority: int
    criteria_ids: List[str]
    applicable_to: List[str] 