from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from .services.openai_service import evaluate_document
from .services.health_service import check_health

router = APIRouter()

class OpenAIRequest(BaseModel):
    model: str
    messages: List[Dict]
    max_tokens: int
    temperature: float
    use_lite: Optional[bool] = False

@router.get('/health')
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {'status': 'healthy'}

@router.post('/openai/evaluate')
async def evaluate(request: OpenAIRequest):
    """OpenAI APIを使用して文書を評価する"""
    try:
        result = await evaluate_document(request.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 