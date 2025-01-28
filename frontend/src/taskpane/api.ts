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
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
    credentials: 'include' as RequestCredentials,
};

// 開発環境用のフェッチオプション
const devFetchOptions = {
    ...fetchOptions,
    headers: {
        ...fetchOptions.headers,
        'Origin': 'https://localhost:3001',
    }
};

/**
 * 文書を評価するAPIを呼び出す
 */
export async function reviewDocument(document: DocumentStructure): Promise<ReviewResponse> {
    try {
        // 文書構造をAPIリクエスト形式に変換
        const requestData: ReviewRequest = {
            title: document.title,
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
            ])
        };

        console.log('Sending request to API:', {
            url: API_ENDPOINTS.REVIEW,
            method: 'POST',
            headers: devFetchOptions.headers,
            data: requestData
        });

        // APIリクエストを送信
        const response = await fetch(API_ENDPOINTS.REVIEW, {
            ...devFetchOptions,
            method: 'POST',
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('API error response:', errorText);
            throw new Error(`API error: ${response.status}`);
        }

        const result = await response.json();
        console.log('API response:', result);
        return result;
    } catch (error) {
        console.error('API request failed:', error);
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