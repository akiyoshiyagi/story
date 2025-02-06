/**
 * APIクライアントモジュール
 */
import { API_ENDPOINTS, OPENAI_CONFIG } from "./const";
import { DocumentStructure, ReviewResponse } from "./types";

interface ReviewRequest {
    title: string;
    full_text: string;
    summary: string;
    paragraphs: string[];
}

interface OpenAIRequest {
    model: string;
    messages: {
        role: string;
        content: string;
    }[];
    max_tokens: number;
    temperature: number;
}

// 共通のフェッチオプション
const fetchOptions = {
    mode: 'cors' as RequestMode,
    credentials: 'same-origin' as RequestCredentials,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
}

// 開発環境用のフェッチオプション
const devFetchOptions = {
    ...fetchOptions,
    method: 'GET',
}

/**
 * 文書を評価するAPIを呼び出す
 */
export async function reviewDocument(document: DocumentStructure): Promise<ReviewResponse> {
    try {
        // 入力値の検証を追加
        if (!document || !document.contents || document.contents.length === 0) {
            throw new Error("文書の内容が空です");
        }

        // 文書構造をAPIリクエスト形式に変換
        const requestData: ReviewRequest = {
            title: document.title || "無題",
            full_text: document.contents.map(group => 
                `${group.summary}\n${group.stories.map(story => 
                    `${story.story}\n${story.bodies.join('\n')}`
                ).join('\n')}`
            ).join('\n\n'),
            summary: document.contents.map(group => group.summary).join('\n'),
            paragraphs: document.contents.flatMap(group => [
                group.summary,
                ...group.stories.flatMap(story => [
                    story.story,
                    ...story.bodies
                ])
            ]).filter(text => text && text.trim().length > 0) // 空の段落を除外
        };

        console.log('\n=== APIリクエスト詳細 ===');
        console.log('リクエストURL:', API_ENDPOINTS.REVIEW);
        console.log('リクエストメソッド: POST');
        console.log('リクエストヘッダー:', devFetchOptions.headers);
        console.log('リクエストデータ:', {
            title: requestData.title,
            summary_length: requestData.summary.length,
            full_text_length: requestData.full_text.length,
            paragraphs_count: requestData.paragraphs.length
        });
        console.log('リクエスト本文のサンプル:', {
            summary: requestData.summary.substring(0, 100) + '...',
            full_text: requestData.full_text.substring(0, 100) + '...',
            paragraphs: requestData.paragraphs.slice(0, 3).map(p => p.substring(0, 50) + '...')
        });

        // APIリクエストを送信
        const response = await fetch(API_ENDPOINTS.REVIEW, {
            ...devFetchOptions,
            method: 'POST',
            body: JSON.stringify(requestData)
        });

        console.log('\n=== APIレスポンス基本情報 ===');
        console.log('ステータスコード:', response.status);
        console.log('ステータステキスト:', response.statusText);
        const headers: { [key: string]: string } = {};
        response.headers.forEach((value, key) => {
            headers[key] = value;
        });
        console.log('レスポンスヘッダー:', headers);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('\n=== APIエラーレスポンス ===');
            console.error('エラーテキスト:', errorText);
            let errorMessage = `APIエラー: ${response.status}`;
            try {
                const errorJson = JSON.parse(errorText);
                errorMessage = errorJson.detail || errorJson.message || errorMessage;
                console.error('パース済みエラー:', errorJson);
            } catch (e) {
                console.error('エラーJSONのパースに失敗:', e);
            }
            throw new Error(errorMessage);
        }

        const result = await response.json();
        
        console.log('\n=== APIレスポンス詳細 ===');
        console.log('評価結果:', {
            evaluations_count: result.evaluations?.length || 0,
            categories_count: result.categories?.length || 0,
            category_scores_count: result.categoryScores?.length || 0,
            total_score: result.totalScore,
            total_judgment: result.totalJudgment
        });

        if (result.evaluations?.length > 0) {
            console.log('\n=== 評価コメントサンプル ===');
            result.evaluations.slice(0, 3).forEach((evaluation: { 
                categoryId: string;
                criteriaId: string;
                score: number;
                feedback: string;
            }, index: number) => {
                console.log(`評価 ${index + 1}:`, {
                    categoryId: evaluation.categoryId,
                    criteriaId: evaluation.criteriaId,
                    score: evaluation.score,
                    feedback: evaluation.feedback.substring(0, 100) + '...'
                });
            });
        }

        // レスポンスの検証を強化
        if (!result) {
            throw new Error("APIレスポンスが空です");
        }
        if (!Array.isArray(result.evaluations)) {
            throw new Error("評価結果の形式が不正です: evaluationsが配列ではありません");
        }
        if (!Array.isArray(result.categories)) {
            throw new Error("評価結果の形式が不正です: categoriesが配列ではありません");
        }
        if (!Array.isArray(result.categoryScores)) {
            throw new Error("評価結果の形式が不正です: categoryScoresが配列ではありません");
        }
        if (typeof result.totalScore !== 'number') {
            throw new Error("評価結果の形式が不正です: totalScoreが数値ではありません");
        }
        if (typeof result.totalJudgment !== 'string') {
            throw new Error("評価結果の形式が不正です: totalJudgmentが文字列ではありません");
        }

        // 評価結果が空の場合は警告を出力
        if (result.evaluations.length === 0) {
            console.warn('\n警告: 評価結果が空です');
        }
        
        return result;
    } catch (error) {
        console.error('\n=== APIリクエストエラー ===');
        console.error('エラー詳細:', error);
        throw error;
    }
}

/**
 * OpenAI APIを使用して文書を評価する
 */
export async function evaluateWithOpenAI(document: DocumentStructure): Promise<ReviewResponse> {
    try {
        // 文書構造をAPIリクエスト形式に変換
        const requestData = {
            model: OPENAI_CONFIG.MODEL,
            messages: [
                {
                    role: "system",
                    content: OPENAI_CONFIG.SYSTEM_PROMPT
                },
                {
                    role: "user",
                    content: document.contents.map(group => 
                        `${group.summary}\n${group.stories.map(story => 
                            `${story.story}\n${story.bodies.join('\n')}`
                        ).join('\n')}`
                    ).join('\n\n')
                }
            ],
            max_tokens: OPENAI_CONFIG.MAX_TOKENS,
            temperature: OPENAI_CONFIG.TEMPERATURE
        };

        console.log('Sending request to OpenAI API:', requestData);

        // バックエンドAPIを呼び出し
        const response = await fetch(API_ENDPOINTS.OPENAI, {
            ...devFetchOptions,
            method: 'POST',
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('OpenAI API error response:', errorText);
            throw new Error(`OpenAI API error: ${response.status}`);
        }

        const result = await response.json();
        console.log('OpenAI API response:', result);
        return result;
    } catch (error) {
        console.error('OpenAI API request failed:', error);
        throw error;
    }
}

/**
 * APIのヘルスチェックを実行
 */
export async function checkApiHealth(): Promise<boolean> {
    try {
        const response = await fetch(API_ENDPOINTS.HEALTH, devFetchOptions);
        if (!response.ok) {
            return false;
        }
        const data = await response.json();
        return data.status === 'healthy';
    } catch (error) {
        console.error('Health check failed:', error);
        return false;
    }
} 