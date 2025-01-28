/*
 * Copyright (c) Microsoft Corporation. All rights reserved. Licensed under the MIT license.
 * See LICENSE in the project root for license information.
 */

/* global console, document, Office */

import { getDocumentStructure, getBulletPoints } from "./documentUtil";
import { UIManager } from "./ui";
import { runIntegrationTests } from "./test";

let isOfficeInitialized = false;
let uiManager: UIManager;

// アドインの初期化処理
function initializeUI() {
    const sideloadMsg = document.getElementById("sideload-msg");
    const appBody = document.getElementById("app-body");
    const checkBtn = document.getElementById("check-button");
    const testBtn = document.getElementById("test-button");

    if (sideloadMsg) {
        sideloadMsg.style.display = "none";
    }
    if (appBody) {
        appBody.style.display = "flex";
    }
    if (checkBtn) {
        checkBtn.addEventListener("click", analyzeDocument);
    }
    if (testBtn) {
        testBtn.addEventListener("click", runTests);
    }

    // UIManagerのインスタンスを作成
    uiManager = new UIManager();
}

// Office初期化時の処理
Office.onReady((info) => {
    if (info.host === Office.HostType.Word) {
        isOfficeInitialized = true;
        initializeUI();
        console.log("WordApi 1.3がサポートされています");
    }
});

// 従来のOffice初期化ハンドラ（後方互換性のため残す）
Office.initialize = () => {
    isOfficeInitialized = true;
    initializeUI();
};

/**
 * テストを実行する
 */
async function runTests(): Promise<void> {
    try {
        if (!isOfficeInitialized) {
            throw new Error("Office.jsが初期化されていません");
        }
        await runIntegrationTests();
    } catch (error) {
        console.error("テスト実行中にエラーが発生:", error);
        uiManager.displayError(error instanceof Error ? error.message : "不明なエラーが発生しました");
    }
}

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
function showProgress(message) {
    const progressArea = document.getElementById("progress-area");
    if (progressArea) {
        progressArea.innerHTML = `<p>${message}</p>`;
        progressArea.style.display = "block";
    }
}

/**
 * 処理中の表示を隠す
 */
function hideProgress() {
    const progressArea = document.getElementById("progress-area");
    if (progressArea) {
        progressArea.style.display = "none";
    }
}

/**
 * エラーメッセージを表示する
 */
function showError(message) {
    const errorArea = document.getElementById("error-area");
    if (errorArea) {
        errorArea.innerHTML = `<p class="error">${message}</p>`;
        errorArea.style.display = "block";
    }
}

// ドキュメントのチェック処理
async function checkDocument() {
    if (!isOfficeInitialized) {
        return;
    }

    try {
        await uiManager.handleCheckDocument();
    } catch (error) {
        console.error("Error in checkDocument:", error);
    }
}

if (Office.context.requirements.isSetSupported("WordApi", "1.3")) {
    console.log("WordApi 1.3がサポートされています");
} else {
    console.log("WordApi 1.3はサポートされていません");
}
