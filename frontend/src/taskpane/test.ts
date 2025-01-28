import { getDocumentStructure } from "./documentUtil";
import { UIManager } from "./ui";
import { checkApiHealth, reviewDocument, evaluateWithOpenAI } from "./api";
import { EvaluationResult } from "./types";

/**
 * コメント機能のテストケース
 */
async function testCommentFeature(): Promise<void> {
    try {
        await Word.run(async (context) => {
            // テスト用の文書をクリア
            context.document.body.clear();
            await context.sync();

            // テスト用の文書構造を作成
            const body = context.document.body;
            
            // ヘッダーを追加（タイトル用）
            const firstSection = context.document.sections.getFirst();
            const header = firstSection.getHeader("Primary");
            header.insertText("新規ECサイト開発プロジェクト 基本計画書", "Replace");
            
            // 本文を追加
            const paragraphs = [
                "【サマリー】\n当社の新規ECサイト開発プロジェクトを開始する。新システムの導入により、オンライン販売の強化とカスタマーエクスペリエンスの向上を目指す。\n\n",
                "【ストーリー1】\n現在の課題として、既存ECサイトの機能が限定的であり、顧客ニーズに十分対応できていない。しかし、具体的にどの機能が不足しているかの分析が必要である。\n\n",
                "【詳細1】\nモバイル対応の遅れや決済手段の制限により、競合他社と比較して機会損失が発生している。また、在庫管理システムとの連携が不十分で、注文処理に時間がかかっている。\n\n",
                "【ストーリー2】\n新システムでは、最新のクラウド技術を活用し、スケーラブルな構成を実現する。ただし、移行計画の詳細は検討中である。\n\n",
                "【詳細2】\nAWSのマイクロサービスアーキテクチャを採用し、将来の拡張性を確保する。また、セキュリティ面では、最新の暗号化技術と認証システムを実装する。\n\n"
            ];

            // 段落を追加
            for (const text of paragraphs) {
                body.insertParagraph(text, "End");
            }
            
            await context.sync();

            // 文書構造を取得
            const structure = await getDocumentStructure();
            if (!structure) {
                throw new Error("文書構造の取得に失敗しました");
            }

            // 文書評価を実行
            const result = await reviewDocument(structure);
            if (!result || !result.evaluations) {
                throw new Error("評価結果の取得に失敗しました");
            }

            // UIManagerのインスタンスを作成してコメントを追加
            const ui = new UIManager();
            await ui.displayEvaluations(result.evaluations);

            // 文書の内容を確認
            const content = context.document.body;
            content.load("text");
            await context.sync();

            console.log(`=== コメント機能テスト結果 ===`);
            console.log(`文書の内容:`);
            console.log(content.text);

            return true;
        });
    } catch (error) {
        console.error("コメント機能テストでエラーが発生:", error);
        throw error;
    }
}

/**
 * Office.jsとの統合テスト
 */
export async function runIntegrationTests(): Promise<void> {
    const ui = new UIManager();
    const results: { name: string; status: "成功" | "失敗"; error?: string }[] = [];

    try {
        // 1. Office.jsの初期化テスト
        try {
            await Office.onReady();
            results.push({ name: "Office.js初期化", status: "成功" });
        } catch (error) {
            results.push({ 
                name: "Office.js初期化", 
                status: "失敗",
                error: error instanceof Error ? error.message : "不明なエラー"
            });
        }

        // 2. 文書アクセステスト
        try {
            await Word.run(async context => {
                const body = context.document.body;
                body.load("text");
                await context.sync();
                results.push({ name: "文書アクセス", status: "成功" });
            });
        } catch (error) {
            results.push({ 
                name: "文書アクセス", 
                status: "失敗",
                error: error instanceof Error ? error.message : "不明なエラー"
            });
        }

        // 3. 文書構造取得テスト
        try {
            const structure = await getDocumentStructure();
            if (structure && structure.title !== undefined && Array.isArray(structure.contents)) {
                results.push({ name: "文書構造取得", status: "成功" });
            } else {
                throw new Error("文書構造が不正です");
            }
        } catch (error) {
            results.push({ 
                name: "文書構造取得", 
                status: "失敗",
                error: error instanceof Error ? error.message : "不明なエラー"
            });
        }

        // 4. APIヘルスチェックテスト
        try {
            const isHealthy = await checkApiHealth();
            if (isHealthy) {
                results.push({ name: "APIヘルスチェック", status: "成功" });
            } else {
                throw new Error("APIが正常に応答しません");
            }
        } catch (error) {
            results.push({ 
                name: "APIヘルスチェック", 
                status: "失敗",
                error: error instanceof Error ? error.message : "不明なエラー"
            });
        }

        // 5. 文書評価テスト
        try {
            const structure = await getDocumentStructure();
            if (!structure || structure.title === undefined || !Array.isArray(structure.contents)) {
                throw new Error("文書構造の取得に失敗しました");
            }
            const result = await reviewDocument(structure);
            if (result && result.evaluations) {
                results.push({ name: "文書評価", status: "成功" });
            } else {
                throw new Error("評価結果が不正です");
            }
        } catch (error) {
            results.push({ 
                name: "文書評価", 
                status: "失敗",
                error: error instanceof Error ? error.message : "不明なエラー"
            });
        }

        // コメント機能テスト
        try {
            await testCommentFeature();
            results.push({ name: "コメント機能", status: "成功" });
        } catch (error) {
            results.push({ 
                name: "コメント機能", 
                status: "失敗",
                error: error instanceof Error ? error.message : "不明なエラー"
            });
        }

        // テスト結果を表示
        displayTestResults(results);

    } catch (error) {
        console.error("テスト実行中にエラーが発生:", error);
        throw error;
    }
}

/**
 * テスト結果を表示する
 */
function displayTestResults(results: { name: string; status: "成功" | "失敗"; error?: string }[]): void {
    const statusElement = document.getElementById("status");
    if (!statusElement) return;

    const totalTests = results.length;
    const passedTests = results.filter(r => r.status === "成功").length;

    let message = `テスト結果: ${passedTests}/${totalTests} 成功\n\n`;
    results.forEach(result => {
        message += `${result.name}: ${result.status}`;
        if (result.error) {
            message += ` (${result.error})`;
        }
        message += "\n";
    });

    statusElement.textContent = message;
    statusElement.className = passedTests === totalTests ? "status success" : "status error";
} 