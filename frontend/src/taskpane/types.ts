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
    category: string;
    score: number;
    priority: number;  // 評価の優先度（1が最も高い）
    target_sentence: string;
    feedback: string[];
    improvement_suggestions: string[];
}

// APIレスポンスの型定義
export interface ReviewResponse {
    total_score: number;
    evaluations: EvaluationResult[];
} 