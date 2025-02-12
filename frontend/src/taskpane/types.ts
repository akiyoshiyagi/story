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
        load(properties?: string): void;
    }

    interface Comment {
        content: string;
        delete(): void;
    }

    interface Range {
        getUniqueId(): string;
        insertComment(text: string): Comment;
        text: string;
        insertContentControl(): ContentControl;
        comments: CommentCollection;
        getComments(): CommentCollection;
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
    feedback: string;
    score: number;
    location?: string;
}

export interface Category {
    id: string;
    name: string;
    priority: number;
}

export interface CategoryScore {
    categoryId: string;
    score: number;
}

// APIレスポンスの型定義
export interface ReviewResponse {
    error?: string;
    totalScore: number;
    totalJudgment: string;
    categoryScores: CategoryScore[];
    evaluations: Evaluation[];
} 