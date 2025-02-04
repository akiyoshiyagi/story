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
export interface Evaluation {
    categoryId: string;
    criteriaId: string;
    score: number;
    feedback: string;
    location: string;
}

export interface Category {
    id: string;
    name: string;
    priority: number;
}

export interface CategoryScore {
    categoryId: string;
    categoryName: string;
    score: number;
    judgment: "OK" | "NG";
}

// APIレスポンスの型定義
export interface ReviewResponse {
    evaluations: Evaluation[];
    categories: Category[];
    categoryScores: CategoryScore[];
    totalScore: number;
    totalJudgment: "OK" | "NG";
    error?: string;
} 