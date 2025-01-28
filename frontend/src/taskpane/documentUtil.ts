/**
 * Word文書操作用のユーティリティ関数
 */

/* global Office, Word */

import { DocumentStructure, StoryStructure } from './types';

/**
 * 文書構造を解析して階層ごとにグループ化する
 */
export async function getDocumentStructure(): Promise<DocumentStructure> {
    try {
        return await Word.run(async (context) => {
            // タイトルをヘッダーから取得
            const sections = context.document.sections;
            sections.load("items");
            await context.sync();
            
            let title = "タイトルなし";
            if (sections.items.length > 0) {
                const firstSection = sections.items[0];
                const header = firstSection.getHeader("Primary");
                header.load("text");
                await context.sync();
                
                const headerText = header.text.trim();
                if (headerText) {
                    title = headerText;
                }
            }

            // 文書全体のパラグラフを取得
            const paragraphs = context.document.body.paragraphs;
            paragraphs.load("items");
            await context.sync();

            // 各パラグラフのテキストを読み込む
            const paragraphItems = paragraphs.items;
            for (const paragraph of paragraphItems) {
                paragraph.load(["text", "firstLineIndent", "leftIndent"]);
            }
            await context.sync();

            // 現在処理中の各レベルの内容を保持
            let currentSummary = '';
            let currentStoryGroup: Array<{
                story: string;
                bodies: string[];
            }> = [];
            let currentStory = '';
            let currentBodies: string[] = [];

            // 結果を格納する配列
            const contents: StoryStructure[] = [];

            // 文書が空の場合のデフォルト値を設定
            if (paragraphItems.length === 0) {
                return {
                    title,
                    contents: [{
                        summary: "空の文書",
                        stories: [{
                            story: "内容なし",
                            bodies: ["テキストを入力してください"]
                        }]
                    }]
                };
            }

            // 各パラグラフを処理
            for (const paragraph of paragraphItems) {
                const text = paragraph.text;
                const trimmedText = text.trim();
                
                // 空のパラグラフはスキップ
                if (!trimmedText) continue;

                // インデントレベルを計算
                const firstLineIndent = paragraph.firstLineIndent || 0;
                const leftIndent = paragraph.leftIndent || 0;
                const totalIndent = leftIndent + firstLineIndent;
                const indentLevel = getIndentLevel(totalIndent);

                // デバッグ情報を出力
                console.log(`=== パラグラフ解析 ===`);
                console.log(`テキスト: ${trimmedText}`);
                console.log(`インデント情報:`, {
                    firstLineIndent,
                    leftIndent,
                    totalIndent,
                    indentLevel
                });

                // インデントレベルが0（対象外）の場合はスキップ
                if (indentLevel === 0) {
                    console.log('インデントレベルが0のためスキップ');
                    continue;
                }

                // レベルに応じて処理
                if (indentLevel === 1) {
                    console.log('サマリーとして処理:', trimmedText);
                    // 前のグループを保存
                    if (currentSummary) {
                        // 前のストーリーグループを保存
                        if (currentStory) {
                            currentStoryGroup.push({
                                story: currentStory,
                                bodies: [...currentBodies]
                            });
                        }

                        if (currentStoryGroup.length === 0) {
                            currentStoryGroup.push({
                                story: "内容なし",
                                bodies: ["テキストを入力してください"]
                            });
                        }

                        contents.push({
                            summary: currentSummary,
                            stories: [...currentStoryGroup]
                        });
                    }

                    // 新しいグループを開始
                    currentSummary = trimmedText;
                    currentStoryGroup = [];
                    currentStory = '';
                    currentBodies = [];
                }
                else if (indentLevel === 2) {
                    console.log('ストーリーとして処理:', trimmedText);
                    // 前のストーリーグループを保存
                    if (currentStory) {
                        currentStoryGroup.push({
                            story: currentStory,
                            bodies: [...currentBodies]
                        });
                    }

                    // 新しいストーリーを開始
                    currentStory = trimmedText;
                    currentBodies = [];
                }
                else if (indentLevel === 3) {
                    console.log('詳細として処理:', trimmedText);
                    currentBodies.push(trimmedText);
                }
            }

            // 最後のグループを処理
            if (currentSummary) {
                // 最後のストーリーグループを保存
                if (currentStory) {
                    currentStoryGroup.push({
                        story: currentStory,
                        bodies: [...currentBodies]
                    });
                }

                if (currentStoryGroup.length === 0) {
                    currentStoryGroup.push({
                        story: "内容なし",
                        bodies: ["テキストを入力してください"]
                    });
                }

                contents.push({
                    summary: currentSummary,
                    stories: [...currentStoryGroup]
                });
            }

            // 結果が空の場合のデフォルト値を設定
            if (contents.length === 0) {
                contents.push({
                    summary: "要約なし",
                    stories: [{
                        story: "内容なし",
                        bodies: ["テキストを入力してください"]
                    }]
                });
            }

            // デバッグ用のログ出力
            console.log('\n=== 解析結果 ===');
            console.log(`タイトル: ${title}`);
            contents.forEach((group, index) => {
                console.log(`[${group.summary}, [${
                    group.stories.map(story => 
                        `[${story.story}, [${story.bodies.join(', ')}]]`
                    ).join(', ')
                }]]`);
            });

            return {
                title,
                contents
            };
        });
    } catch (error) {
        console.error('Error in getDocumentStructure:', error);
        throw error;
    }
}

/**
 * 箇条書きの段落を取得する
 * @returns 箇条書きの段落のテキスト配列
 */
export async function getBulletPoints(): Promise<string[]> {
    try {
        return await Word.run(async (context) => {
            const body = context.document.body;
            const paragraphs = body.paragraphs;
            paragraphs.load("items");
            await context.sync();

            const bulletPoints: string[] = [];
            
            // 各パラグラフのテキストを読み込む
            const paragraphItems = paragraphs.items;
            for (let i = 0; i < paragraphItems.length; i++) {
                const paragraph = paragraphItems[i];
                paragraph.load(["text", "firstLineIndent", "leftIndent"]);
            }
            await context.sync();

            // 各段落を処理
            for (let i = 0; i < paragraphItems.length; i++) {
                const paragraph = paragraphItems[i];
                const text = paragraph.text.trim();
                // 箇条書きの記号で始まるテキストを検出
                if (text.match(/^[・※\-\*•]/) || text.match(/^\d+[\.\)]/) || text.startsWith("• ")) {
                    bulletPoints.push(text);
                }
            }

            return bulletPoints;
        });
    } catch (error) {
        console.error("Error fetching bullet points:", error);
        throw error;
    }
}

/**
 * 文書全体のテキストを取得する
 * @returns 文書全体のテキスト
 */
export async function getFullText(): Promise<string> {
    try {
        return await Word.run(async (context) => {
            const body = context.document.body;
            body.load("text");
            await context.sync();
            return body.text.trim();
        });
    } catch (error) {
        console.error("Error in getFullText:", error);
        throw error;
    }
}

/**
 * インデントレベルを判定する
 * @param indent インデント値（ポイント単位）
 * @returns インデントレベル（1-3）、対象外の場合は0
 */
function getIndentLevel(indent: number): number {
    // 実際の値に基づいてレベルを判定
    if (indent <= 0) return 1;    // グループ1: totalIndent = 0
    if (indent <= 30) return 2;   // グループ2: totalIndent ≈ 21
    if (indent <= 50) return 3;   // グループ3: totalIndent ≈ 42
    return 0;                     // 対象外
}

/**
 * Summaryの見出しかどうかを判定
 */
function isSummaryHeading(text: string): boolean {
    const keywords = ['summary', '要約', 'サマリー'];
    return keywords.some(keyword => 
        text.toLowerCase().includes(keyword.toLowerCase())
    );
}

/**
 * Storyの見出しかどうかを判定
 */
function isStoryHeading(text: string): boolean {
    const keywords = ['story', 'ストーリー', '物語'];
    return keywords.some(keyword => 
        text.toLowerCase().includes(keyword.toLowerCase())
    );
}