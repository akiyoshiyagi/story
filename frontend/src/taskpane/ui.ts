/**
 * UI操作を管理するクラス
 */
import { UI_CONSTANTS } from "./const";
import { getDocumentStructure } from "./documentUtil";
import { reviewDocument, checkApiHealth } from "./api";
import type { EvaluationResult, ReviewResponse } from "./types";

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
        // キーボードショートカット
        document.addEventListener('keydown', (event: Event) => {
            const keyboardEvent = event as KeyboardEvent;
            if ((keyboardEvent.ctrlKey || keyboardEvent.metaKey) && keyboardEvent.key === 'Enter') {
                this.handleCheckDocument();
            }
        });

        // 評価項目のクリックイベント
        document.querySelectorAll('.evaluation-item').forEach((item: Element) => {
            const header = item.querySelector('.evaluation-header');
            const content = item.querySelector('.evaluation-content');
            if (header instanceof HTMLElement && content instanceof HTMLElement) {
                const handleClick = (event: Event): void => {
                    // 展開状態を切り替え
                    const isExpanded = content.classList.contains('expanded');
                    content.classList.toggle('expanded');
                    
                    // アイコンの回転
                    const icon = header.querySelector('.expand-icon');
                    if (icon instanceof HTMLElement) {
                        icon.classList.toggle('rotated');
                    }
                    
                    // 高さを調整
                    if (isExpanded) {
                        content.style.maxHeight = '150px';
                    } else {
                        const scrollHeight = content.scrollHeight;
                        content.style.maxHeight = `${scrollHeight}px`;
                    }
                };
                header.addEventListener('click', handleClick);
            }
        });

        // ツールチップの初期化
        this.initializeTooltips();
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
        // スコアを100点満点に変換して表示
        const score100 = Math.round(score * 100);
        this.scoreElement.textContent = `${score100}`;
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
        
        console.log("=== 評価プロセス開始 ===");
        console.log("1. 受け取った評価結果:", evaluations);
        console.log("評価結果の数:", evaluations.length);
        
        // 評価結果の優先度分布を表示
        const priorityDistribution = evaluations.reduce((acc, curr) => {
            acc[curr.priority] = (acc[curr.priority] || 0) + 1;
            return acc;
        }, {} as { [key: number]: number });
        console.log("優先度の分布:", priorityDistribution);
        
        // 評価結果の詳細をログ出力
        evaluations.forEach((evaluation, index) => {
            console.log(`\n評価 ${index + 1} の詳細:`);
            console.log(`- カテゴリ: ${evaluation.category}`);
            console.log(`- Priority: ${evaluation.priority}`);
            console.log(`- 適用範囲: ${evaluation.applicable_to?.join(', ')}`);
            console.log(`- スコア: ${evaluation.score}`);
            console.log(`- 対象文: ${evaluation.target_sentence}`);
            console.log(`- フィードバック: ${evaluation.feedback?.join('\n  ')}`);
            console.log(`- 改善提案: ${evaluation.improvement_suggestions?.join('\n  ')}`);
        });

        // 最も優先度の高い課題のある評価のみをフィルタリング
        console.log("\n2. 優先度に基づくフィルタリングを開始");
        const highestPriorityNegativeEvaluations = this.filterHighestPriorityNegativeEvaluations(evaluations);
        console.log("フィルタリング後の評価数:", highestPriorityNegativeEvaluations.length);

        // フィルタリング後の優先度分布を表示
        const filteredPriorityDistribution = highestPriorityNegativeEvaluations.reduce((acc, curr) => {
            acc[curr.priority] = (acc[curr.priority] || 0) + 1;
            return acc;
        }, {} as { [key: number]: number });
        console.log("フィルタリング後の優先度分布:", filteredPriorityDistribution);

        // 評価内容を表示
        const contentElement = document.getElementById("evaluation-content");
        if (contentElement) {
            // 課題のある評価が見つからない場合
            if (highestPriorityNegativeEvaluations.length === 0) {
                console.log("\n3. 課題のある評価が見つかりませんでした");
                contentElement.innerHTML = '<div class="feedback-section"><div class="no-issues">課題は見つかりませんでした。</div></div>';
                return;
            }

            console.log("\n3. UIへの評価結果の表示を開始");
                let content = '<div class="feedback-section">';
            
            // 全体のスコアを計算（平均値）
            const averageScore = highestPriorityNegativeEvaluations.reduce((sum, evaluation) => sum + evaluation.score, 0) / highestPriorityNegativeEvaluations.length;
            const score100 = Math.round(averageScore * 100);
            console.log("計算されたスコア:", score100);

            // スコアの表示
            content += `<div class="score-detail" role="region" aria-label="スコア詳細">
                <div class="score-bar-container">
                    <div class="score-bar" style="width: ${score100}%" role="progressbar" aria-valuenow="${score100}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
                <div class="score-value">${score100}点</div>
            </div>`;

            // 評価結果をスコアの低い順にソート
            const sortedEvaluations = [...highestPriorityNegativeEvaluations].sort((a, b) => a.score - b.score);

            // 各評価の表示
            sortedEvaluations.forEach(evaluation => {
                content += '<div class="evaluation-item">';
                
                // 対象文章
                content += `<div class="target-sentence">${evaluation.target_sentence}</div>`;
                
                // フィードバックを表示
                if (evaluation.feedback && evaluation.feedback.length > 0) {
                    content += '<div class="feedback-points" role="list" aria-label="評価ポイント">';
                    content += '<h4>課題点</h4>';
                    content += '<ul>';
                    evaluation.feedback
                        .filter(f => !this.isPositiveFeedback(f))
                        .forEach(feedback => {
                            content += `<li class="negative" role="listitem">${feedback}</li>`;
                    });
                    content += '</ul></div>';
                }

                // 改善提案を表示
                if (evaluation.improvement_suggestions && evaluation.improvement_suggestions.length > 0) {
                    content += '<div class="suggestions" role="list" aria-label="改善提案">';
                    content += '<h4>改善提案</h4>';
                    content += '<ul>';
                    evaluation.improvement_suggestions.forEach(suggestion => {
                        content += `<li class="suggestion-item" role="listitem">${suggestion}</li>`;
                    });
                    content += '</ul></div>';
                }

                content += '</div>';
            });

                content += '</div>';
                contentElement.innerHTML = content;

                // アニメーション効果を追加
                contentElement.classList.add('fade-in');
                setTimeout(() => {
                    contentElement.classList.remove('fade-in');
                }, 500);
            }

        // Word文書にコメントを追加
        console.log("\n4. Word文書へのコメント追加を開始");
        try {
            await this.addCommentsToDocument(evaluations);
        } catch (error) {
            console.error("Error adding comments to document:", error);
            this.displayError("評価コメントの追加中にエラーが発生しました");
        }
        console.log("=== 評価プロセス終了 ===");
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
     * 評価結果の表示をリセット
     */
    private resetEvaluations(): void {
        // 評価内容をクリア
        const contentElement = document.getElementById("evaluation-content");
            if (contentElement) {
                contentElement.innerHTML = "";
            }

        // スコアをリセット
        if (this.scoreElement) {
            this.scoreElement.textContent = "-";
        }

        // ステータスをリセット
        if (this.statusElement) {
            this.statusElement.textContent = "";
            this.statusElement.className = "status";
        }
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
     * 評価結果をPriority順にソート
     */
    private sortEvaluationsByPriority(evaluations: EvaluationResult[]): EvaluationResult[] {
        // 全ての評価結果の詳細をログ出力
        console.log("\n=== 全評価結果の詳細 ===");
        
        // Priority 1から14までの評価結果を確実に表示
        for (let priority = 1; priority <= 14; priority++) {
            const evaluationsForPriority = evaluations.filter(e => e.priority === priority);
            console.log(`\nPriority ${priority} の評価結果:`);
            
            if (evaluationsForPriority.length === 0) {
                console.log("- 評価結果: なし");
            } else {
                evaluationsForPriority.forEach((evaluation, index) => {
                    console.log(`\n評価 ${index + 1} の詳細:`);
                    console.log(`- カテゴリ: ${evaluation.category}`);
                    console.log(`- Priority: ${evaluation.priority}`);
                    console.log(`- 適用範囲: ${evaluation.applicable_to}`);
                    console.log(`- スコア: ${evaluation.score}`);
                    console.log(`- 対象文: ${evaluation.target_text || "なし"}`);
                    console.log(`- フィードバック: ${evaluation.feedback.join(", ")}`);
                    console.log(`- 改善提案: ${evaluation.improvement_suggestions || "なし"}`);
                });
            }
        }
        console.log("\n=== 評価結果の詳細表示終了 ===\n");

        return [...evaluations].sort((a, b) => a.priority - b.priority);
    }

    /**
     * 課題のある評価のみをフィルタリング
     */
    private filterNegativeEvaluations(evaluations: EvaluationResult[]): EvaluationResult[] {
        return evaluations.filter(evaluation => {
            // フィードバックが空の場合はスキップ
            if (!evaluation.feedback || evaluation.feedback.length === 0) {
                return false;
            }

            // 「問題なし」のみの場合はスキップ
            if (evaluation.feedback.length === 1 && evaluation.feedback[0] === "問題なし") {
                return false;
            }

            // ポジティブなフィードバックのみの場合はスキップ
            const hasNegativeFeedback = evaluation.feedback.some(feedback => !this.isPositiveFeedback(feedback));
            return hasNegativeFeedback;
        });
    }

    /**
     * 評価結果から最上位Priorityの否定的な評価のみを収集
     */
    private filterHighestPriorityNegativeEvaluations(evaluations: EvaluationResult[]): EvaluationResult[] {
        console.log("\n=== フィルタリングプロセス開始 ===");
        console.log("Priority 1から14の順に評価を確認します");
        
        if (evaluations.length === 0) {
            console.log("評価結果が空のため、フィルタリングをスキップします");
            return [];
        }
        
        // 評価結果を優先度でグループ化
        const evaluationsByPriority: { [key: number]: EvaluationResult[] } = {};
        
        // まず、優先度ごとにグループ化
        evaluations.forEach(evaluation => {
            const priority = evaluation.priority || 999;
            if (!evaluationsByPriority[priority]) {
                evaluationsByPriority[priority] = [];
            }
            evaluationsByPriority[priority].push(evaluation);
        });

        // 優先度順（昇順）にソート（Priority 1から14の順）
        const priorities = Object.keys(evaluationsByPriority)
            .map(Number)
            .sort((a, b) => a - b);

        console.log("\n優先度グループ:");
        priorities.forEach(priority => {
            console.log(`Priority ${priority}: ${evaluationsByPriority[priority].length}件`);
            console.log(`- カテゴリ: ${evaluationsByPriority[priority].map(e => e.category).join(', ')}`);
        });

        // 各優先度レベルで否定的な評価を探す
        for (const priority of priorities) {
            console.log(`\n>>> Priority ${priority} の評価を処理中 <<<`);
            const evaluationsForPriority = evaluationsByPriority[priority];
            
            // この優先度の評価結果をapplicable_toごとにグループ化
            const evaluationsByTarget: { [key: string]: EvaluationResult[] } = {};
            
            evaluationsForPriority.forEach(evaluation => {
                const target = evaluation.applicable_to ? evaluation.applicable_to.join(',') : 'default';
                if (!evaluationsByTarget[target]) {
                    evaluationsByTarget[target] = [];
                }
                evaluationsByTarget[target].push(evaluation);
            });

            // 否定的な評価を収集
            const negativeEvaluations: EvaluationResult[] = [];
            
            // 各適用範囲ごとに評価
            for (const [target, targetEvaluations] of Object.entries(evaluationsByTarget)) {
                console.log(`\n適用範囲 "${target}" の評価を確認中...`);
                
                // この適用範囲で否定的な評価を探す
                const negativeEvaluationsForTarget = targetEvaluations.filter(evaluation => {
                    // フィードバックが空の場合はスキップ
                    if (!evaluation.feedback || evaluation.feedback.length === 0) {
                        return false;
                    }

                    // 「問題なし」のみの場合はスキップ
                    if (evaluation.feedback.length === 1 && evaluation.feedback[0] === "問題なし") {
                        return false;
                    }

                    // ポジティブなフィードバックのみの場合はスキップ
                    const hasNegativeFeedback = evaluation.feedback.some(feedback => !this.isPositiveFeedback(feedback));
                    return hasNegativeFeedback;
                });

                if (negativeEvaluationsForTarget.length > 0) {
                    console.log(`適用範囲 "${target}" で ${negativeEvaluationsForTarget.length} 件の否定的な評価が見つかりました`);
                    // セクション識別子でソートして追加
                    const sortedEvaluations = negativeEvaluationsForTarget.sort((a, b) => {
                        const sectionA = this.extractSectionNumber(a.target_sentence);
                        const sectionB = this.extractSectionNumber(b.target_sentence);
                        return sectionA - sectionB;
                    });
                    negativeEvaluations.push(...sortedEvaluations);
                }
            }

            // この優先度で否定的な評価が見つかった場合、それを返して終了
            if (negativeEvaluations.length > 0) {
                console.log(`\n>>> Priority ${priority} で ${negativeEvaluations.length} 件の否定的な評価が見つかりました <<<`);
                console.log("=== フィルタリングプロセス終了 ===");
                return negativeEvaluations;  // 最上位Priorityの評価のみを返す
            }
            
            console.log(`\n>>> Priority ${priority} では否定的な評価が見つかりませんでした。次のPriorityを確認します <<<`);
        }

        console.log("\nすべてのPriorityで否定的な評価が見つかりませんでした");
        console.log("=== フィルタリングプロセス終了 ===");
        return [];
    }

    /**
     * セクション番号を抽出する
     */
    private extractSectionNumber(targetSentence: string): number {
        if (!targetSentence) return 999;
        
        const match = targetSentence.match(/本文段落(\d+)/);
        if (match) {
            return parseInt(match[1], 10);
        }
        
        // サマリーは最優先
        if (targetSentence.includes("[サマリー]")) {
            return 0;
        }
        
        return 999;  // その他のケース
    }

    /**
     * 評価コメントをWord文書に追加する
     */
    private async addCommentsToDocument(evaluations: EvaluationResult[]): Promise<void> {
        try {
            await Word.run(async (context) => {
                console.log("\n=== Word文書へのコメント追加プロセス開始 ===");
                console.log("1. 文書のパラグラフを取得中...");
                const paragraphs = context.document.body.paragraphs;
                // 必要なプロパティをロード
                paragraphs.load(["text", "firstLineIndent", "leftIndent"]);
                await context.sync();
                console.log(`取得したパラグラフ数: ${paragraphs.items.length}`);

                // パラグラフの内容をログ出力
                console.log("\n=== 文書の構造 ===");
                paragraphs.items.forEach((paragraph, index) => {
                    console.log(`[段落 ${index + 1}]`);
                    console.log(`- テキスト: ${paragraph.text}`);
                    console.log(`- インデント: ${paragraph.firstLineIndent || 0} + ${paragraph.leftIndent || 0}`);
                });
                console.log("==================");

                // 最高優先度の評価のみを取得
                console.log("\n2. 最高優先度の評価を取得");
                const highestPriorityEvaluations = this.filterHighestPriorityNegativeEvaluations(evaluations);
                console.log(`処理対象の評価数: ${highestPriorityEvaluations.length}`);
                
                // 各評価結果に対してコメントを追加
                for (const evaluation of highestPriorityEvaluations) {
                    console.log(`\n3. 評価結果を処理中:`);
                    console.log(`- カテゴリ: ${evaluation.category}`);
                    console.log(`- 適用範囲: ${evaluation.applicable_to?.join(', ')}`);

                    // 「問題なし」の評価はスキップ
                    if (evaluation.feedback.length === 1 && evaluation.feedback[0] === "問題なし") {
                        console.log("「問題なし」の評価をスキップします");
                        continue;
                    }

                    // インデントレベルに基づいて対象段落を取得
                    console.log("\n4. 対象段落を取得中...");
                    const targetParagraphs = await this.getTargetParagraphs(paragraphs, evaluation.applicable_to || []);
                    console.log(`対象段落数: ${targetParagraphs.length}`);
                    
                    // 対象段落が見つからない場合はスキップ
                    if (targetParagraphs.length === 0) {
                        console.log(`警告: 適用範囲 ${evaluation.applicable_to} に該当する段落が見つかりませんでした`);
                        continue;
                    }

                    // 対象の段落を探す
                    const targetText = evaluation.target_sentence.trim();
                    console.log(`\n5. 検索対象テキスト: "${targetText}"`);

                    // 対象段落にコメントを追加
                    let matchFound = false;
                    for (const paragraph of targetParagraphs) {
                        const paragraphText = paragraph.text.trim();
                        console.log(`段落テキスト: "${paragraphText}"`);
                        if (this.isTextMatching(paragraphText, targetText)) {
                            console.log("テキストマッチが見つかりました");
                            await this.addCommentToParagraph(context, paragraph, evaluation);
                            matchFound = true;
                        }
                    }

                    if (!matchFound) {
                        console.log(`警告: 対象の段落が見つかりませんでした: ${targetText}`);
                    }
                }

                await context.sync();
                console.log("\nすべてのコメントを追加しました");
                console.log("=== Word文書へのコメント追加プロセス終了 ===");
            });
        } catch (error) {
            console.error("コメント追加処理でエラーが発生:", error);
            throw error;
        }
    }

    /**
     * 適用範囲に基づいて対象段落を取得
     */
    private async getTargetParagraphs(paragraphs: Word.ParagraphCollection, applicableTo: string[]): Promise<Word.Paragraph[]> {
        const result: Word.Paragraph[] = [];
        
        // 適用範囲が指定されていない場合は全段落を対象とする
        if (!applicableTo || applicableTo.length === 0) {
            console.log("適用範囲が指定されていないため、全段落を対象とします");
            return paragraphs.items;
        }

        console.log(`適用範囲: ${applicableTo.join(", ")}`);

        // インデントレベルに基づいて段落をフィルタリング
        for (let i = 0; i < paragraphs.items.length; i++) {
            const paragraph = paragraphs.items[i];
            const firstLineIndent = paragraph.firstLineIndent || 0;
            const leftIndent = paragraph.leftIndent || 0;
            const totalIndent = leftIndent + firstLineIndent;
            
            // インデントレベルを判定（0=タイトル, 1=サマリー, 2=ストーリー, 3=詳細）
            const indentLevel = Math.round(totalIndent / 7);  // 7は1レベルあたりのインデント量

            console.log(`段落 ${i + 1}: インデントレベル = ${indentLevel}, テキスト = "${paragraph.text.trim()}"`);

            // 適用範囲に基づいて段落を選択
            if (applicableTo.includes("FULL_DOCUMENT")) {
                // タイトル部分のみを対象とする
                if (indentLevel === 0 && i === 0) {  // 最初の段落（タイトル）のみ
                    result.push(paragraph);
                    console.log(`FULL_DOCUMENT: タイトル段落を追加`);
                }
            } else if (applicableTo.includes("SUMMARY_ONLY") && indentLevel === 1) {
                // サマリー部分のみを対象とする
                result.push(paragraph);
                console.log("SUMMARY_ONLY: サマリー段落を追加");
            } else if (applicableTo.includes("SUMMARY_AND_STORY")) {
                // サマリーとストーリー部分を対象とする
                if (indentLevel === 1 || indentLevel === 2) {
                    result.push(paragraph);
                    console.log("SUMMARY_AND_STORY: サマリーまたはストーリー段落を追加");
                }
            } else if (applicableTo.includes("STORY_AND_BODY")) {
                // ストーリーと本文部分を対象とする
                if (indentLevel >= 2) {
                    result.push(paragraph);
                    console.log("STORY_AND_BODY: ストーリーまたは本文段落を追加");
                }
            }
        }

        console.log(`選択された段落数: ${result.length}`);
        return result;
    }

    /**
     * 段落にコメントを追加
     */
    private async addCommentToParagraph(context: Word.RequestContext, paragraph: Word.Paragraph, evaluation: EvaluationResult): Promise<void> {
        try {
            // フィードバックとimprovement_suggestionsを結合してコメントを作成
            const feedbackItems = evaluation.feedback.filter(item => item !== "問題なし");
            const improvementItems = evaluation.improvement_suggestions || [];
            const commentParts = [];
            
            if (feedbackItems.length > 0) {
                // カテゴリ名を追加
                commentParts.push(`【${evaluation.criteriaId}】`);
                commentParts.push("【フィードバック】\n" + feedbackItems.join("\n"));
            }
            if (improvementItems.length > 0) {
                commentParts.push("【改善提案】\n" + improvementItems.join("\n"));
            }
            
            if (commentParts.length > 0) {
                const comment = commentParts.join("\n\n");
                console.log(`コメントを追加: ${comment}`);
                console.log(`対象の段落: ${paragraph.text}`);
                
                // locationがカテゴリIDの場合は、最初の段落にコメントを追加
                if (evaluation.location === evaluation.categoryId) {
                    const range = paragraph.getRange();
                    range.insertComment(comment);
                    await context.sync();
                    console.log("コメントが正常に追加されました");
                    return;
                }
                
                // 通常のケース：段落の範囲を取得してコメントを追加
                const range = paragraph.getRange();
                range.insertComment(comment);
                await context.sync();
                console.log("コメントが正常に追加されました");
            }
        } catch (error) {
            console.error("コメント追加中にエラーが発生:", error);
            throw error;
        }
    }

    /**
     * フィードバックがポジティブなものかどうかを判定
     */
    private isPositiveFeedback(feedback: string): boolean {
        const positiveKeywords = [
            "問題なし",
            "良好",
            "適切",
            "明確",
            "統一されて",
            "問題ありません",
            "十分",
            "概ね明確",
            "特に問題は見られません",
            "適切に記載されて",
            "正しく記載されて",
            "十分な情報が含まれて"
        ];

        return positiveKeywords.some(keyword => feedback.includes(keyword));
    }

    /**
     * テキストが一致するかどうかを判定
     */
    private isTextMatching(paragraphText: string, targetText: string): boolean {
        // 空白、改行を正規化して比較
        const normalizedParagraph = paragraphText.replace(/\s+/g, ' ').trim();
        const normalizedTarget = targetText.replace(/\s+/g, ' ').trim();
        
        // 完全一致を試みる
        if (normalizedParagraph === normalizedTarget) {
            console.log("完全一致しました");
            return true;
        }
        
        // 部分一致を試みる（targetTextが段落テキストに含まれているか）
        if (normalizedParagraph.includes(normalizedTarget)) {
            console.log("部分一致しました");
            return true;
        }
        
        // どちらも一致しない場合
        console.log("テキストが一致しませんでした");
        console.log(`段落: "${normalizedParagraph}"`);
        console.log(`対象: "${normalizedTarget}"`);
        return false;
    }

    /**
     * 評価結果から表示すべき評価を抽出する
     */
    private filterEvaluationsForDisplay(evaluations: EvaluationResult[]): EvaluationResult[] {
        if (!evaluations || evaluations.length === 0) {
            return [];
        }

        // 評価結果を優先度でグループ化
        const evaluationsByPriority = new Map<number, EvaluationResult[]>();
        evaluations.forEach(evaluation => {
            const priority = evaluation.priority || 999;
            if (!evaluationsByPriority.has(priority)) {
                evaluationsByPriority.set(priority, []);
            }
            evaluationsByPriority.get(priority)?.push(evaluation);
        });

        // 優先度順（昇順）にソート
        const sortedPriorities = Array.from(evaluationsByPriority.keys()).sort((a, b) => a - b);

        // 最も優先度の高いグループから、コメントのある評価を探す
        for (const priority of sortedPriorities) {
            const priorityEvaluations = evaluationsByPriority.get(priority) || [];
            const validEvaluations = priorityEvaluations.filter(e => this.hasValidFeedback(e));
            
            if (validEvaluations.length > 0) {
                console.log(`Priority ${priority} のグループからコメントを表示します`);
                return validEvaluations;
            }
            console.log(`Priority ${priority} のグループにはコメントがありませんでした`);
        }

        return [];
    }

    /**
     * 評価結果が有効なフィードバックを持っているかチェック
     */
    private hasValidFeedback(evaluation: EvaluationResult): boolean {
        // "問題なし"以外のフィードバックがあるかチェック
        const hasFeedback = evaluation.feedback.some(feedback => feedback !== "問題なし");
        
        // 改善提案があるかチェック
        const hasImprovements = evaluation.improvement_suggestions && 
                               evaluation.improvement_suggestions.length > 0;
        
        return hasFeedback || hasImprovements;
    }
} 