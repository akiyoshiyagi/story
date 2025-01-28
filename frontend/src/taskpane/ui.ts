/**
 * UI操作を管理するクラス
 */
import { UI_CONSTANTS } from "./const";
import { getDocumentStructure } from "./documentUtil";
import { reviewDocument, checkApiHealth } from "./api";
import type { EvaluationResult } from "./types";

// 評価カテゴリとIDのマッピング
const CATEGORY_ID_MAP = {
    "全文修辞表現": "full-text-rhetoric",
    "サマリーの論理展開": "summary-logic-flow",
    "サマリー単体の論理": "summary-internal-logic",
    "サマリーとストーリー間の論理": "summary-story-logic",
    "ストーリー単体の論理": "story-internal-logic",
    "細部の修辞表現": "detail-rhetoric"
};

export class UIManager {
    private scoreElement: HTMLElement;
    private statusElement: HTMLElement;
    private checkButton: HTMLButtonElement;
    private loadingSpinner: HTMLElement;

    constructor() {
        this.scoreElement = document.getElementById("score") as HTMLElement;
        this.checkButton = document.getElementById("check-button") as HTMLButtonElement;
        this.statusElement = document.getElementById("status") as HTMLElement;
        this.loadingSpinner = document.getElementById("loading-spinner") as HTMLElement;
        
        // 初期状態をセット
        this.resetEvaluations();
        this.initializeErrorHandling();
        this.initializeInteractivity();
        this.initializeAccessibility();
    }

    /**
     * エラーハンドリングの初期化
     */
    private initializeErrorHandling(): void {
        window.onerror = (message, source, lineno, colno, error) => {
            console.error("Global error:", { message, source, lineno, colno, error });
            this.displayError("予期せぬエラーが発生しました。");
            return false;
        };

        window.onunhandledrejection = (event) => {
            console.error("Unhandled promise rejection:", event.reason);
            this.displayError("非同期処理でエラーが発生しました。");
        };
    }

    /**
     * インタラクティブな機能を初期化
     */
    private initializeInteractivity(): void {
        // 評価項目のクリックイベント
        document.querySelectorAll('.evaluation-item').forEach(item => {
            const header = item.querySelector('.evaluation-header');
            const content = item.querySelector('.evaluation-content');
            
            if (header && content) {
                header.addEventListener('click', () => {
                    // 展開状態を切り替え
                    const isExpanded = content.classList.contains('expanded');
                    content.classList.toggle('expanded');
                    
                    // アイコンの回転
                    const icon = header.querySelector('.expand-icon');
                    if (icon) {
                        icon.classList.toggle('rotated');
                    }
                    
                    // 高さを調整
                    if (isExpanded) {
                        (content as HTMLElement).style.maxHeight = '150px';
                    } else {
                        const scrollHeight = (content as HTMLElement).scrollHeight;
                        (content as HTMLElement).style.maxHeight = `${scrollHeight}px`;
                    }
                });
            }
        });

        // ツールチップの初期化
        this.initializeTooltips();

        // キーボードショートカット
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter でチェック実行
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                this.handleCheckDocument();
            }
        });
    }

    /**
     * ツールチップを初期化
     */
    private initializeTooltips(): void {
        const tooltips = {
            'score': '文書全体の評価スコアです（100点満点）',
            'status-full-text-rhetoric': '文章全体の表現や読みやすさを評価',
            'status-summary-logic-flow': 'サマリー部分の論理展開を評価',
            'status-summary-internal-logic': 'サマリー内部の論理的整合性を評価',
            'status-summary-story-logic': 'サマリーとストーリーの関連性を評価',
            'status-story-internal-logic': '各ストーリーの論理的整合性を評価',
            'status-detail-rhetoric': '細部の表現や用語の適切さを評価'
        };

        Object.entries(tooltips).forEach(([id, text]) => {
            const element = document.getElementById(id);
            if (element) {
                element.setAttribute('title', text);
                element.classList.add('has-tooltip');
                
                // ホバー時のツールチップ表示
                element.addEventListener('mouseenter', (e) => {
                    const tooltip = document.createElement('div');
                    tooltip.className = 'tooltip';
                    tooltip.textContent = text;
                    
                    // 位置を調整
                    const rect = element.getBoundingClientRect();
                    tooltip.style.left = `${rect.left}px`;
                    tooltip.style.top = `${rect.bottom + 5}px`;
                    
                    document.body.appendChild(tooltip);
                });
                
                element.addEventListener('mouseleave', () => {
                    const tooltip = document.querySelector('.tooltip');
                    if (tooltip) {
                        tooltip.remove();
                    }
                });
            }
        });
    }

    /**
     * アクセシビリティ対応を初期化
     */
    private initializeAccessibility(): void {
        // 評価項目のARIA属性を設定
        document.querySelectorAll('.evaluation-item').forEach((item, index) => {
            const header = item.querySelector('.evaluation-header');
            const content = item.querySelector('.evaluation-content');
            
            if (header && content) {
                // ARIA属性を設定
                const headerId = `evaluation-header-${index}`;
                const contentId = `evaluation-content-${index}`;
                
                header.setAttribute('id', headerId);
                header.setAttribute('role', 'button');
                header.setAttribute('aria-expanded', 'false');
                header.setAttribute('aria-controls', contentId);
                header.setAttribute('tabindex', '0');
                
                content.setAttribute('id', contentId);
                content.setAttribute('role', 'region');
                content.setAttribute('aria-labelledby', headerId);
                
                // キーボード操作
                header.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        header.click();
                    }
                });
            }
        });

        // スコアと評価状態の読み上げ対応
        this.scoreElement.setAttribute('role', 'status');
        this.scoreElement.setAttribute('aria-label', 'ドキュメント評価スコア');
        
        // ステータスメッセージの読み上げ対応
        this.statusElement.setAttribute('role', 'alert');
        this.statusElement.setAttribute('aria-live', 'polite');
        
        // ローディング状態の通知
        this.loadingSpinner.setAttribute('role', 'progressbar');
        this.loadingSpinner.setAttribute('aria-label', '処理中');
    }

    /**
     * スコアを表示する
     */
    displayScore(score: number): void {
        this.scoreElement.textContent = score.toString();
    }

    /**
     * ステータスメッセージを表示する
     */
    displayStatus(message: string, isError: boolean = false, type: "normal" | "retry" | "error" = "normal"): void {
        const statusElement = document.getElementById("status");
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `status ${type}`;
            
            if (type === "retry") {
                statusElement.classList.add("loading");
            } else {
                statusElement.classList.remove("loading");
            }
        }
    }

    /**
     * 評価結果を表示する
     */
    async displayEvaluations(evaluations: EvaluationResult[]): Promise<void> {
        // 初期状態にリセット
        this.resetEvaluations();
        
        // 各評価結果を表示
        evaluations.forEach(evaluation => {
            const categoryId = CATEGORY_ID_MAP[evaluation.category];
            if (!categoryId) return;

            // ステータスを更新
            const statusElement = document.getElementById(`status-${categoryId}`);
            if (statusElement) {
                const status = evaluation.score >= 0.7 ? "OK" : "NG";
                statusElement.textContent = status;
                statusElement.className = `evaluation-status ${evaluation.score >= 0.7 ? "ok" : "ng"}`;
                
                // アクセシビリティ対応
                statusElement.setAttribute('role', 'status');
                statusElement.setAttribute('aria-label', `${evaluation.category}の評価: ${status}`);
            }

            // 評価内容を更新
            const contentElement = document.getElementById(`content-${categoryId}`);
            if (contentElement) {
                let content = '<div class="feedback-section">';
                
                // フィードバックを表示
                if (evaluation.feedback.length > 0) {
                    content += '<div class="feedback-points" role="list" aria-label="評価ポイント">';
                    content += '<h4>評価ポイント</h4>';
                    content += '<ul>';
                    evaluation.feedback.forEach(feedback => {
                        const isPositive = !feedback.includes("改善") && !feedback.includes("不足") && !feedback.includes("問題");
                        content += `<li class="${isPositive ? 'positive' : 'negative'}" role="listitem">${feedback}</li>`;
                    });
                    content += '</ul></div>';
                }

                // スコアの詳細を表示
                content += `<div class="score-detail" role="region" aria-label="スコア詳細">
                    <div class="score-bar-container">
                        <div class="score-bar" style="width: ${evaluation.score * 100}%" role="progressbar" aria-valuenow="${Math.round(evaluation.score * 100)}" aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                    <div class="score-value">${Math.round(evaluation.score * 100)}点</div>
                </div>`;

                // 改善提案を表示
                if (evaluation.improvement_suggestions.length > 0) {
                    content += '<div class="suggestions" role="list" aria-label="改善提案">';
                    content += '<h4>改善提案</h4>';
                    content += '<ul>';
                    evaluation.improvement_suggestions.forEach(suggestion => {
                        content += `<li class="suggestion-item" role="listitem">${suggestion}</li>`;
                    });
                    content += '</ul></div>';
                }

                content += '</div>';
                contentElement.innerHTML = content;

                // アニメーション効果を追加
                contentElement.classList.add('fade-in');
                setTimeout(() => {
                    contentElement.classList.remove('fade-in');
                }, 500);
            }
        });

        // Word文書にコメントを追加
        try {
            await this.addCommentsToDocument(evaluations);
        } catch (error) {
            console.error("Error adding comments to document:", error);
            this.displayError("評価コメントの追加中にエラーが発生しました");
        }
    }

    /**
     * ローディング状態を設定する
     */
    setLoading(isLoading: boolean): void {
        this.checkButton.disabled = isLoading;
        this.loadingSpinner.style.display = isLoading ? "block" : "none";
        if (isLoading) {
            this.displayStatus(UI_CONSTANTS.LOADING_MESSAGE);
            this.checkButton.classList.add("loading");
        } else {
            this.checkButton.classList.remove("loading");
        }
    }

    /**
     * エラーを表示する
     */
    displayError(message: string): void {
        const statusElement = document.getElementById("status");
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = "status error";
            
            // エラーメッセージの後に回復手順を表示
            const recoverySteps = this.getRecoverySteps(message);
            if (recoverySteps) {
                const recoveryElement = document.createElement("div");
                recoveryElement.className = "recovery-steps";
                recoveryElement.innerHTML = recoverySteps;
                statusElement.appendChild(recoveryElement);
            }
        }
    }

    /**
     * エラーの回復手順を取得する
     */
    private getRecoverySteps(errorMessage: string): string {
        if (errorMessage.includes("Word との接続")) {
            return `
                <h3>問題を解決するには:</h3>
                <ol>
                    <li>アドインのタスクペインを閉じる</li>
                    <li>Word文書を保存する</li>
                    <li>Word を再起動する</li>
                    <li>アドインを再度開く</li>
                </ol>
            `;
        }
        if (errorMessage.includes("文書の構造")) {
            return `
                <h3>文書構造を修正するには:</h3>
                <ol>
                    <li>各セクションのインデントを確認:
                        <ul>
                            <li>サマリー → インデントなし</li>
                            <li>ストーリー → 1段階インデント</li>
                            <li>詳細 → 2段階インデント</li>
                        </ul>
                    </li>
                    <li>空の行が含まれていないか確認する</li>
                    <li>修正後、再度チェックを実行する</li>
                </ol>
            `;
        }
        if (errorMessage.includes("サーバーとの通信")) {
            return `
                <h3>接続問題を解決するには:</h3>
                <ol>
                    <li>インターネット接続を確認する</li>
                    <li>ファイアウォールの設定を確認する</li>
                    <li>1-2分待ってから再度試す</li>
                    <li>問題が続く場合は管理者に連絡する</li>
                </ol>
            `;
        }
        return "";
    }

    /**
     * 評価結果表示をリセットする
     */
    private resetEvaluations(): void {
        // すべての評価ステータスをリセット
        Object.values(CATEGORY_ID_MAP).forEach(id => {
            const statusElement = document.getElementById(`status-${id}`);
            if (statusElement) {
                statusElement.textContent = "-";
                statusElement.className = "evaluation-status";
            }

            const contentElement = document.getElementById(`content-${id}`);
            if (contentElement) {
                contentElement.innerHTML = "";
            }
        });
    }

    /**
     * 操作を再試行する
     */
    private async retryOperation<T>(
        operation: () => Promise<T>,
        maxRetries: number = 3,
        delayMs: number = 1000
    ): Promise<T> {
        let lastError: Error;
        
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                return await operation();
            } catch (error) {
                lastError = error instanceof Error ? error : new Error(String(error));
                
                if (attempt < maxRetries) {
                    // リトライ中のステータス表示
                    this.displayStatus(
                        `再試行中... (${attempt}/${maxRetries})`,
                        false,
                        "retry"
                    );
                    
                    // 待機時間を設定（指数バックオフ）
                    const waitTime = delayMs * Math.pow(2, attempt - 1);
                    await new Promise(resolve => setTimeout(resolve, waitTime));
                }
            }
        }
        
        throw lastError;
    }

    /**
     * ドキュメントのチェック処理を実行
     */
    public async handleCheckDocument(): Promise<void> {
        try {
            // 処理開始前の状態をリセット
            this.resetEvaluations();
            this.setLoading(true);

            // APIの健全性をチェック（リトライ機能付き）
            const isHealthy = await this.retryOperation(
                () => checkApiHealth(),
                3,  // 最大3回リトライ
                1000  // 1秒間隔
            );
            
            if (!isHealthy) {
                throw new Error("APIサーバーに接続できません");
            }

            // 文書構造を取得（リトライ機能付き）
            const structure = await this.retryOperation(
                () => getDocumentStructure(),
                2,  // 最大2回リトライ
                500   // 0.5秒間隔
            );

            // 文書評価を実行（リトライ機能付き）
            const result = await this.retryOperation(
                () => reviewDocument(structure),
                3,  // 最大3回リトライ
                1000  // 1秒間隔
            );

            if (!result || !result.evaluations) {
                throw new Error("評価結果が不正です");
            }

            // 評価結果を表示
            this.displayScore(result.total_score);
            this.displayEvaluations(result.evaluations);
            this.displayStatus("評価が完了しました", false, "normal");

        } catch (error) {
            console.error("Error in handleCheckDocument:", error);
            const errorMessage = this.getErrorMessage(error);
            this.displayError(errorMessage);
        } finally {
            this.setLoading(false);
        }
    }

    /**
     * エラーメッセージを取得する
     */
    private getErrorMessage(error: unknown): string {
        if (error instanceof Error) {
            // 具体的なエラーケースごとに分かりやすいメッセージを返す
            if (error.message.includes("Office.js")) {
                return "Word との接続に問題が発生しました。アドインを再読み込みしてください。";
            }
            if (error.message.includes("文書構造")) {
                return "文書の構造を正しく読み取れませんでした。インデントの形式が正しいか確認してください。\n" +
                       "【確認項目】\n" +
                       "・サマリーは左端に配置されているか\n" +
                       "・ストーリーは1段階インデントされているか\n" +
                       "・詳細は2段階インデントされているか";
            }
            if (error.message.includes("API")) {
                return "サーバーとの通信に問題が発生しました。インターネット接続を確認し、しばらく待ってから再度お試しください。";
            }
            if (error.message.includes("評価結果")) {
                return "文書の評価中にエラーが発生しました。文書の内容が正しく入力されているか確認してください。";
            }
            return `エラーが発生しました: ${error.message}`;
        }
        return "予期せぬエラーが発生しました。アドインを再読み込みしてください。";
    }

    /**
     * 評価コメントをWord文書に追加する
     */
    private async addCommentsToDocument(evaluations: EvaluationResult[]): Promise<void> {
        try {
            console.log("コメント追加処理を開始します");
            console.log("評価結果:", evaluations);

            await Word.run(async (context) => {
                // 文書全体のパラグラフを取得
                console.log("文書のパラグラフを取得中...");
                const paragraphs = context.document.body.paragraphs;
                paragraphs.load("text");
                await context.sync();
                console.log(`取得したパラグラフ数: ${paragraphs.items.length}`);

                // パラグラフの内容をログ出力
                console.log("\n=== 文書の構造 ===");
                for (let i = 0; i < paragraphs.items.length; i++) {
                    console.log(`[段落 ${i + 1}] ${paragraphs.items[i].text}`);
                }
                console.log("==================");

                // 既に処理した文章を追跡（パラグラフのインデックスと文章の組み合わせで管理）
                const processedSentences = new Set<string>();

                // 各文章に対する評価をグループ化
                console.log("評価結果をグループ化中...");
                const evaluationsByTargetSentence = new Map<string, EvaluationResult[]>();
                for (const evaluation of evaluations) {
                    if (!evaluation.target_sentence) {
                        console.log("対象文が空の評価をスキップ:", evaluation);
                        continue;
                    }
                    
                    const current = evaluationsByTargetSentence.get(evaluation.target_sentence) || [];
                    current.push(evaluation);
                    evaluationsByTargetSentence.set(evaluation.target_sentence, current);
                }
                console.log("グループ化された評価:", Object.fromEntries(evaluationsByTargetSentence));

                // 各文章に対して評価を追加
                for (const [targetSentence, sentenceEvaluations] of evaluationsByTargetSentence) {
                    console.log(`\n対象文「${targetSentence}」の処理を開始`);

                    // 評価を優先度でソート
                    const sortedEvaluations = sentenceEvaluations.sort((a, b) => {
                        if (a.priority === b.priority) {
                            return b.score - a.score; // スコアが高い順
                        }
                        return a.priority - b.priority; // 優先度が低い順
                    });

                    // 最優先の評価を取得
                    const topEvaluation = sortedEvaluations[0];
                    console.log("最優先の評価:", {
                        priority: topEvaluation.priority,
                        category: topEvaluation.category,
                        score: topEvaluation.score,
                        feedback: topEvaluation.feedback,
                        suggestions: topEvaluation.improvement_suggestions
                    });

                    try {
                        // 対象文を含むパラグラフを検索
                        console.log("マッチするパラグラフを検索中...");
                        const matchingParagraphs = this.findMatchingParagraphs(targetSentence, paragraphs.items);
                        console.log(`マッチしたパラグラフ数: ${matchingParagraphs.length}`);

                        // マッチしたパラグラフにコメントを追加
                        for (const match of matchingParagraphs) {
                            const key = `${match.index}-${targetSentence}`;
                            if (!processedSentences.has(key)) {
                                console.log(`パラグラフ ${match.index + 1} にコメントを追加中...`);
                                const range = paragraphs.items[match.index].getRange();
                                await context.sync();

                                // フィードバックと改善提案をフィルタリング
                                const validFeedback = topEvaluation.feedback.filter(f => !this.isPositiveFeedback(f));
                                console.log("有効なフィードバック:", validFeedback);
                                
                                // 改善提案が存在する場合は、それに対応する課題点を生成
                                if (topEvaluation.improvement_suggestions.length > 0) {
                                    // コメントの内容を構築
                                    let commentContent = `[${topEvaluation.category}]\n\n`;
                                    
                                    // 課題点セクション
                                    commentContent += `【課題点】\n`;
                                    if (validFeedback.length > 0) {
                                        // 既存のフィードバックを使用
                                        validFeedback.forEach(feedback => {
                                            commentContent += `・${feedback}\n`;
                                        });
                                    } else {
                                        // 改善提案から課題点を推測
                                        const issue = this.inferIssueFromSuggestion(topEvaluation.improvement_suggestions[0]);
                                        commentContent += `・${issue}\n`;
                                    }
                                    
                                    // 改善提案セクション
                                    commentContent += `\n【改善提案】\n`;
                                    topEvaluation.improvement_suggestions.forEach(suggestion => {
                                        commentContent += `・${suggestion}\n`;
                                    });

                                    console.log("追加するコメント内容:", commentContent);

                                    try {
                                        // コメントを追加
                                        await range.insertComment(commentContent);
                                        await context.sync();
                                        processedSentences.add(key);
                                        console.log(`コメントを追加しました: 段落 ${match.index + 1}`);
                                    } catch (commentError) {
                                        console.error("コメント追加中にエラーが発生:", commentError);
                                        throw commentError;
                                    }
                                } else {
                                    console.log("改善提案がないため、コメントをスキップします");
                                }
                            } else {
                                console.log(`パラグラフ ${match.index + 1} は既に処理済みのためスキップします`);
                            }
                        }
                    } catch (error) {
                        console.error("コメント追加中にエラーが発生:", error);
                        throw error; // エラーを上位に伝播
                    }
                }

                await context.sync();
                console.log("\nすべてのコメントを追加しました");
            });
        } catch (error) {
            console.error("コメント追加処理でエラーが発生:", error);
            throw error;
        }
    }

    /**
     * フィードバックがポジティブなものかどうかを判定
     */
    private isPositiveFeedback(feedback: string): boolean {
        const positiveKeywords = [
            "良好です",
            "適切です",
            "明確です",
            "統一されています",
            "問題ありません",
            "十分です",
            "概ね明確です"
        ];

        // ポジティブキーワードが含まれている場合は、ポジティブなフィードバック
        return positiveKeywords.some(keyword => feedback.includes(keyword));
    }

    /**
     * 改善提案から課題点を推測する
     */
    private inferIssueFromSuggestion(suggestion: string): string {
        // キーワードと課題点のマッピング
        const issuePatterns = [
            {
                keywords: ["一貫", "統一"],
                issue: "用語や表現の一貫性が不足しています"
            },
            {
                keywords: ["具体的", "詳細"],
                issue: "具体的な説明が不足しています"
            },
            {
                keywords: ["明確"],
                issue: "説明が不明確です"
            },
            {
                keywords: ["追加", "補足"],
                issue: "必要な情報が不足しています"
            },
            {
                keywords: ["修正", "改善"],
                issue: "表現が適切ではありません"
            },
            {
                keywords: ["構成", "順序"],
                issue: "文書の構成に問題があります"
            },
            {
                keywords: ["簡潔"],
                issue: "文章が冗長です"
            },
            {
                keywords: ["説明"],
                issue: "説明が不十分です"
            }
        ];

        // 改善提案の内容に基づいて適切な課題点を選択
        for (const pattern of issuePatterns) {
            if (pattern.keywords.some(keyword => suggestion.includes(keyword))) {
                return pattern.issue;
            }
        }

        // デフォルトの課題点
        return "記述に改善の余地があります";
    }

    /**
     * 対象文とパラグラフのマッチングを行う
     */
    private findMatchingParagraphs(targetSentence: string, paragraphs: Word.Paragraph[]): { index: number, text: string }[] {
        const matchingParagraphs = [];

        // 全体評価の場合は最初のパラグラフにコメントを追加
        if (targetSentence === "全体" || targetSentence === "本文全体" || targetSentence === "タイトルおよびサマリー") {
            matchingParagraphs.push({ index: 0, text: paragraphs[0].text });
            console.log("全体評価のため、最初のパラグラフを選択:", paragraphs[0].text);
            return matchingParagraphs;
        }

        // 引用符と余分な空白を除去
        const cleanTargetText = targetSentence.replace(/[「」""]/g, "").trim();
        
        // 各パラグラフをチェック
        for (let i = 0; i < paragraphs.length; i++) {
            const paragraphText = paragraphs[i].text.trim();
            
            // 完全一致または部分一致をチェック
            if (paragraphText === cleanTargetText || paragraphText.includes(cleanTargetText)) {
                console.log(`マッチしたパラグラフ ${i + 1}:`, paragraphText);
                matchingParagraphs.push({ index: i, text: paragraphText });
            }
        }

        return matchingParagraphs;
    }
} 