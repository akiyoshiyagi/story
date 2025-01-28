"""
環境設定を管理するモジュール
"""
from typing import Dict, Any
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """環境設定クラス"""
    # アプリケーション設定
    APP_NAME: str = "Story Checker API"
    DEBUG: bool = True
    USE_DUMMY_CONTENTS: bool = False
    
    # CORS設定
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://localhost:3000",
        "https://localhost:8080",
        "https://localhost:3001",  # Office Add-inのオリジン
        "http://127.0.0.1:8001",   # バックエンドAPI
        "http://127.0.0.1:3001",   # フロントエンド（IP指定）
        "null",                    # Office.jsからのリクエストに対応
    ]
    CORS_METHODS: list = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_HEADERS: list = [
        "Content-Type",
        "Accept",
        "Authorization",
        "X-Requested-With",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers",
    ]
    CORS_CREDENTIALS: bool = True
    
    # GPT4o-mini設定
    OPENAI_LITE_API_KEY: str
    OPENAI_LITE_API_TYPE: str
    OPENAI_LITE_API_VERSION: str
    OPENAI_LITE_API_BASE_URL: str
    OPENAI_LITE_API_LLM_MODEL_NAME: str
    
    # GPT4o sub設定
    OPENAI_API_KEY: str
    OPENAI_API_TYPE: str
    OPENAI_API_VERSION: str
    OPENAI_API_BASE_URL: str
    OPENAI_API_LLM_MODEL_NAME: str
    
    # 共通OpenAI設定
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_TIMEOUT: int = 30
    OPENAI_MAX_RETRIES: int = 3
    
    # Google Cloud設定
    GOOGLE_APPLICATION_CREDENTIALS: str
    
    class Config:
        env_file = ".env"
        
@lru_cache()
def get_settings() -> Settings:
    """
    環境設定のシングルトンインスタンスを取得
    
    Returns:
        Settings: 環境設定インスタンス
    """
    return Settings() 