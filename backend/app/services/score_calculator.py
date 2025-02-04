"""
スコア計算を管理するサービス
"""
from typing import List, Dict, Any
from ..config.criteria_mapping import CRITERIA_MAPPING

class ScoreCalculator:
    def __init__(self):
        self.MAX_SCORE = 100
        self.MIN_SCORE = 0

    def normalize_score(self, score: float) -> int:
        """
        スコアを0-100の範囲に正規化し、四捨五入する
        """
        normalized = score * self.MAX_SCORE
        return round(normalized)

    def calculate_criteria_score(self, evaluation_results: List[Dict[str, Any]], criteria_ids: List[str]) -> int:
        """
        特定の評価基準グループのスコアを計算
        
        Args:
            evaluation_results: 評価結果のリスト
            criteria_ids: 評価基準IDのリスト
            
        Returns:
            正規化されたスコア（0-100）
        """
        if not criteria_ids:
            return self.MAX_SCORE

        # 指定された評価基準の結果のみを抽出
        relevant_results = [
            result for result in evaluation_results
            if result.get('criteria_id') in criteria_ids
        ]

        if not relevant_results:
            return self.MAX_SCORE

        # すべての評価が「問題なし」の場合は100点
        if all(not result.get('has_issues', False) for result in relevant_results):
            return self.MAX_SCORE

        # 個別スコアの平均を計算
        scores = [result.get('score', 1.0) for result in relevant_results]
        avg_score = sum(scores) / len(scores)
        
        return self.normalize_score(avg_score)

    def calculate_display_category_scores(
        self,
        evaluation_results: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        表示カテゴリごとのスコアを計算
        
        Args:
            evaluation_results: 評価結果のリスト
            
        Returns:
            カテゴリごとのスコア情報（優先度順）
        """
        category_scores = {}
        
        # 優先度でソートされたカテゴリを取得
        sorted_categories = sorted(
            CRITERIA_MAPPING.items(),
            key=lambda x: x[1]['priority']
        )
        
        for category_id, mapping in sorted_categories:
            criteria_ids = mapping['evaluation_criteria']
            score = self.calculate_criteria_score(evaluation_results, criteria_ids)
            
            # カテゴリごとの評価結果を格納
            category_scores[category_id] = {
                'display_name': mapping['display_name'],
                'priority': mapping['priority'],
                'score': score,
                'evaluation_results': [
                    result for result in evaluation_results
                    if result.get('criteria_id') in criteria_ids
                ]
            }
        
        return category_scores

    def calculate_total_score(self, category_scores: Dict[str, Dict[str, Any]]) -> int:
        """
        総合スコアを計算
        
        Args:
            category_scores: カテゴリごとのスコア情報
            
        Returns:
            総合スコア（0-100）
        """
        if not category_scores:
            return self.MAX_SCORE

        # 各カテゴリのスコアの平均を計算
        scores = [info['score'] for info in category_scores.values()]
        avg_score = sum(scores) / len(scores)
        
        return round(avg_score) 