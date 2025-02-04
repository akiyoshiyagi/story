import { getDocumentStructure } from "./documentUtil";
import { reviewDocument, checkApiHealth } from "./api";
import type { ReviewResponse } from "./types";

// カテゴリIDとHTML要素のIDのマッピング
const CATEGORY_ID_MAPPING: Record<string, {
    scoreId: string;
    judgmentId: string;
    contentId: string;
}> = {
    'FULL_TEXT_RHETORIC': {
        scoreId: 'score-full-text-rhetoric',
        judgmentId: 'judgment-full-text-rhetoric',
        contentId: 'content-full-text-rhetoric'
    },
    'SUMMARY_LOGIC_FLOW': {
        scoreId: 'score-summary-logic-flow',
        judgmentId: 'judgment-summary-logic-flow',
        contentId: 'content-summary-logic-flow'
    },
    'SUMMARY_INTERNAL_LOGIC': {
        scoreId: 'score-summary-internal-logic',
        judgmentId: 'judgment-summary-internal-logic',
        contentId: 'content-summary-internal-logic'
    },
    'SUMMARY_STORY_LOGIC': {
        scoreId: 'score-summary-story-logic',
        judgmentId: 'judgment-summary-story-logic',
        contentId: 'content-summary-story-logic'
    },
    'STORY_INTERNAL_LOGIC': {
        scoreId: 'score-story-internal-logic',
        judgmentId: 'judgment-story-internal-logic',
        contentId: 'content-story-internal-logic'
    },
    'DETAIL_RHETORIC': {
        scoreId: 'score-detail-rhetoric',
        judgmentId: 'judgment-detail-rhetoric',
        contentId: 'content-detail-rhetoric'
    }
};

export class UIManager {
    private checkButton: HTMLButtonElement;
    private loadingSpinner: HTMLElement;
    private statusElement: HTMLElement;

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
    }

    /**
     * 評価結果を表示する
     */
    private displayEvaluationResults(response: ReviewResponse): void {
        try {
            // エラーチェック
            if (response.error) {
                this.showError(`評価中にエラーが発生しました: ${response.error}`);
                return;
            }

            // 総合評価の表示
            const totalScoreElement = document.getElementById('total-score');
            const totalJudgmentElement = document.getElementById('total-judgment');
            
            if (totalScoreElement && totalJudgmentElement) {
                totalScoreElement.textContent = `${response.totalScore}点`;
                totalJudgmentElement.textContent = response.totalJudgment;
                totalJudgmentElement.setAttribute('data-status', response.totalJudgment);
            }

            // カテゴリごとの評価結果を表示
            response.categoryScores.forEach(categoryScore => {
                const elementIds = CATEGORY_ID_MAPPING[categoryScore.categoryId];
                if (!elementIds) {
                    console.warn(`Unknown category ID: ${categoryScore.categoryId}`);
                    return;
                }

                // 判定（OK/NG）の表示
                const judgmentElement = document.getElementById(elementIds.judgmentId);
                if (judgmentElement) {
                    judgmentElement.textContent = categoryScore.judgment;
                    judgmentElement.setAttribute('data-status', categoryScore.judgment);
                }
            });

            // Word文書にコメントを追加
            this.addCommentsToDocument(response.evaluations);

            // 評価完了のステータス表示
            this.showStatus('評価が完了しました');

        } catch (error) {
            console.error('Error displaying evaluation results:', error);
            this.showError('評価結果の表示中にエラーが発生しました');
        }
    }

    /**
     * Word文書にコメントを追加
     */
    private async addCommentsToDocument(evaluations: Array<{ categoryId: string; location: string; feedback: string }>): Promise<void> {
        try {
            await Word.run(async context => {
                // 文書内の全段落を取得
                const paragraphs = context.document.body.paragraphs;
                paragraphs.load('text');
                await context.sync();

                // 各評価結果に対してコメントを追加
                for (const evaluation of evaluations) {
                    const targetLocation = evaluation.location;
                    
                    // 対象の段落を探す
                    for (const paragraph of paragraphs.items) {
                        if (paragraph.text.includes(targetLocation)) {
                            // コメントを追加
                            const comment = `${evaluation.feedback}`;
                            paragraph.insertComment(comment);
                            break;
                        }
                    }
                }

                await context.sync();
            });
        } catch (error) {
            console.error('Error adding comments:', error);
            throw error;
        }
    }

    /**
     * エラーメッセージを表示
     */
    public showError(message: string): void {
        if (this.statusElement) {
            this.statusElement.textContent = message;
            this.statusElement.className = "status error";
        }
    }

    /**
     * ステータスメッセージを表示
     */
    public showStatus(message: string): void {
        if (this.statusElement) {
            this.statusElement.textContent = message;
            this.statusElement.className = "status";
        }
    }

    /**
     * ドキュメントのチェック処理を実行
     */
    public async handleCheckDocument(): Promise<void> {
        try {
            this.setLoading(true);

            // APIの健全性をチェック
            const isHealthy = await checkApiHealth();
            if (!isHealthy) {
                throw new Error("APIサーバーに接続できません");
            }

            // 文書構造を取得
            const structure = await getDocumentStructure();

            // 文書評価を実行
            const result = await reviewDocument(structure);
            if (!result) {
                throw new Error("評価結果が不正です");
            }

            // 評価結果を表示
            this.displayEvaluationResults(result);

        } catch (error) {
            console.error("Error in handleCheckDocument:", error);
            this.showError(error instanceof Error ? error.message : "予期せぬエラーが発生しました");
        } finally {
            this.setLoading(false);
        }
    }

    /**
     * ローディング状態を設定
     */
    private setLoading(isLoading: boolean): void {
        if (this.checkButton) {
            this.checkButton.disabled = isLoading;
        }
        if (this.loadingSpinner) {
            this.loadingSpinner.style.display = isLoading ? "block" : "none";
        }
    }
} 