/*
 * Copyright (c) Microsoft Corporation. All rights reserved. Licensed under the MIT license.
 * See LICENSE in the project root for license information.
 */

/* global console, document, Office */

import { UIManager } from "./uiManager";

// UIManagerのシングルトンインスタンス
let uiManager: UIManager | null = null;

Office.onReady((info) => {
    if (info.host === Office.HostType.Word) {
        // UIManagerのインスタンスを作成
        uiManager = new UIManager();

        // 実行ボタンのイベントハンドラを設定
        const checkButton = document.getElementById("check-button");
        if (checkButton) {
            checkButton.onclick = handleCheckButtonClick;
        }
        
        // グローバルエラーハンドリング
        window.onerror = (message, source, lineno, colno, error) => {
            console.error("Global error:", { message, source, lineno, colno, error });
            if (uiManager) {
                uiManager.showError("予期せぬエラーが発生しました");
            }
            return false;
        };

        window.onunhandledrejection = (event) => {
            console.error("Unhandled promise rejection:", event.reason);
            if (uiManager) {
                uiManager.showError("非同期処理でエラーが発生しました");
            }
        };
    }
});

/**
 * 実行ボタンのクリックハンドラ
 */
async function handleCheckButtonClick(): Promise<void> {
    if (!uiManager) {
        console.error("UIManagerが初期化されていません");
        return;
    }

    try {
        await uiManager.handleCheckDocument();
    } catch (error) {
        console.error("文書解析中にエラーが発生:", error);
        uiManager.showError(error instanceof Error ? error.message : "予期せぬエラーが発生しました");
    }
}

/**
 * 処理中の表示を行う
 */
function showProgress(message: string): void {
    const progressArea = document.getElementById("progress-area");
    if (progressArea) {
        progressArea.innerHTML = `<p>${message}</p>`;
        progressArea.style.display = "block";
    }
}

/**
 * 処理中の表示を隠す
 */
function hideProgress(): void {
    const progressArea = document.getElementById("progress-area");
    if (progressArea) {
        progressArea.style.display = "none";
    }
}
