"""
FastAPIメインアプリケーション
"""
import logging
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .services.evaluation_service import EvaluationService
from .services.openai_service import evaluate_document as openai_evaluate
from .config import get_settings
from . import routes

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# ルートロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# 既存のハンドラをクリア
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# 新しいハンドラを追加
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

app = FastAPI()
settings = get_settings()

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://localhost:3001",  # Office Add-inのオリジン
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(routes.router, prefix="/api")

class DocumentRequest(BaseModel):
    title: str
    full_text: str
    summary: str
    paragraphs: list[str]

class OpenAIRequest(BaseModel):
    model: str
    messages: list[dict]
    max_tokens: int
    temperature: float
    use_lite: bool = False  # デフォルトはGPT4o sub

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    グローバル例外ハンドラー
    """
    logger.error(f"Global error handler caught: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__}
    )

@app.get("/api/health")
async def health_check():
    """
    ヘルスチェックエンドポイント
    """
    return {"status": "healthy"}

@app.post("/api/review")
async def review_document(request: DocumentRequest):
    """
    文書を評価するエンドポイント
    """
    try:
        logger.debug(f"Received review request for document: {request.title}")
        
        # 評価サービスのインスタンスを作成
        evaluation_service = EvaluationService()
        
        # 評価を実行
        evaluation_result = await evaluation_service.evaluate_document(
            full_text=request.full_text,
            summary=request.summary,
            paragraphs=request.paragraphs,
            title=request.title
        )
        
        logger.debug(f"Evaluation completed successfully for document: {request.title}")
        return evaluation_result
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}", exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in review_document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/openai/evaluate")
async def evaluate_with_openai(request: OpenAIRequest):
    """
    OpenAI APIを使用して文書を評価するエンドポイント
    """
    try:
        logger.debug(f"Received OpenAI evaluation request: {request}")
        result = await openai_evaluate(request.dict())
        logger.debug(f"OpenAI API response: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in OpenAI evaluation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 