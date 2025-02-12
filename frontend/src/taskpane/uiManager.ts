import { getDocumentStructure } from "./documentUtil";
import { reviewDocument, checkApiHealth } from "./api";
import type { ReviewResponse } from "./types";

interface DocumentBlock {
    level: number;
    text: string;
    range: Word.Range;
    children: DocumentBlock[];
    parent: DocumentBlock | null;
}

interface GroupedComment {
    range: Word.Range;
    comments: string[];
}

interface CommentData {
    content: string;
    paragraphIndex: number;
}

interface EvaluationComment {
    categoryId: string;
    criteriaId: string;
    name: string;
    feedback: string;
    location?: string;
}

// カテゴリIDとHTML要素のIDのマッピング
const CATEGORY_ID_MAPPING: Record<string, {
    buttonId: string;
    judgmentId: string;
}> = {
    'FULL_TEXT_RHETORIC': {
        buttonId: 'btn-full-text-rhetoric',
        judgmentId: 'judgment-full-text-rhetoric'
    },
    'SUMMARY_LOGIC_FLOW': {
        buttonId: 'btn-summary-logic-flow',
        judgmentId: 'judgment-summary-logic-flow'
    },
    'SUMMARY_INTERNAL_LOGIC': {
        buttonId: 'btn-summary-internal-logic',
        judgmentId: 'judgment-summary-internal-logic'
    },
    'SUMMARY_STORY_LOGIC': {
        buttonId: 'btn-summary-story-logic',
        judgmentId: 'judgment-summary-story-logic'
    },
    'STORY_INTERNAL_LOGIC': {
        buttonId: 'btn-story-internal-logic',
        judgmentId: 'judgment-story-internal-logic'
    },
    'DETAIL_RHETORIC': {
        buttonId: 'btn-detail-rhetoric',
        judgmentId: 'judgment-detail-rhetoric'
    }
};

// カテゴリ評価マッピングの型定義
type CategoryInfo = {
    targetSection: 'all' | 'summary' | 'story' | 'body' | 'summary_story';
    description: string;
};

type CategoryMapping = {
    [key in 'FULL_TEXT_RHETORIC' | 'SUMMARY_LOGIC_FLOW' | 'SUMMARY_INTERNAL_LOGIC' | 'SUMMARY_STORY_LOGIC' | 'STORY_INTERNAL_LOGIC' | 'DETAIL_RHETORIC']: CategoryInfo;
};

// カテゴリと評価範囲の対応を定義
const CATEGORY_EVALUATION_MAPPING: CategoryMapping = {
    'FULL_TEXT_RHETORIC': {
        targetSection: 'all',
        description: '文章全体の修辞評価'
    },
    'SUMMARY_LOGIC_FLOW': {
        targetSection: 'summary',
        description: 'サマリーの論理展開評価'
    },
    'SUMMARY_INTERNAL_LOGIC': {
        targetSection: 'summary',
        description: 'サマリーの内部論理評価'
    },
    'SUMMARY_STORY_LOGIC': {
        targetSection: 'summary_story',
        description: 'サマリーとストーリーの論理評価'
    },
    'STORY_INTERNAL_LOGIC': {
        targetSection: 'story',
        description: 'ストーリーの内部論理評価'
    },
    'DETAIL_RHETORIC': {
        targetSection: 'body',
        description: '詳細の修辞評価'
    }
};

export class UIManager {
    private checkButton: HTMLButtonElement;
    private loadingSpinner: HTMLElement;
    private statusElement: HTMLElement;
    private logger: Console = console;
    private documentStructure: {
        indentLevels: number[];
        paragraphTypes: Map<number, 'summary' | 'story' | 'body' | 'detail'>;
        indentDistribution: Map<number, number>;
    } = {
        indentLevels: [],
        paragraphTypes: new Map(),
        indentDistribution: new Map()
    };

    // コメントの一時保存用マップ
    private commentStore: { [key: string]: CommentData[] } = {};

    constructor() {
        this.checkButton = document.getElementById('check-button') as HTMLButtonElement;
        this.loadingSpinner = document.getElementById('loading-spinner') as HTMLElement;
        this.statusElement = document.getElementById('status') as HTMLElement;

        this.initializeEventListeners();
    }

    /**
     * イベントリスナーを初期化する
     */
    private initializeEventListeners(): void {
        // チェックボタンのクリックイベント
        this.checkButton.addEventListener('click', async () => {
            await this.handleCheckDocument();
        });

        // キーボードイベント
        document.addEventListener('keydown', (event: KeyboardEvent) => {
            if (event.key === 'Enter') {
                this.handleCheckDocument();
            }
        });

        // カテゴリボタンのイベントリスナーを初期化
        this.initializeCategoryButtons();
    }

    /**
     * ドキュメントのチェックを実行する
     */
    private async handleCheckDocument(): Promise<void> {
        try {
            this.setLoading(true);
            this.setStatus('文書を解析中...');

            // APIの健全性チェック
            const isHealthy = await checkApiHealth();
            if (!isHealthy) {
                throw new Error('APIサーバーに接続できません');
            }

            // ドキュメントの構造を解析
            const structure = await getDocumentStructure();
            if (!structure) {
                throw new Error('文書の構造を解析できません');
            }

            this.setStatus('評価中...');
            const response = await reviewDocument(structure);
            await this.handleReviewResponse(response);

            // 評価完了時のメッセージを設定
            this.setStatus('評価完了');

        } catch (error) {
            this.logger.error('Error during document check:', error);
            this.setStatus(`エラーが発生しました: ${error instanceof Error ? error.message : '不明なエラー'}`);
        } finally {
            this.setLoading(false);
        }
    }

    // カテゴリボタンの初期化
    private async initializeCategoryButtons(): Promise<void> {
        try {
            await Word.run(async (context) => {
                // 現在のドキュメントの全てのコメントを取得
                const body = context.document.body;
                const paragraphs = body.paragraphs;
                paragraphs.load("items");
                await context.sync();

                // 各段落のインデックスとコメントを取得
                for (let i = 0; i < paragraphs.items.length; i++) {
                    const paragraph = paragraphs.items[i];
                    const range = paragraph.getRange();
                    const comments = range.getComments();
                    comments.load("items");
                    await context.sync();

                    if (comments.items.length > 0) {
                        comments.items.forEach((comment: Word.Comment) => {
                            const categoryId = this.getCategoryFromComment(comment);
                            if (categoryId) {
                                if (!this.commentStore[categoryId]) {
                                    this.commentStore[categoryId] = [];
                                }
                                this.commentStore[categoryId].push({
                                    content: comment.content || "",
                                    paragraphIndex: i
                                });
                            }
                        });
                    }
                }

                // カテゴリボタンのイベントリスナーを設定
                Object.keys(CATEGORY_ID_MAPPING).forEach(categoryId => {
                    const button = document.getElementById(`btn-${categoryId}`);
                    if (button) {
                        button.addEventListener("click", () => this.toggleCategoryComments(categoryId));
                    }
                });
            });
        } catch (error) {
            console.error("Error initializing category buttons:", error);
        }
    }

    // コメントからカテゴリIDを取得
    private getCategoryFromComment(comment: Word.Comment): string | null {
        if (!comment || !comment.content) return null;
        const content = comment.content;
        // カテゴリIDをコメントの内容から抽出
        for (const categoryId of Object.keys(CATEGORY_ID_MAPPING)) {
            if (content.includes(categoryId)) {
                return categoryId;
            }
        }
        return null;
    }

    // カテゴリのコメント表示を切り替え
    private async toggleCategoryComments(selectedCategoryId: string): Promise<void> {
        try {
            await Word.run(async (context) => {
                // 全てのコメントを非表示
                const body = context.document.body;
                const paragraphs = body.paragraphs;
                paragraphs.load("items");
                await context.sync();

                // 既存のコメントを削除
                for (const paragraph of paragraphs.items) {
                    const range = paragraph.getRange();
                    const comments = range.getComments();
                    comments.load("items");
                    await context.sync();

                    comments.items.forEach((comment: Word.Comment) => comment.delete());
                }
                await context.sync();

                // 選択されたカテゴリのコメントのみを表示
                const selectedComments = this.commentStore[selectedCategoryId];
                if (selectedComments) {
                    selectedComments.forEach(({ content, paragraphIndex }) => {
                        if (content && paragraphIndex < paragraphs.items.length) {
                            const paragraph = paragraphs.items[paragraphIndex];
                            const range = paragraph.getRange();
                            range.insertComment(content);
                        }
                    });
                }
                await context.sync();
            });
        } catch (error) {
            console.error("Error toggling category comments:", error);
        }
    }

    /**
     * ローディング状態を設定する
     */
    private setLoading(isLoading: boolean): void {
        this.loadingSpinner.style.display = isLoading ? 'block' : 'none';
            this.checkButton.disabled = isLoading;
    }

    /**
     * ステータスメッセージを設定する
     */
    private setStatus(message: string): void {
        this.statusElement.textContent = message;
    }

    /**
     * レビュー結果を処理する
     */
    private async handleReviewResponse(response: ReviewResponse): Promise<void> {
        try {
            // 評価結果の表示を更新
            this.updateEvaluationDisplay(response);
            
            // カテゴリボタンの状態を更新
            await this.updateCategoryButtons(response);
            
        } catch (error) {
            console.error('Error handling review response:', error);
            throw error;
        }
    }

    /**
     * 評価結果の表示を更新する
     */
    private updateEvaluationDisplay(response: ReviewResponse): void {
        // 総合評価スコアの表示を更新
        const totalScoreElement = document.getElementById('total-score');
        if (totalScoreElement) {
            totalScoreElement.textContent = `${Math.round(response.totalScore * 100)}点`;
        }

        // 総合判定の表示を更新
        const totalJudgmentElement = document.getElementById('total-judgment');
        if (totalJudgmentElement) {
            totalJudgmentElement.textContent = response.totalJudgment || '判定なし';
        }
    }

    /**
     * カテゴリボタンの状態を更新する
     */
    private async updateCategoryButtons(response: ReviewResponse): Promise<void> {
        // カテゴリごとの評価結果を表示
        response.categoryScores?.forEach(score => {
            const judgmentElement = document.getElementById(CATEGORY_ID_MAPPING[score.categoryId]?.judgmentId);
            if (judgmentElement) {
                judgmentElement.textContent = `${Math.round(score.score * 100)}点`;
            }
        });
    }
} 