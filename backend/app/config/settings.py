"""
アプリケーション設定を管理するモジュール
"""
from functools import lru_cache
from pydantic_settings import BaseSettings

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
    
    # OpenAI API設定（標準）
    OPENAI_API_KEY: str | None = None
    OPENAI_API_TYPE: str | None = None
    OPENAI_API_VERSION: str | None = None
    OPENAI_API_BASE_URL: str | None = None
    OPENAI_API_LLM_MODEL_NAME: str | None = None
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_TIMEOUT: int = 60
    OPENAI_MAX_RETRIES: int = 3

    # OpenAI API設定（Lite）
    OPENAI_LITE_API_KEY: str | None = None
    OPENAI_LITE_API_TYPE: str | None = None
    OPENAI_LITE_API_VERSION: str | None = None
    OPENAI_LITE_API_BASE_URL: str | None = None
    OPENAI_LITE_API_LLM_MODEL_NAME: str | None = None

    # Google Cloud設定
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None

    class Config:
        """設定クラスの設定"""
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 未定義の環境変数を無視する

@lru_cache()
def get_settings() -> Settings:
    """
    設定インスタンスを取得（キャッシュ付き）
    
    Returns:
        Settings: 設定インスタンス
    """
    return Settings() 