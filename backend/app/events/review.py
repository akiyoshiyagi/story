"""
文章レビュー処理を管理するモジュール
"""
from typing import Dict, Any, List
from ..services.llm_model import LLMService
from ..prompt_template.prompt import SYSTEM_PROMPT, EVALUATION_CRITERIA


class ReviewManager:
    """レビュー管理クラス"""
    
    def __init__(self):
        """レビューマネージャーの初期化"""
        self.llm_service = LLMService()
        
    async def process_document(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        文書を処理し評価を実行
        
        Args:
            content (Dict[str, Any]): 
                {
                    "full_text": str,  # 文書全体
                    "summary": str,    # サマリー部分
                    "paragraphs": List[str]  # 段落ごとのリスト
                }
                
        Returns:
            Dict[str, Any]: 評価結果
        """
        results = []
        
        # 各評価基準に対して評価を実行
        for criteria in EVALUATION_CRITERIA:
            result = await self.llm_service.evaluate_text(
                text=self._get_target_text(content, criteria["name"]),
                evaluation_criteria=criteria["description"],
                system_prompt=SYSTEM_PROMPT
            )
            results.append({
                "priority": criteria["priority"],
                **result
            })
        
        # 優先度順にソート
        results.sort(key=lambda x: x["priority"])
        
        # 総合スコアを計算
        total_score = self._calculate_total_score(results)
        
        return {
            "total_score": total_score,
            "evaluations": results
        }
    
    def _get_target_text(self, content: Dict[str, Any], criteria_name: str) -> str:
        """
        評価基準に応じた評価対象テキストを取得
        
        Args:
            content (Dict[str, Any]): 文書コンテンツ
            criteria_name (str): 評価基準名
            
        Returns:
            str: 評価対象テキスト
        """
        if criteria_name == "全文修辞表現":
            return content["full_text"]
        elif criteria_name in ["サマリーの論理展開", "サマリー単体の論理"]:
            return content["summary"]
        elif criteria_name == "サマリーとストーリー間の論理":
            return f"サマリー:\n{content['summary']}\n\n本文:\n{content['full_text']}"
        elif criteria_name == "ストーリー単体の論理":
            return "\n\n".join(content["paragraphs"])
        else:  # 細部の修辞表現
            return content["full_text"]
    
    def _calculate_total_score(self, results: List[Dict[str, Any]]) -> int:
        """
        総合スコアを計算
        
        Args:
            results (List[Dict[str, Any]]): 評価結果リスト
            
        Returns:
            int: 総合スコア（0-100）
        """
        if not results:
            return 0
            
        # 優先度の重みを考慮してスコアを計算
        total_weight = sum(len(results) - r["priority"] + 1 for r in results)
        weighted_score = sum(
            (len(results) - r["priority"] + 1) * r["score"]
            for r in results
        )
        
        return round(weighted_score / total_weight) 