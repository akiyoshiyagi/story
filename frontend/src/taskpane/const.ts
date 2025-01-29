/**
 * フロントエンドで使用する定数を定義
 */

// APIエンドポイント
export const API_BASE_URL = "http://127.0.0.1:8001";
export const API_ENDPOINTS = {
    REVIEW: `${API_BASE_URL}/api/review`,
    HEALTH: `${API_BASE_URL}/api/health`,
    EVALUATE: `${API_BASE_URL}/api/evaluate`,
    CHECK_STATUS: `${API_BASE_URL}/api/status`,
    OPENAI: `${API_BASE_URL}/api/openai/evaluate`
};

// OpenAI API設定
export const OPENAI_CONFIG = {
    MODEL: "gpt-4o",
    MAX_TOKENS: 2000,
    TEMPERATURE: 0.7,
    SYSTEM_PROMPT: `あなたはビジネス文書の評価と改善提案を行う専門家です。
以下の観点で文書を評価し、具体的なフィードバックと改善提案を提供してください：

1. 論理構造の評価
2. 文章の明確さと簡潔さ
3. ビジネス文書としての適切性
4. 用語の一貫性
5. 文の接続と流れ

各評価は以下の形式で提供してください：
- スコア（0-1の数値）
- 優先度（1-3の整数、1が最も高い）
- フィードバック（具体的な問題点）
- 改善提案（具体的な修正案）`
};

// 評価カテゴリ
export const EVALUATION_CATEGORIES = {
    FULL_TEXT_RHETORIC: "全文修辞表現",
    SUMMARY_LOGIC_FLOW: "サマリーの論理展開",
    SUMMARY_INTERNAL_LOGIC: "サマリー単体の論理",
    SUMMARY_STORY_LOGIC: "サマリーとストーリー間の論理",
    STORY_INTERNAL_LOGIC: "ストーリー単体の論理",
    DETAIL_RHETORIC: "細部の修辞表現"
};

// UI表示用の定数
export const UI_CONSTANTS = {
    MIN_SCORE: 0,
    MAX_SCORE: 100,
    LOADING_MESSAGE: "評価中...",
    ERROR_MESSAGE: "エラーが発生しました",
    SUCCESS_MESSAGE: "評価が完了しました",
    INITIAL_MESSAGE: "「実行」ボタンをクリックして文書を評価します"
};

// スコアの閾値
export const SCORE_THRESHOLDS = {
    EXCELLENT: 90,
    GOOD: 70,
    FAIR: 50
};

// 評価カテゴリのマッピング
export const CATEGORY_ID_MAP: { [key: string]: string } = {
    "全文修辞表現": "full-text-rhetoric",
    "サマリーの論理展開": "summary-logic-flow",
    "サマリー単体の論理": "summary-internal-logic",
    "サマリーとストーリー間の論理": "summary-story-logic",
    "ストーリー単体の論理": "story-internal-logic",
    "細部の修辞表現": "detail-rhetoric"
}; 