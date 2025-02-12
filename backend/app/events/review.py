"""
文章レビュー処理を管理するモジュール
"""
import logging
from typing import Dict, Any, List
from ..services.llm_model import LLMService
from ..prompt_template.prompt import (
    SYSTEM_PROMPT,
    EVALUATION_CRITERIA,
    identify_target_type,
    get_evaluation_text
)

# ロガーの設定
logger = logging.getLogger(__name__)

class ReviewManager:
    """レビュー管理クラス"""
    
    def __init__(self):
        """レビューマネージャーの初期化"""
        self.llm_service = LLMService()
        self.logger = logging.getLogger(__name__)
        
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
        try:
            self.logger.info("文書評価プロセスを開始")
            self.logger.debug(f"入力文書: サマリー長={len(content.get('summary', ''))}, "
                          f"段落数={len(content.get('paragraphs', []))}, "
                          f"全文長={len(content.get('full_text', ''))}")

            # 入力値の検証
            if not content.get('full_text'):
                raise ValueError("文書本文が空です")
            
            results = []
            
            # 各評価基準に対して評価を実行
            for criteria in EVALUATION_CRITERIA:
                try:
                    self.logger.debug(f"評価基準 '{criteria['name']}' の評価を開始")
                    
                    # 評価対象テキストを取得
                    target_text = self._get_target_text(content, criteria["name"])
                    if not target_text:
                        self.logger.warning(f"評価基準 '{criteria['name']}' の評価対象テキストが空です")
                        continue

                    # 評価を実行
                    result = await self.llm_service.evaluate_text(
                        text=target_text,
                        evaluation_criteria=criteria["description"],
                        system_prompt=SYSTEM_PROMPT
                    )
                    
                    results.append({
                        "priority": criteria["priority"],
                        **result
                    })
                    
                    self.logger.debug(f"評価基準 '{criteria['name']}' の評価が完了")
                    
                except Exception as e:
                    self.logger.error(f"評価基準 '{criteria['name']}' の評価中にエラー: {str(e)}")
                    results.append({
                        "priority": criteria["priority"],
                        "name": criteria["name"],
                        "score": 0.0,
                        "error": str(e)
                    })
            
            # 優先度順にソート
            results.sort(key=lambda x: x["priority"])
            
            # 総合スコアを計算
            total_score = self._calculate_total_score(results)
            
            self.logger.info(f"文書評価完了: 総合スコア={total_score}, 評価数={len(results)}")
            
            return {
                "total_score": total_score,
                "evaluations": results
            }
            
        except Exception as e:
            self.logger.error(f"文書評価プロセス中に致命的なエラー: {str(e)}")
            return {
                "total_score": 0,
                "evaluations": [],
                "error": str(e)
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
        try:
            document_structure = {
                "structure": {
                    "summary": [content.get("summary", "")],
                    "story": content.get("paragraphs", []),
                    "body": content.get("full_text", "")
                }
            }
            
            # 評価対象タイプを特定
            target_type = identify_target_type(document_structure)
            self.logger.debug(f"評価基準 '{criteria_name}' の評価対象タイプ: {target_type}")
            
            # 評価対象テキストを取得
            target_text = get_evaluation_text(document_structure, target_type) or ""
            
            if not target_text:
                self.logger.warning(f"評価基準 '{criteria_name}' の評価対象テキストが空です")
            else:
                self.logger.debug(f"評価基準 '{criteria_name}' の評価対象テキスト長: {len(target_text)}")
                
            return target_text
            
        except Exception as e:
            self.logger.error(f"評価対象テキストの取得中にエラー: {str(e)}")
            raise
    
    def _calculate_total_score(self, results: List[Dict[str, Any]]) -> int:
        """
        総合スコアを計算
        
        Args:
            results (List[Dict[str, Any]]): 評価結果リスト
            
        Returns:
            int: 総合スコア（0-100）
        """
        try:
            if not results:
                self.logger.warning("評価結果が空のため、スコアは0とします")
                return 0
            
            # エラーのある結果を除外
            valid_results = [r for r in results if "error" not in r]
            
            if not valid_results:
                self.logger.warning("有効な評価結果が無いため、スコアは0とします")
                return 0
            
            # 単純な平均値を計算
            total_score = sum(r["score"] for r in valid_results)
            score = round((total_score / len(valid_results)) * 100)
            
            self.logger.debug(f"総合スコア計算: 有効な評価数={len(valid_results)}, スコア={score}")
            
            return score
            
        except Exception as e:
            self.logger.error(f"総合スコアの計算中にエラー: {str(e)}")
            return 0 