/**
 * 共通の型定義
 */

declare namespace Word {
    interface Document {
        comments: CommentCollection;
        contentControls: ContentControlCollection;
    }

    interface CommentCollection {
        items: Comment[];
        load(properties: string): void;
    }

    interface Comment {
        delete(): void;
        text: string;
    }

    interface Range {
        getUniqueId(): string;
        insertComment(text: string): Comment;
        text: string;
        insertContentControl(): ContentControl;
    }

    interface Paragraph {
        getRange(): Range;
        firstLineIndent: number;
        leftIndent: number;
        text: string;
    }

    interface ContentControlCollection {
        items: ContentControl[];
        load(propertyNames?: string): void;
    }

    interface ContentControl {
        title: string;
        delete(): void;
        insertText(text: string, location: InsertLocation): void;
    }

    enum InsertLocation {
        before = "Before",
        after = "After",
        start = "Start",
        end = "End",
        replace = "Replace"
    }
}

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