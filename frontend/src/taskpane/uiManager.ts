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
}> = {
    'FULL_TEXT_RHETORIC': {
        buttonId: 'btn-full-text-rhetoric'
    },
    'SUMMARY_LOGIC_FLOW': {
        buttonId: 'btn-summary-logic-flow'
    },
    'SUMMARY_INTERNAL_LOGIC': {
        buttonId: 'btn-summary-internal-logic'
    },
    'SUMMARY_STORY_LOGIC': {
        buttonId: 'btn-summary-story-logic'
    },
    'STORY_INTERNAL_LOGIC': {
        buttonId: 'btn-story-internal-logic'
    },
    'DETAIL_RHETORIC': {
        buttonId: 'btn-detail-rhetoric'
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
    // 評価基準情報を保持
    private evaluationCriteria: Map<string, string[]> = new Map();
    // コメントの一時保存用マップ
    private commentStore: { [key: string]: CommentData[] } = {};
    // 現在選択されているカテゴリ
    private selectedCategory: string | null = null;

    constructor() {
        this.checkButton = document.getElementById('check-button') as HTMLButtonElement;
        this.loadingSpinner = document.getElementById('loading-spinner') as HTMLElement;
        this.statusElement = document.getElementById('status') as HTMLElement;

        // カテゴリボタンのイベントリスナーを初期化
        this.initializeCategoryButtons();
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
    private initializeCategoryButtons(): void {
        // カテゴリボタンのイベントリスナーを設定
        Object.entries(CATEGORY_ID_MAPPING).forEach(([categoryId, mapping]) => {
            const button = document.getElementById(mapping.buttonId);
            if (button) {
                button.addEventListener("click", () => {
                    this.toggleCategoryComments(categoryId);
                });
            }
        });
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

    // コメントからEVALUATION_CRITERIAを取得
    private getEvaluationCriteriaFromComment(comment: Word.Comment): string | null {
        if (!comment || !comment.content) return null;
        const content = comment.content;
        
        // コメントから評価観点を抽出
        const match = content.match(/【評価観点】(.*?)(\n|$)/);
        if (match && match[1]) {
            return match[1].trim();
        }
        return null;
    }

    /**
     * 位置情報からパラグラフインデックスを取得
     */
    private async getParagraphIndices(targetText: string | undefined): Promise<number[]> {
        if (!targetText) return [0];

        try {
            const result = await Word.run(async (context) => {
                const body = context.document.body;
                const paragraphs = body.paragraphs;
                paragraphs.load("text");
                await context.sync();

                const indices: number[] = [];
                // 対象のテキストを含むすべてのパラグラフを検索
                for (let i = 0; i < paragraphs.items.length; i++) {
                    const paragraphText = paragraphs.items[i].text.trim();
                    if (paragraphText.includes(targetText.trim())) {
                        indices.push(i);
                    }
                }
                return indices.length > 0 ? indices : [0]; // 見つからない場合は先頭のパラグラフを使用
            });
            return result;
        } catch (error) {
            console.error("Error finding paragraph indices:", error);
            return [0];
        }
    }

    /**
     * レビュー結果を処理する
     */
    private async handleReviewResponse(response: ReviewResponse): Promise<void> {
        try {
            // コメントストアをクリア
            this.commentStore = {};
            this.selectedCategory = null;
            
            // 評価結果からコメントを保存
            if (response.evaluations) {
                for (const evaluation of response.evaluations) {
                    if (!evaluation.feedback.includes('問題なし')) {
                        const categoryId = evaluation.categoryId;
                        if (!this.commentStore[categoryId]) {
                            this.commentStore[categoryId] = [];
                        }
                        
                        // 同じ位置に複数のコメントが存在する可能性を考慮
                        const paragraphIndices = await this.getParagraphIndices(evaluation.location);
                        for (const paragraphIndex of paragraphIndices) {
                            this.commentStore[categoryId].push({
                                content: this.formatComment(evaluation),
                                paragraphIndex: paragraphIndex
                            });
                        }
                    }
                }
            }

            // 評価結果の表示を更新
            this.updateEvaluationDisplay(response);

            // すべてのコメントを一旦削除
            await this.clearAllComments();
            
            // ボタンの状態を更新
            this.updateCategoryButtonStates();
            
        } catch (error) {
            console.error('Error handling review response:', error);
            throw error;
        }
    }

    /**
     * すべてのコメントを削除
     */
    private async clearAllComments(): Promise<void> {
        try {
            await Word.run(async (context) => {
                const body = context.document.body;
                const paragraphs = body.paragraphs;
                paragraphs.load("items");
                await context.sync();

                for (const paragraph of paragraphs.items) {
                    const range = paragraph.getRange();
                    const comments = range.getComments();
                    comments.load("items");
                    await context.sync();

                    comments.items.forEach((comment: Word.Comment) => comment.delete());
                }
                await context.sync();
            });
        } catch (error) {
            console.error("Error clearing comments:", error);
        }
    }

    /**
     * コメントをフォーマットする
     */
    private formatComment(evaluation: any): string {
        const parts = [
            `【評価観点】${evaluation.criteriaId}`
        ];

        if (evaluation.feedback) {
            parts.push(evaluation.feedback);
        }

        return parts.join('\n');
    }

    /**
     * 評価結果の表示を更新する
     */
    private updateEvaluationDisplay(response: ReviewResponse): void {
        // 総合評価スコアの表示を更新（計算された合計スコアをそのまま表示）
        const totalScoreElement = document.getElementById('total-score');
        if (totalScoreElement) {
            totalScoreElement.textContent = `${response.totalScore}点`;
        }

        // 総合判定の表示を更新（80点以上でOK、未満でNG）
        const totalJudgmentElement = document.getElementById('total-judgment');
        if (totalJudgmentElement) {
            const judgment = response.totalScore >= 80 ? 'OK' : 'NG';
            totalJudgmentElement.textContent = judgment;
        }

        // デバッグ情報の出力
        console.log('\n=== スコア計算結果 ===');
        console.log(`総合スコア: ${response.totalScore}点`);
        console.log(`総合判定: ${response.totalScore >= 80 ? 'OK' : 'NG'}`);
        if (response.evaluations) {
            console.log('各評価基準のスコア:');
            const processedCriteria = new Set();
            response.evaluations.forEach(evaluation => {
                // 重複評価を防ぐ
                if (!processedCriteria.has(evaluation.criteriaId)) {
                    processedCriteria.add(evaluation.criteriaId);
                    // フィードバックに基づいてスコアを表示（「問題なし」の場合はmax_score、それ以外は0点）
                    const score = evaluation.feedback.includes('問題なし') ? 'max_score' : '0';
                    console.log(`- ${evaluation.criteriaId}: ${score}点`);
                }
            });
        }
    }

    // カテゴリのコメント表示を切り替え
    private async toggleCategoryComments(selectedCategoryId: string): Promise<void> {
        try {
            // 既存のコメントを削除
            await this.clearAllComments();

            // 同じカテゴリが選択された場合は選択解除して終了
            if (this.selectedCategory === selectedCategoryId) {
                this.selectedCategory = null;
                this.updateCategoryButtonStates();
                return;
            }

            // 新しいカテゴリを選択
            this.selectedCategory = selectedCategoryId;

            // 選択されたカテゴリのコメントを表示
            await Word.run(async (context) => {
                const body = context.document.body;
                const paragraphs = body.paragraphs;
                paragraphs.load("items");
                await context.sync();

                const selectedComments = this.commentStore[selectedCategoryId];
                if (selectedComments) {
                    // 同じパラグラフに対する複数のコメントをグループ化
                    const groupedComments = selectedComments.reduce((acc, comment) => {
                        if (!acc[comment.paragraphIndex]) {
                            acc[comment.paragraphIndex] = [];
                        }
                        acc[comment.paragraphIndex].push(comment.content);
                        return acc;
                    }, {} as { [key: number]: string[] });

                    // グループ化されたコメントを追加
                    for (const [index, contents] of Object.entries(groupedComments)) {
                        const paragraphIndex = parseInt(index);
                        if (paragraphIndex < paragraphs.items.length) {
                            const paragraph = paragraphs.items[paragraphIndex];
                            const range = paragraph.getRange();
                            // 複数のコメントを結合して追加
                            range.insertComment(contents.join('\n\n'));
                        }
                    }
                }
                await context.sync();
            });

            // ボタンの表示状態を更新
            this.updateCategoryButtonStates();
            
        } catch (error) {
            console.error("Error toggling category comments:", error);
        }
    }

    /**
     * カテゴリボタンの表示状態を更新
     */
    private updateCategoryButtonStates(): void {
        Object.entries(CATEGORY_ID_MAPPING).forEach(([categoryId, mapping]) => {
            const button = document.getElementById(mapping.buttonId);
            if (button) {
                if (categoryId === this.selectedCategory) {
                    button.classList.add('selected');
                } else {
                    button.classList.remove('selected');
                }
            }
        });
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
} 