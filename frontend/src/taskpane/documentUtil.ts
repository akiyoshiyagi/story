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
            paragraphs.load(["items", "text", "listItem", "listItem/level"]);
            await context.sync();

            // デバッグ情報の出力
            console.log('=== 文書構造解析開始 ===');
            console.log(`総段落数: ${paragraphs.items.length}`);

            // 結果を格納する配列
            const contents: StoryStructure[] = [];
            let currentStructure: StoryStructure | null = null;
            let currentStory: { story: string; bodies: string[] } | null = null;

            // 各パラグラフを処理
            const structuredContents: {
                level: number;
                text: string;
                listLevel: number;
            }[] = [];

            // パラグラフのレベルを判定
            for (const paragraph of paragraphs.items) {
                const text = paragraph.text.trim();
                if (!text) continue;

                // リストレベルを取得（箇条書きレベル）
                let listLevel = 0;
                try {
                    if (paragraph.listItem) {
                        listLevel = paragraph.listItem.level + 1;
                        console.log('リストレベルを検出:', {
                            text: text.substring(0, 50),
                            level: listLevel
                        });
                    }
                } catch (error) {
                    console.warn('リストレベルの取得に失敗:', {
                        text: text.substring(0, 50),
                        error: error instanceof Error ? error.message : String(error)
                    });
                }

                // 箇条書きレベルに基づいてドキュメントレベルを設定
                let level: number;
                if (listLevel === 1) {
                    level = 1; // サマリー
                } else if (listLevel === 2) {
                    level = 2; // ストーリー
                } else if (listLevel === 3) {
                    level = 3; // 本文
                } else {
                    // リストレベルが0または不明な場合
                    if (structuredContents.length === 0) {
                        level = 1; // 最初の段落はサマリーとして扱う
                        console.log('最初の段落をサマリーとして設定:', text.substring(0, 50));
                    } else if (!currentStructure) {
                        level = 1; // サマリーがない場合は新しいサマリーとして扱う
                        console.log('サマリーが未設定のため、新しいサマリーとして設定:', text.substring(0, 50));
                    } else if (!currentStory) {
                        level = 2; // ストーリーがない場合は新しいストーリーとして扱う
                        console.log('ストーリーが未設定のため、新しいストーリーとして設定:', text.substring(0, 50));
                    } else {
                        level = 3; // それ以外は本文として扱う
                        console.log('本文として設定:', text.substring(0, 50));
                    }
                }

                console.log('段落解析:', {
                    text: text.substring(0, 50) + (text.length > 50 ? '...' : ''),
                    listLevel,
                    level: `${level} (${getLevelName(level)})`,
                    isFirstParagraph: structuredContents.length === 0
                });

                structuredContents.push({
                    level,
                    text,
                    listLevel
                });

                // 文書構造を更新
                if (level === 1) {
                    // サマリーの場合：新しい構造を開始
                    if (currentStructure) {
                        console.log('既存の構造を保存:', {
                            summary: currentStructure.summary.substring(0, 50),
                            storiesCount: currentStructure.stories.length
                        });
                        contents.push(currentStructure);
                    }
                    currentStructure = {
                        summary: text,
                        stories: []
                    };
                    currentStory = null;
                    console.log('新しいサマリーを作成:', text.substring(0, 50));

                } else if (level === 2) {
                    // ストーリーの場合：現在のサマリーに紐づけて新しいストーリーを開始
                    if (!currentStructure) {
                        console.log('サマリーが未設定のためストーリー用の構造を作成');
                        currentStructure = {
                            summary: "要約なし",
                            stories: []
                        };
                    }
                    currentStory = {
                        story: paragraph.text,
                        bodies: []
                    };
                    currentStructure.stories.push(currentStory);
                    console.log('ストーリーを追加:', paragraph.text.substring(0, 50));

                } else if (level === 3) {
                    // 本文の場合：現在のストーリーに紐づけて本文を追加
                    if (!currentStructure) {
                        console.log('サマリーが未設定のため本文用の構造を作成');
                        currentStructure = {
                            summary: "要約なし",
                            stories: []
                        };
                    }
                    if (!currentStory) {
                        console.log('ストーリーが未設定のため新しいストーリーを作成');
                        currentStory = {
                            story: "内容なし",
                            bodies: []
                        };
                        currentStructure.stories.push(currentStory);
                    }
                    currentStory.bodies.push(paragraph.text);
                    console.log('本文を追加:', paragraph.text.substring(0, 50));
                }
            }

            // 最終結果のサマリーを出力
            console.log('\n=== 文書構造の解析結果 ===');
            const levelCounts = structuredContents.reduce((acc, curr) => {
                acc[curr.level] = (acc[curr.level] || 0) + 1;
                return acc;
            }, {} as Record<number, number>);

            console.log('段落の分類結果:', {
                'サマリー (Level 1)': levelCounts[1] || 0,
                'ストーリー (Level 2)': levelCounts[2] || 0,
                '本文 (Level 3)': levelCounts[3] || 0,
                '詳細 (Level 4)': levelCounts[4] || 0
            });

            // 最後の構造を追加
            if (currentStructure) {
                console.log('最後の構造を保存:', {
                    summary: currentStructure.summary.substring(0, 50),
                    storiesCount: currentStructure.stories.length
                });
                contents.push(currentStructure);
            }

            console.log('作成された構造:', contents.map(content => ({
                summary: content.summary.substring(0, 50),
                storiesCount: content.stories.length,
                totalBodies: content.stories.reduce((sum, story) => sum + story.bodies.length, 0)
            })));

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
 * レベル名を取得
 */
function getLevelName(level: number): string {
    switch (level) {
        case 1: return 'サマリー';
        case 2: return 'ストーリー';
        case 3: return '本文';
        case 4: return '詳細';
        default: return '不明';
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