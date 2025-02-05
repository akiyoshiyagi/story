import { getDocumentStructure } from "./documentUtil";
import { reviewDocument, checkApiHealth } from "./api";
import type { ReviewResponse } from "./types";

interface DocumentBlock {
    level: number;
    text: string;
    range: Word.Range;
    children: DocumentBlock[];
    parent?: DocumentBlock;
}

interface GroupedComment {
    range: Word.Range;
    comments: string[];
}

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

            // 総合評価の表示（小数点以下を四捨五入）
            const totalScoreElement = document.getElementById('total-score');
            const totalJudgmentElement = document.getElementById('total-judgment');
            
            if (totalScoreElement && totalJudgmentElement) {
                totalScoreElement.textContent = `${Math.round(response.totalScore)}点`;
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
                // 既存のコメントを削除
                const contentControls = context.document.contentControls;
                contentControls.load("items");
                await context.sync();

                contentControls.items.forEach(control => {
                    if (control.title === "評価コメント") {
                        control.delete();
                    }
                });
                await context.sync();

                // 新しいコメントを追加
                await this.addGroupedComments(context, evaluations);
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
            this.showStatus('評価を実行中...');

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

    /**
     * 文書構造を解析してブロックツリーを構築
     */
    private async buildDocumentBlocks(context: Word.RequestContext): Promise<DocumentBlock[]> {
        const paragraphs = context.document.body.paragraphs;
        paragraphs.load(["text", "firstLineIndent", "leftIndent"]);
        await context.sync();

        const blocks: DocumentBlock[] = [];
        let currentBlock: DocumentBlock | null = null;

        for (const paragraph of paragraphs.items) {
            const totalIndent = (paragraph.firstLineIndent || 0) + (paragraph.leftIndent || 0);
            const level = this.getIndentLevel(totalIndent);
            
            const newBlock = {
                level,
                text: paragraph.text,
                range: paragraph.getRange(),
                children: []
            };

            if (!currentBlock) {
                blocks.push(newBlock);
            } else if (level > currentBlock.level) {
                newBlock.parent = currentBlock;
                currentBlock.children.push(newBlock);
            } else {
                let parent = currentBlock.parent;
                while (parent && level <= parent.level) {
                    parent = parent.parent;
                }
                if (parent) {
                    newBlock.parent = parent;
                    parent.children.push(newBlock);
                } else {
                    blocks.push(newBlock);
                }
            }
            
            currentBlock = newBlock;
        }

        return blocks;
    }

    /**
     * インデントレベルを判定
     */
    private getIndentLevel(totalIndent: number): number {
        if (totalIndent <= 0) return 1;    // サマリー
        if (totalIndent <= 30) return 2;   // ストーリー
        if (totalIndent <= 50) return 3;   // ボディー
        return 0;                          // その他
    }

    /**
     * コメントの追加位置を決定
     */
    private async determineCommentPosition(
        context: Word.RequestContext,
        evaluation: { categoryId: string; location: string; feedback: string }
    ): Promise<Word.Range | null> {
        const blocks = await this.buildDocumentBlocks(context);

        // 評価対象範囲に基づいて位置を決定
        switch (evaluation.categoryId) {
            case 'FULL_DOCUMENT':
            case 'SUMMARY_ONLY':
                // タイトル部分（最初のブロック）を返す
                return blocks[0]?.range || null;

            case 'SUMMARY_AND_STORY': {
                // ストーリーに対応するサマリーを探す
                const storyBlock = this.findBlockByText(blocks, evaluation.location);
                if (!storyBlock) return null;

                // 親のサマリーブロックを探す
                let current = storyBlock;
                while (current.parent && current.parent.level > 1) {
                    current = current.parent;
                }
                // サマリーが見つからない場合は現在の位置を使用
                return current.parent?.range || storyBlock.range;
            }

            case 'STORY_AND_BODY': {
                // Bodyに対応するストーリーを探す
                const bodyBlock = this.findBlockByText(blocks, evaluation.location);
                if (!bodyBlock) return null;

                // 親のストーリーブロックを探す
                let current = bodyBlock;
                while (current.parent && current.parent.level > 2) {
                    current = current.parent;
                }
                // ストーリーが見つからない場合は現在の位置を使用
                return current.parent?.range || bodyBlock.range;
            }

            default:
                return null;
        }
    }

    /**
     * テキストからブロックを検索
     */
    private findBlockByText(blocks: DocumentBlock[], targetText: string): DocumentBlock | null {
        for (const block of blocks) {
            if (block.text.includes(targetText)) {
                return block;
            }
            const found = this.findBlockByText(block.children, targetText);
            if (found) return found;
        }
        return null;
    }

    /**
     * グループ化されたコメントを追加
     */
    private async addGroupedComments(
        context: Word.RequestContext,
        evaluations: Array<{ categoryId: string; location: string; feedback: string }>
    ): Promise<void> {
        // コメントをロケーションごとにグループ化
        const commentGroups = new Map<string, GroupedComment>();
        
        for (const evaluation of evaluations) {
            const range = await this.determineCommentPosition(context, evaluation);
            if (!range) continue;

            const rangeId = range.text;  // テキストをIDとして使用
            if (!commentGroups.has(rangeId)) {
                commentGroups.set(rangeId, {
                    range: range,
                    comments: []
                });
            }
            commentGroups.get(rangeId)?.comments.push(evaluation.feedback);
        }

        // グループ化されたコメントを追加
        for (const [_, group] of commentGroups) {
            const commentText = group.comments
                .map(comment => `• ${comment}`)
                .join('\n');
            
            // コメントをコンテンツコントロールとして追加
            const contentControl = group.range.insertContentControl();
            contentControl.title = "評価コメント";
            contentControl.insertText(commentText, Word.InsertLocation.end);
        }
        
        await context.sync();
    }
} 