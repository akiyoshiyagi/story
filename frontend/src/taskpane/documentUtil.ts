/**
 * Word文書操作用のユーティリティ関数
 */

/* global Office, Word */

import { DocumentStructure, StoryStructure } from './types';

// Word.Commentの型定義を更新
interface Comment {
    delete(): void;
}

// Word.CommentCollectionの型定義を更新
interface CommentCollection {
    items: Comment[];
    getAll(): CommentCollection;
    load(option: string): void;
}

// Word.Documentの拡張型定義を更新
interface ExtendedDocument extends Word.Document {
    comments: CommentCollection;
}

interface Evaluation {
    categoryId: string;    // カテゴリID
    criteriaId: string;    // 評価基準ID
    score: number;
    feedback: string;
    location?: string;
}

// カテゴリと評価基準のマッピング
export const CATEGORY_CRITERIA_MAP: { [key: string]: string[] } = {
    "FULL_TEXT_RHETORIC": ["最低限の修辞表現", "修辞表現"],
    "SUMMARY_LOGIC_FLOW": ["前回の振り返りの有無", "SCQA有無", "転換の接続詞の重複利用"],
    "SUMMARY_INTERNAL_LOGIC": ["接続詞の妥当性", "サマリーレイヤーに不適な接続詞の有無", "直前のサマリーとの論理的連続性"],
    "SUMMARY_STORY_LOGIC": ["メッセージレイヤーの逐次的展開性", "逐次的展開の評価", "根拠s, 詳細s⇔主張"],
    "STORY_INTERNAL_LOGIC": ["接続詞の適切性", "転換の接続詞の二重利用", "無駄なナンバリングの回避"],
    "DETAIL_RHETORIC": ["メッセージとボディの論理的整合性"]
};

// カテゴリの日本語名マッピング
export const CATEGORY_DISPLAY_NAMES: { [key: string]: string } = {
    "FULL_TEXT_RHETORIC": "全文修辞表現",
    "SUMMARY_LOGIC_FLOW": "サマリーの論理展開",
    "SUMMARY_INTERNAL_LOGIC": "サマリー単体の論理",
    "SUMMARY_STORY_LOGIC": "サマリーとストーリー間の論理",
    "STORY_INTERNAL_LOGIC": "ストーリー単体の論理",
    "DETAIL_RHETORIC": "細部の修辞表現"
};

// 現在選択されているカテゴリを保持する変数
let selectedCategories: Set<string> = new Set();

/**
 * カテゴリの選択状態を切り替える
 * @param categoryId カテゴリID
 * @returns 更新後の選択状態（true: 選択中, false: 非選択）
 */
export function toggleCategory(categoryId: string): boolean {
    if (selectedCategories.has(categoryId)) {
        selectedCategories.delete(categoryId);
        return false;
    } else {
        selectedCategories.add(categoryId);
        return true;
    }
}

/**
 * 現在選択されているカテゴリを取得する
 * @returns 選択中のカテゴリIDの配列
 */
export function getSelectedCategories(): string[] {
    return Array.from(selectedCategories);
}

/**
 * すべてのカテゴリを選択する
 */
export function selectAllCategories(): void {
    selectedCategories = new Set(Object.keys(CATEGORY_CRITERIA_MAP));
}

/**
 * すべてのカテゴリの選択を解除する
 */
export function clearSelectedCategories(): void {
    selectedCategories.clear();
}

/**
 * コメントのテキストを生成する
 */
function generateCommentText(evaluation: Evaluation): string {
    try {
        // フィードバックを問題点と改善提案に分割
        const feedbackParts = evaluation.feedback.split('【改善提案】');
        const problems = feedbackParts[0].split('\n')
            .filter(line => line.trim())
            .map(line => {
                // ナンバリングを含む識別子を基本形に変換
                return line
                    .replace(/【サマリー\d+】/g, "【サマリー】")
                    .replace(/【ストーリー\d+-\d+】/g, "【ストーリー】")
                    .replace(/【本文\d+】/g, "【ボディ】");
            });

        const suggestions = feedbackParts.length > 1 
            ? feedbackParts[1].split('\n')
                .filter(line => line.trim())
                .map(line => {
                    // ナンバリングを含む識別子を基本形に変換
                    return line
                        .replace(/【サマリー\d+】/g, "【サマリー】")
                        .replace(/【ストーリー\d+-\d+】/g, "【ストーリー】")
                        .replace(/【本文\d+】/g, "【ボディ】");
                })
            : [];

        // コメントテキストの構築
        const commentParts = [
            `【評価観点】${evaluation.criteriaId}`,
        ];

        // 問題点の追加（エラーの場合は適切なメッセージを表示）
        if (problems.length > 0 && !problems[0].includes('予期せぬエラー')) {
            commentParts.push(`【問題点】\n${problems.join('\n')}`);
        } else {
            commentParts.push('【問題点】\n• 問題なし');
        }

        // 改善提案の追加
        if (suggestions.length > 0) {
            commentParts.push(`【改善提案】\n${suggestions.join('\n')}`);
        }

        // メッセージとボディの論理的整合性の評価は、メッセージレイヤーの逐次的展開性で問題があった場合のみ表示
        if (evaluation.criteriaId === "メッセージとボディの論理的整合性" && 
            !evaluation.feedback.includes("問題なし")) {
            commentParts.push("※メッセージレイヤーの逐次的展開性に問題があるため、追加で評価を実施しました。");
        }

        return commentParts.filter(Boolean).join('\n\n');
    } catch (error) {
        // エラーが発生した場合は適切なエラーメッセージを返す
        console.error('Error in generateCommentText:', error);
        return [
            `【評価観点】${evaluation.criteriaId}`,
            '【問題点】',
            '• 評価結果の生成中にエラーが発生しました',
            '• 評価を再度実行してください',
            '• 問題が続く場合は管理者に連絡してください'
        ].join('\n');
    }
}

/**
 * コメントを追加する位置を決定する
 */
async function getCommentTarget(context: Word.RequestContext, evaluation: Evaluation, paragraphs: Word.ParagraphCollection): Promise<Word.Range | null> {
    try {
        // カテゴリIDに基づいて評価対象範囲を決定
        const targetType = getTargetTypeFromCategoryId(evaluation.criteriaId);
        console.log(`評価タイプ: ${targetType}, 評価基準: ${evaluation.criteriaId}`);

        // 段落のテキストを読み込む
        paragraphs.load("text");
        await context.sync();

        // locationの前処理
        const location = preprocessLocation(evaluation.location);
        console.log(`前処理後の位置情報: ${location}`);

        // 位置検索のロジックを改善
        let targetParagraph: Word.Paragraph | null = null;

        if (location) {
            // 複数の位置情報がある場合は分割して処理
            const locationParts = location.split(/[、,]/);
            
            for (const part of locationParts) {
                const cleanPart = cleanLocationText(part);
                console.log(`クリーニング後の位置情報パート: ${cleanPart}`);
                
                // 様々なマッチング方法を試行
                targetParagraph = findParagraphByVariousMethods(paragraphs.items, cleanPart);
                
                if (targetParagraph) {
                    console.log(`位置が特定されました: ${targetParagraph.text.substring(0, 50)}...`);
                    break;
                }
            }
        }

        // 位置が特定できない場合は評価タイプに基づいてフォールバック
        if (!targetParagraph) {
            targetParagraph = findFallbackParagraph(paragraphs.items, targetType);
            if (targetParagraph) {
                console.log(`フォールバック位置が使用されました: ${targetParagraph.text.substring(0, 50)}...`);
            }
        }

        // 最終的なフォールバック：文書の先頭の段落
        if (!targetParagraph && paragraphs.items.length > 0) {
            console.warn(`コメント位置が特定できないため、先頭段落を使用: ${evaluation.criteriaId}`);
            targetParagraph = paragraphs.items[0];
        }

        return targetParagraph ? targetParagraph.getRange() : null;

    } catch (error) {
        console.error("コメント位置の特定中にエラー:", error);
        throw error;
    }
}

/**
 * 位置情報の前処理
 */
function preprocessLocation(location: string | undefined): string {
    if (!location) return "";
    
    // ナンバリングを含む識別子を基本形に変換
    return location.trim()
        .replace(/【サマリー\d+】/g, "【サマリー】")
        .replace(/【ストーリー\d+-\d+】/g, "【ストーリー】")
        .replace(/【本文\d+】/g, "【ボディ】");
}

/**
 * 位置情報テキストのクリーニング
 */
function cleanLocationText(text: string): string {
    return text
        .trim()
        .replace(/[【】［］\[\]]/g, '')      // 括弧類を削除
        .replace(/^\d+\.\s*/, '')           // 先頭の番号を削除
        .replace(/^(ストーリー|サマリー)(\d+[-\d]*)?[:：]?\s*/i, '$1') // 番号付きの識別子を基本形に変換
        .trim();
}

/**
 * 様々な方法でパラグラフを検索
 */
function findParagraphByVariousMethods(paragraphs: Word.Paragraph[], searchText: string): Word.Paragraph | null {
    // 1. 完全一致
    let found = paragraphs.find(p => p.text.trim() === searchText);
    if (found) {
        console.log('完全一致で発見');
        return found;
    }

    // 2. 部分一致（前方一致）
    found = paragraphs.find(p => p.text.trim().startsWith(searchText));
    if (found) {
        console.log('前方一致で発見');
        return found;
    }

    // 3. 部分一致（含む）
    found = paragraphs.find(p => p.text.trim().includes(searchText));
    if (found) {
        console.log('部分一致で発見');
        return found;
    }

    // 4. キーワードベースの検索
    const keywords = searchText.split(/\s+/).filter(k => k.length > 3); // 短すぎる単語を除外
    if (keywords.length > 0) {
        found = paragraphs.find(p => 
            keywords.every(keyword => p.text.toLowerCase().includes(keyword.toLowerCase()))
        );
        if (found) {
            console.log('キーワード一致で発見');
            return found;
        }
    }

    console.log('該当するパラグラフが見つかりませんでした');
    return null;
}

/**
 * フォールバックパラグラフの検索
 */
function findFallbackParagraph(paragraphs: Word.Paragraph[], targetType: string): Word.Paragraph | null {
    console.log(`フォールバック検索: ${targetType}`);
    
    switch (targetType) {
        case "FULL_SUMMARY_AND_STORY":
        case "FULL_SUMMARY":
            // 文書の先頭の段落を使用
            console.log('文書先頭の段落を使用');
            return paragraphs[0] || null;

        case "CONSECUTIVE_SUMMARY":
            // 短い段落（サマリー的な特徴を持つ）を探す
            const summaryParagraph = paragraphs.find(p => p.text.length < 200);
            if (summaryParagraph) {
                console.log('サマリー的な段落を発見');
                return summaryParagraph;
            }
            break;

        case "SUMMARY_STORY_BLOCK":
        case "SUMMARY_WISE_STORY_BLOCK":
            // 中程度の長さの段落を探す
            const storyParagraph = paragraphs.find(p => p.text.length >= 200 && p.text.length < 500);
            if (storyParagraph) {
                console.log('ストーリー的な段落を発見');
                return storyParagraph;
            }
            break;

        case "STORY_WISE_BODY_BLOCK":
            // 長い段落を探す
            const bodyParagraph = paragraphs.find(p => p.text.length >= 500);
            if (bodyParagraph) {
                console.log('本文的な段落を発見');
                return bodyParagraph;
            }
            break;
    }

    console.log('デフォルトの段落を使用');
    return paragraphs[0] || null;
}

/**
 * カテゴリIDから評価対象範囲を取得
 */
function getTargetTypeFromCategoryId(categoryId: string): string {
    const targetTypeMap: { [key: string]: string } = {
        "最低限の修辞表現": "FULL_SUMMARY_AND_STORY",
        "前回の振り返りの有無": "FULL_SUMMARY",
        "SCQA有無": "FULL_SUMMARY",
        "転換の接続詞の重複利用": "FULL_SUMMARY",
        "接続詞の妥当性": "CONSECUTIVE_SUMMARY",
        "サマリーレイヤーに不適な接続詞の有無": "CONSECUTIVE_SUMMARY",
        "直前のサマリーとの論理的連続性": "CONSECUTIVE_SUMMARY",
        "メッセージレイヤーの逐次的展開性": "SUMMARY_STORY_BLOCK",
        "逐次的展開の評価": "SUMMARY_STORY_BLOCK",
        "根拠s, 詳細s⇔主張": "SUMMARY_STORY_BLOCK",
        "接続詞の適切性": "SUMMARY_WISE_STORY_BLOCK",
        "転換の接続詞の二重利用": "SUMMARY_WISE_STORY_BLOCK",
        "無駄なナンバリングの回避": "SUMMARY_WISE_STORY_BLOCK",
        "メッセージとボディの論理的整合性": "STORY_WISE_BODY_BLOCK",
        "修辞表現": "FULL_SUMMARY_AND_STORY"
    };

    const targetType = targetTypeMap[categoryId];
    if (!targetType) {
        console.warn(`Unknown category ID: ${categoryId}, defaulting to FULL_SUMMARY_AND_STORY`);
        return "FULL_SUMMARY_AND_STORY";
    }
    return targetType;
}

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
                    level = 3; // ボディ
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
                        level = 3; // ボディとして扱う
                        console.log('ボディとして設定:', text.substring(0, 50));
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
                    // ボディの場合：現在のストーリーに紐づけてボディを追加
                    if (!currentStructure) {
                        console.log('サマリーが未設定のためボディ用の構造を作成');
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
                    console.log('ボディを追加:', paragraph.text.substring(0, 50));
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
                'ボディ (Level 3)': levelCounts[3] || 0,
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
        case 3: return 'ボディ';
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

/**
 * 評価結果をWordのコメントとして追加する
 * @param evaluations 評価結果の配列
 */
export async function addEvaluationComments(evaluations: Evaluation[]): Promise<void> {
    try {
        await Word.run(async (context) => {
            console.log('\n=== コメント追加処理開始 ===');
            console.log(`評価結果数: ${evaluations.length}`);
            console.log(`選択されたカテゴリ: ${Array.from(selectedCategories).join(', ')}`);

            // 文書の保護状態とアクセス権限を確認
            const document = context.document as ExtendedDocument;
            document.load("settings");
            await context.sync();

            try {
                // 文書への書き込み権限をテスト
                const testRange = document.body.insertParagraph("", "Start");
                await context.sync();
                testRange.delete();
                await context.sync();
            } catch (error) {
                console.error('文書への書き込みテストに失敗:', error);
                throw new Error('文書への書き込み権限がありません。読み取り専用モードを解除してください。');
            }

            // 文書全体のパラグラフを取得
            const paragraphs = document.body.paragraphs;
            paragraphs.load("text");
            await context.sync();

            // 既存のコメントを削除
            try {
                const doc = context.document as ExtendedDocument;
                // コメントコレクションが利用可能かチェック
                if (doc && doc.comments) {
                    doc.comments.load("items");
                    await context.sync();
                    
                    if (doc.comments.items && doc.comments.items.length > 0) {
                        doc.comments.items.forEach((comment: Comment) => {
                            comment.delete();
                        });
                        await context.sync();
                        console.log(`${doc.comments.items.length}件の既存コメントを削除しました`);
                    }
                } else {
                    console.log('コメントコレクションが利用できません。新規コメントのみ追加します。');
                }
            } catch (error) {
                console.warn('既存のコメント削除中にエラー:', error);
                // コメント削除に失敗しても処理を継続
            }

            // 選択されたカテゴリに属する評価基準のみをフィルタリング
            const filteredEvaluations = selectedCategories.size > 0
                ? evaluations.filter(evaluation => {
                    for (const categoryId of selectedCategories) {
                        if (CATEGORY_CRITERIA_MAP[categoryId]?.includes(evaluation.criteriaId)) {
                            return true;
                        }
                    }
                    return false;
                })
                : evaluations;

            console.log(`フィルタリング後の評価結果数: ${filteredEvaluations.length}`);

            // 各評価結果に対してコメントを追加
            for (const evaluation of filteredEvaluations) {
                try {
                    // 「問題なし」の場合はスキップ
                    if (evaluation.feedback.includes('問題なし')) {
                        console.log(`問題なしのためスキップ: ${evaluation.criteriaId}`);
                        continue;
                    }

                    // コメントのテキストを生成
                    const commentText = generateCommentText(evaluation);

                    // コメントを追加する位置を取得
                    const targetRange = await getCommentTarget(context, evaluation, paragraphs);
                    if (!targetRange) {
                        console.warn(`コメント追加位置が見つかりません: ${evaluation.criteriaId}`);
                        continue;
                    }

                    try {
                        // コメントを追加
                        targetRange.insertComment(commentText);
                        await context.sync();
                        console.log(`コメントを追加: ${evaluation.criteriaId}`);
                    } catch (commentError) {
                        console.error('コメント追加エラー:', commentError);
                        throw commentError;
                    }
                } catch (evaluationError) {
                    console.error('個別の評価に対するコメント追加中にエラー:', evaluationError);
                    continue;
                }
            }

            console.log('=== コメント追加処理完了 ===');
        });
    } catch (error) {
        console.error('Error in addEvaluationComments:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        
        if (errorMessage.includes('AccessDenied')) {
            throw new Error(
                '文書へのアクセス権限がありません。以下を確認してください：\n' +
                '1. 文書が読み取り専用モードでないこと\n' +
                '2. 文書が保護されていないこと\n' +
                '3. 文書が共有モードでない場合は、編集モードで開き直してください\n' +
                '4. Office アドインに必要な権限が付与されていること'
            );
        } else {
            throw new Error(
                'コメントの追加に失敗しました。以下を確認してください：\n' +
                '1. Word文書が正しく開かれていること\n' +
                '2. 文書が破損していないこと\n' +
                '3. 十分なメモリとディスク容量があること'
            );
        }
    }
}