"""
LLMモデル（OpenAI API）との通信を管理するモジュール
"""
from typing import Dict, Any, List
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json
from ..config import get_settings

settings = get_settings()

class LLMService:
    """LLMサービスクラス"""
    
    def __init__(self):
        """LLMサービスの初期化"""
        self.llm = ChatOpenAI(
            model_name=settings.openai_model,
            temperature=0,
            openai_api_key=settings.openai_api_key
        )
    
    async def evaluate_text(
        self,
        text: str,
        evaluation_criteria: str,
        system_prompt: str
    ) -> Dict[str, Any]:
        """
        テキストを評価する
        
        Args:
            text (str): 評価対象のテキスト
            evaluation_criteria (str): 評価基準
            system_prompt (str): システムプロンプト
            
        Returns:
            Dict[str, Any]: 評価結果（JSON形式）
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"評価基準:\n{evaluation_criteria}\n\n評価対象テキスト:\n{text}")
        ]
        
        response = await self.llm.agenerate([messages])
        
        # レスポンスをJSON形式に変換
        try:
            result = json.loads(response.generations[0][0].text)
            return result
        except json.JSONDecodeError:
            return {
                "error": "評価結果のJSON解析に失敗しました",
                "raw_response": response.generations[0][0].text
            } 