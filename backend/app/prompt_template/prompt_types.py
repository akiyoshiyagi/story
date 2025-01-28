"""
評価プロンプトの型定義モジュール
"""
from typing import List
from pydantic import BaseModel


class EvaluationCriteria(BaseModel):
    """評価基準モデル"""
    name: str
    description: str
    priority: int


class EvaluationResult(BaseModel):
    """評価結果モデル"""
    category: str
    score: int
    feedback: List[str]
    improvement_suggestions: List[str] 