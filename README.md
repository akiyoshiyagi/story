# Story Checker（ストーリーチェッカー）

ビジネス文書の論理構造と表現を自動評価し、改善提案を提供するMicrosoft Word アドイン

## 機能概要

- 文書の論理構造分析
- 表現の適切性評価
- リアルタイムフィードバック
- 具体的な改善提案
- Word文書へのコメント自動挿入

## 必要要件

### フロントエンド
- Node.js 14.x以上
- npm 6.x以上
- Microsoft Office（Word）2016以上

### バックエンド
- Python 3.8以上
- FastAPI
- OpenAI API アクセス権

## セットアップ手順

### バックエンド

1. 環境構築
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集し、必要な環境変数を設定
```

3. サーバーの起動
```bash
python -m uvicorn app.main:app --reload --port 8001
```

### フロントエンド

1. 依存パッケージのインストール
```bash
cd frontend
npm install
```

2. 開発サーバーの起動
```bash
npm run dev
```

## 使用方法

1. Word文書を開く
2. アドインタブから「Story Checker」を起動
3. 「実行」ボタンをクリックして文書を評価
4. 評価結果と改善提案を確認

## 評価カテゴリ

- 全文修辞表現
- サマリーの論理展開
- サマリー単体の論理
- サマリーとストーリー間の論理
- ストーリー単体の論理
- 細部の修辞表現

## 開発者向け情報

### テスト実行
```bash
# バックエンドのテスト
cd backend
python -m pytest

# フロントエンドのテスト
cd frontend
npm test
```

### ビルド
```bash
cd frontend
npm run build
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 注意事項

- APIキーは必ず環境変数で管理してください
- 本番環境では適切なセキュリティ設定を行ってください
- 大量のリクエストを送信する場合は、APIの利用制限に注意してください 