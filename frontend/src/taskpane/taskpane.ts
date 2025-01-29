/*
 * Copyright (c) Microsoft Corporation. All rights reserved. Licensed under the MIT license.
 * See LICENSE in the project root for license information.
 */

/* global console, document, Office */

import { UIManager } from "./ui";

let isOfficeInitialized = false;
const uiManager = new UIManager();

Office.onReady(info => {
    if (info.host === Office.HostType.Word) {
        isOfficeInitialized = true;
        document.getElementById("check-button").onclick = analyzeDocument;
    }
});

// 従来のOffice初期化ハンドラ（後方互換性のため残す）
Office.initialize = () => {
    isOfficeInitialized = true;
};

/**
 * 文書を解析して結果を表示する
 */
async function analyzeDocument(): Promise<void> {
    try {
        if (!isOfficeInitialized) {
            throw new Error("Office.jsが初期化されていません");
        }

        await uiManager.handleCheckDocument();
    } catch (error) {
        console.error("文書解析中にエラーが発生:", error);
        uiManager.displayError(error instanceof Error ? error.message : "不明なエラーが発生しました");
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
