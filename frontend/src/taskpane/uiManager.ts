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

interface EvaluationComment {
    categoryId: string;
    criteriaId: string;
    feedback: string;
    location: string;
    score: number;
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
            console.log('評価結果:', response);
            
            // エラーチェック
            if (response.error) {
                this.showError(`評価中にエラーが発生しました: ${response.error}`);
                return;
            }

            // 総合評価の表示
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
                if (!elementIds) return;

                const judgmentElement = document.getElementById(elementIds.judgmentId);
                if (judgmentElement) {
                    // スコアに基づいてOK/NGを判定
                    const judgment = categoryScore.score >= 0.8 ? "OK" : "NG";
                    judgmentElement.textContent = judgment;
                    judgmentElement.setAttribute('data-status', judgment);
                }
            });

            // 評価コメントを追加
            const evaluationComments = response.evaluations.map(evaluation => ({
                categoryId: evaluation.categoryId,
                criteriaId: evaluation.criteriaId,
                feedback: evaluation.feedback,
                location: evaluation.location,
                score: evaluation.score
            }));

            console.log('作成されたコメント:', evaluationComments);

            // コメントを追加
            this.addCommentsToDocument(evaluationComments)
                .then(() => {
                    this.showStatus('評価が完了しました');
                })
                .catch(error => {
                    this.showError(`コメントの追加中にエラーが発生しました: ${error instanceof Error ? error.message : String(error)}`);
                });

        } catch (error) {
            console.error('Error displaying evaluation results:', error);
            this.showError('評価結果の表示中にエラーが発生しました');
        }
    }

    /**
     * インデントレベルを判定
     */
    private getIndentLevel(firstLineIndent: number, leftIndent: number): number {
        // インデント情報の詳細ログ
        this.logger.debug(`
=== インデント判定の詳細 ===
- firstLineIndent: ${firstLineIndent}
- leftIndent: ${leftIndent}
- totalIndent: ${firstLineIndent + leftIndent}
`);

        // サマリーパターンの判定
        if (firstLineIndent <= -21 && leftIndent >= 21 && leftIndent <= 22) {
            this.logger.debug('サマリーパターンを検出: 逆インデントと左インデントが相殺');
            return 1; // サマリー
        }

        // ストーリーパターンの判定
        if (firstLineIndent <= -21 && leftIndent >= 42 && leftIndent <= 43) {
            this.logger.debug('ストーリーパターンを検出: 大きな逆インデントと左インデント');
            return 2; // ストーリー
        }

        // 本文パターンの判定
        if (firstLineIndent <= -21 && leftIndent >= 63 && leftIndent <= 64) {
            this.logger.debug('本文パターンを検出: より大きな左インデント');
            return 3; // 本文
        }

        // インデント分布の記録
        if (!this.documentStructure.indentDistribution) {
            this.documentStructure.indentDistribution = new Map<number, number>();
        }
        const totalIndent = firstLineIndent + leftIndent;
        const currentCount = this.documentStructure.indentDistribution.get(totalIndent) || 0;
        this.documentStructure.indentDistribution.set(totalIndent, currentCount + 1);

        // インデント分布の分析ログ
        this.logger.debug(`
=== インデント分布の更新 ===
- 現在のインデント値: ${totalIndent}
- 出現回数: ${currentCount + 1}
`);

        // デフォルトの判定（インデント値に基づく）
        if (totalIndent <= 0) {
            this.logger.debug('デフォルト判定: サマリー');
            return 1; // サマリー
        } else if (totalIndent <= 21) {
            this.logger.debug('デフォルト判定: ストーリー');
            return 2; // ストーリー
        } else if (totalIndent <= 42) {
            this.logger.debug('デフォルト判定: 本文');
            return 3; // 本文
        } else {
            this.logger.debug('デフォルト判定: 詳細');
            return 4; // 詳細
        }
    }

    /**
     * 文書構造を解析
     */
    private async analyzeDocumentStructure(): Promise<void> {
        try {
            await Word.run(async context => {
                const paragraphs = context.document.body.paragraphs;
                paragraphs.load(["text", "firstLineIndent", "leftIndent"]);
                await context.sync();

                // 文書構造の初期化
                this.documentStructure = {
                    indentLevels: [],
                    paragraphTypes: new Map(),
                    indentDistribution: new Map()
                };

                const structureCounts = {
                    summary: 0,
                    story: 0,
                    body: 0,
                    detail: 0
                };

                this.logger.debug('\n=== 文書構造解析開始 ===');
                this.logger.debug(`総段落数: ${paragraphs.items.length}`);

                // 各段落のインデントレベルを判定
                for (const paragraph of paragraphs.items) {
                    const text = paragraph.text.trim();
                    if (!text) continue;

                    const firstLineIndent = paragraph.firstLineIndent || 0;
                    const leftIndent = paragraph.leftIndent || 0;

                    this.logger.debug(`
=== 段落解析 ===
テキスト: ${text.substring(0, 100)}${text.length > 100 ? '...' : ''}
インデント情報:
- firstLineIndent: ${firstLineIndent}
- leftIndent: ${leftIndent}
`);

                    const level = this.getIndentLevel(firstLineIndent, leftIndent);
                    this.documentStructure.indentLevels.push(level);

                    // 段落タイプのカウントと記録
                    switch (level) {
                        case 1:
                            structureCounts.summary++;
                            this.logger.debug(`サマリー段落として分類: ${text.substring(0, 50)}...`);
                            break;
                        case 2:
                            structureCounts.story++;
                            this.logger.debug(`ストーリー段落として分類: ${text.substring(0, 50)}...`);
                            break;
                        case 3:
                            structureCounts.body++;
                            this.logger.debug(`本文段落として分類: ${text.substring(0, 50)}...`);
                            break;
                        case 4:
                            structureCounts.detail++;
                            this.logger.debug(`詳細段落として分類: ${text.substring(0, 50)}...`);
                            break;
                    }
                }

                // 文書構造の分析結果
                this.logger.debug(`
=== 文書構造の分析結果 ===
サマリー段落数: ${structureCounts.summary}
ストーリー段落数: ${structureCounts.story}
本文段落数: ${structureCounts.body}
詳細段落数: ${structureCounts.detail}
`);

                // 構造の妥当性チェック
                if (structureCounts.summary === 0 || 
                    structureCounts.story === 0 || 
                    structureCounts.body === 0) {
                    this.logger.warn(`
=== 文書構造の警告 ===
サマリーなし: ${structureCounts.summary === 0}
ストーリーなし: ${structureCounts.story === 0}
本文なし: ${structureCounts.body === 0}
`);
                }

                await context.sync();
            });
        } catch (error) {
            this.logger.error("文書構造の解析中にエラーが発生:", error);
            throw error;
        }
    }

    /**
     * コメントを追加する前に文書構造をチェック
     */
    private async addCommentsToDocument(evaluations: EvaluationComment[]): Promise<void> {
        try {
            console.log('=== コメント追加処理開始 ===');
            console.log('評価コメント数:', evaluations.length);
            
            await Word.run(async context => {
                const paragraphs = context.document.body.paragraphs;
                paragraphs.load(["items", "text", "listItem", "listItem/level", "firstLineIndent", "leftIndent"]);
                await context.sync();

                // 文書構造の解析
                const documentSections = {
                    summary: [] as Word.Paragraph[],
                    story: [] as Word.Paragraph[],
                    body: [] as Word.Paragraph[],
                    detail: [] as Word.Paragraph[]
                };

                console.log('\n=== 段落の分類開始 ===');
                console.log('総段落数:', paragraphs.items.length);

                // 段落の分類
                for (const paragraph of paragraphs.items) {
                    const text = paragraph.text.trim();
                    if (!text) continue;

                    // インデントレベルとリストレベルの両方を考慮
                    let level = 0;
                    try {
                        if (paragraph.listItem) {
                            level = paragraph.listItem.level + 1;
                            console.log('リストレベルを検出:', {
                                text: text.substring(0, 30),
                                level: level
                            });
                        } else {
                            // インデントに基づくレベル判定
                            const firstLineIndent = paragraph.firstLineIndent || 0;
                            const leftIndent = paragraph.leftIndent || 0;
                            level = this.getIndentLevel(firstLineIndent, leftIndent);
                            console.log('インデントレベルを検出:', {
                                text: text.substring(0, 30),
                                firstLineIndent,
                                leftIndent,
                                level
                            });
                        }
                    } catch (error) {
                        console.warn('段落レベルの取得に失敗:', {
                            text: text.substring(0, 30),
                            error: error instanceof Error ? error.message : String(error)
                        });
                        continue;
                    }

                    // レベルに基づいて段落を分類
                    switch (level) {
                        case 1:
                            documentSections.summary.push(paragraph);
                            console.log('サマリーとして分類:', text.substring(0, 30));
                            break;
                        case 2:
                            documentSections.story.push(paragraph);
                            console.log('ストーリーとして分類:', text.substring(0, 30));
                            break;
                        case 3:
                            documentSections.body.push(paragraph);
                            console.log('本文として分類:', text.substring(0, 30));
                            break;
                        default:
                            documentSections.detail.push(paragraph);
                            console.log('詳細として分類:', text.substring(0, 30));
                            break;
                    }
                }

                console.log('\n=== 文書構造解析結果 ===');
                console.log({
                    サマリー数: documentSections.summary.length,
                    ストーリー数: documentSections.story.length,
                    本文数: documentSections.body.length,
                    詳細数: documentSections.detail.length
                });

                // 評価コメントの追加
                for (const evaluation of evaluations) {
                    console.log('\n--- 評価処理開始 ---');
                    console.log({
                        カテゴリ: evaluation.categoryId,
                        評価基準: evaluation.criteriaId,
                        評価スコア: evaluation.score,
                        対象箇所: evaluation.location || '指定なし'
                    });

                    const categoryInfo = CATEGORY_EVALUATION_MAPPING[evaluation.categoryId as keyof CategoryMapping];
                    if (!categoryInfo) {
                        console.warn('未知のカテゴリID:', evaluation.categoryId);
                        continue;
                    }

                    let targetParagraphs: Word.Paragraph[] = [];
                    
                    // 評価範囲に基づいてターゲット段落を決定
                    switch (categoryInfo.targetSection) {
                        case 'all':
                            targetParagraphs = [...documentSections.summary, ...documentSections.story, ...documentSections.body];
                            console.log('全体を評価対象に設定');
                            break;
                        case 'summary':
                            targetParagraphs = documentSections.summary;
                            console.log('サマリーを評価対象に設定');
                            break;
                        case 'story':
                            targetParagraphs = documentSections.story;
                            console.log('ストーリーを評価対象に設定');
                            break;
                        case 'body':
                            targetParagraphs = documentSections.body;
                            console.log('本文を評価対象に設定');
                            break;
                        case 'summary_story':
                            targetParagraphs = [...documentSections.summary, ...documentSections.story];
                            console.log('サマリーとストーリーを評価対象に設定');
                            break;
                    }

                    console.log('評価対象段落数:', targetParagraphs.length);

                    if (targetParagraphs.length === 0) {
                        console.warn(`${categoryInfo.description}のターゲット段落が見つかりません`);
                        // 代替の配置先を探す
                        if (documentSections.summary.length > 0) {
                            targetParagraphs = documentSections.summary;
                            console.log('代替：サマリーに配置');
                        } else if (documentSections.story.length > 0) {
                            targetParagraphs = documentSections.story;
                            console.log('代替：ストーリーに配置');
                        } else if (documentSections.body.length > 0) {
                            targetParagraphs = documentSections.body;
                            console.log('代替：本文に配置');
                        }
                    }

                    if (targetParagraphs.length === 0) {
                        console.error('コメントを配置する段落が見つかりません');
                        continue;
                    }

                    // コメントの配置
                    let targetParagraph = targetParagraphs[0];
                    if (evaluation.location) {
                        // 特定の文章が指定されている場合は、その文章を含む段落を探す
                        const matchingParagraph = targetParagraphs.find(p => 
                            p.text.trim().includes(evaluation.location.trim())
                        );
                        if (matchingParagraph) {
                            targetParagraph = matchingParagraph;
                            console.log('指定された位置に配置:', evaluation.location.substring(0, 30));
                        } else {
                            console.log('指定位置が見つからないため、最初の段落に配置');
                        }
                    }

                    try {
                        const range = targetParagraph.getRange();
                        const icon = evaluation.score >= 0.8 ? "✓" : "⚠";
                        const formattedFeedback = `${icon} ${evaluation.criteriaId}\n${evaluation.feedback}`;
                        
                        console.log('コメントを追加:', {
                            対象段落: targetParagraph.text.substring(0, 30),
                            コメント: formattedFeedback
                        });

                        const comment = range.insertComment(formattedFeedback);
                        comment.load("text");
                        await context.sync();
                        console.log('コメント追加成功');
                    } catch (error) {
                        console.error('コメント追加エラー:', error);
                    }
                }

                await context.sync();
                console.log('=== コメント追加処理完了 ===');
            });
        } catch (error) {
            console.error('コメント追加処理でエラー発生:', error);
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
            console.log('文書構造:', structure);

            // 文書評価を実行
            const result = await reviewDocument(structure);
            if (!result) {
                throw new Error("評価結果が不正です");
            }

            // 評価結果を表示
            await this.displayEvaluationResults(result);

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
            if (block.children) {
                const found = this.findBlockByText(block.children, targetText);
                if (found) return found;
            }
        }
        return null;
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
            const level = this.getIndentLevel(paragraph.firstLineIndent || 0, paragraph.leftIndent || 0);
            
            const newBlock: DocumentBlock = {
                level,
                text: paragraph.text,
                range: paragraph.getRange(),
                children: [],
                parent: null
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
} 