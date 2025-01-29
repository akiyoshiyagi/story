"""
評価プロンプトの型定義モジュール
"""
from typing import List
from pydantic import BaseModel
from ..models.evaluation import EvaluationResult


class EvaluationCriteria(BaseModel):
    """評価基準モデル"""
    name: str
    description: str
    priority: int


class EvaluationResult(BaseModel):
    """評価結果モデル"""
    category: str
    score: float
    priority: int
    target_sentence: str
    feedback: List[str]
    improvement_suggestions: List[str] 