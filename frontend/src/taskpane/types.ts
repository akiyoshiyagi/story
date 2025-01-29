/**
 * 共通の型定義
 */

// 文書構造の型定義
export interface DocumentStructure {
    title: string;  // ドキュメント全体のタイトル
    contents: StoryStructure[];  // 文書の内容
}

export interface StoryStructure {
    summary: string;
    stories: Array<{
        story: string;
        bodies: string[];
    }>;
}

// 評価結果の型定義
export interface EvaluationResult {
    target_sentence: string;  // 評価対象の文章
    feedback: string[];      // 課題点
    improvement_suggestions: string[];  // 改善提案
    score: number;          // スコア（0-1の範囲）
}

// APIレスポンスの型定義
export interface ReviewResponse {
    total_score: number;
    evaluations: EvaluationResult[];
} 