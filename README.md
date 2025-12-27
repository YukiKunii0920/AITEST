# AI Meeting Agent System

TeamsおよびGoogle Meetの会議に参加し、リアルタイムで議論を聴取・議事録化し、複数の専門家AIエージェント（PM、マーケター、法務、営業、コンサルタント）がチャット欄に有益なコメントやアドバイスを投稿するシステムです。

## 📋 概要

このシステムは、以下の機能を提供します：

1. **会議Bot参加**: Microsoft Teams、Google Meet、Zoomなどの会議にBotとして参加
2. **リアルタイム文字起こし**: 音声をリアルタイムでテキスト化（日本語対応）
3. **マルチエージェント分析**: 複数の専門家AIが議論を分析（将来実装予定）
4. **チャット介入**: 適切なタイミングでチャットにアドバイスを投稿

## 🏗️ アーキテクチャ

### 技術スタック

- **会議Bot API**: Recall.ai
- **音声認識**: Recall.ai Streaming (日本語対応)
- **Webhookサーバー**: FastAPI + Uvicorn
- **マルチエージェント**: LangGraph（将来実装予定）
- **LLM**: OpenAI GPT-4o（将来実装予定）

### システム構成

```
┌─────────────────┐
│  Google Meet    │
│  Teams / Zoom   │
└────────┬────────┘
         │
         │ Bot参加
         ▼
┌─────────────────┐
│   Recall.ai     │◄─── Create Bot API
│   Bot Service   │
└────────┬────────┘
         │
         │ Webhook (リアルタイムイベント)
         ▼
┌─────────────────┐
│  Webhook Server │
│   (FastAPI)     │
└────────┬────────┘
         │
         │ イベント処理
         ▼
┌─────────────────┐
│ Multi-Agent     │
│ System          │◄─── 将来実装
│ (LangGraph)     │
└─────────────────┘
```

## 🚀 セットアップ

### 1. 前提条件

- Python 3.10以上
- Recall.ai APIキー（https://dashboard.recall.ai から取得）
- ngrok（ローカル開発時のWebhook受信用）

### 2. インストール

```bash
# リポジトリをクローン
git clone https://github.com/YukiKunii0920/AITEST.git
cd AITEST

# 依存パッケージをインストール
pip install -r requirements.txt

# 環境変数を設定
cp config/.env.example config/.env
# config/.env を編集してAPIキーを設定
```

### 3. 環境変数の設定

`config/.env` ファイルを編集：

```env
# Recall.ai API設定
RECALL_API_KEY=your_recall_api_key_here
RECALL_API_BASE_URL=https://us-east-1.recall.ai/api/v1

# Webhook設定
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8000
WEBHOOK_PUBLIC_URL=https://your-ngrok-url.ngrok.io

# OpenAI API設定（将来のマルチエージェント用）
OPENAI_API_KEY=your_openai_api_key_here
```

### 4. ngrokでWebhookエンドポイントを公開（ローカル開発時）

```bash
# 別のターミナルでngrokを起動
ngrok http 8000

# 表示されたURLをconfig/.envのWEBHOOK_PUBLIC_URLに設定
# 例: https://abc123.ngrok.io
```

## 📖 使い方

### Step 1: Webhookサーバーを起動

```bash
python src/main.py
```

サーバーが起動すると、以下のエンドポイントが利用可能になります：

- `POST /webhook/recall`: Recall.aiからのWebhook受信
- `GET /status`: 現在の状態を確認
- `GET /transcript`: 文字起こし履歴を取得

### Step 2: ボットを会議に参加させる

```bash
# Google Meetの例
python src/create_bot.py "https://meet.google.com/xxx-yyyy-zzz"

# オプション付き
python src/create_bot.py "https://meet.google.com/xxx-yyyy-zzz" \
  --name "AI Assistant" \
  --join-delay 5  # 5分後に参加
```

実行すると、ボットIDが表示されます。このIDは次のステップで使用します。

### Step 3: ボットの状態を確認

```bash
python src/get_bot_status.py <bot_id>
```

### Step 4: チャットメッセージを送信

```bash
# 全員に送信
python src/send_message.py <bot_id> "こんにちは、AIアシスタントです"

# メッセージをピン留め
python src/send_message.py <bot_id> "重要なお知らせ" --pin
```

## 📂 プロジェクト構造

```
AITEST/
├── config/
│   ├── .env.example          # 環境変数テンプレート
│   └── .env                  # 環境変数（要作成）
├── src/
│   ├── bot/
│   │   ├── recall_client.py  # Recall.ai APIクライアント
│   │   └── webhook_server.py # Webhookサーバー
│   ├── agents/               # マルチエージェント（将来実装）
│   ├── utils/
│   │   ├── config.py         # 設定管理
│   │   └── logger.py         # ロギング設定
│   ├── main.py               # メインアプリケーション
│   ├── create_bot.py         # ボット作成スクリプト
│   ├── get_bot_status.py     # ボット状態確認スクリプト
│   └── send_message.py       # メッセージ送信スクリプト
├── tests/                    # テストコード
├── docs/                     # ドキュメント
├── requirements.txt          # 依存パッケージ
└── README.md                 # このファイル
```

## 🔧 開発状況

### ✅ 実装済み（Step 1）

- [x] Recall.ai APIクライアント
- [x] Webhookサーバー（FastAPI）
- [x] リアルタイム文字起こし受信
- [x] 参加者イベント処理
- [x] チャットメッセージ送信
- [x] ボット管理スクリプト

### 🚧 実装予定（Step 2以降）

- [ ] Deepgram統合（より高精度な日本語STT）
- [ ] LangGraphによるマルチエージェント制御
- [ ] 専門家AIエージェント（PM、マーケター、法務、営業、コンサルタント）
- [ ] 発言タイミング制御（Supervisorモデル）
- [ ] 議事録自動生成
- [ ] データベース統合（会議履歴保存）

## 📝 ログ

ログは以下の場所に保存されます：

- **コンソール**: 人間が読みやすい形式
- **ファイル**: `logs/bot.log`（JSON形式）

## 🐛 トラブルシューティング

### Webhookが受信できない

1. ngrokが起動していることを確認
2. `config/.env`の`WEBHOOK_PUBLIC_URL`が正しいことを確認
3. Webhookサーバー（`python src/main.py`）が起動していることを確認

### ボットが会議に参加できない

1. 会議URLが正しいことを確認
2. 会議が開始されていることを確認（事前に会議を作成しておく）
3. Recall.ai APIキーが有効であることを確認

### 文字起こしが表示されない

1. 会議で誰かが話していることを確認
2. Webhookサーバーのログを確認（`transcript.data`イベントが受信されているか）
3. ボットのステータスを確認（`python src/get_bot_status.py <bot_id>`）

## 📄 ライセンス

MIT License

## 🤝 コントリビューション

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。

## 📞 サポート

問題が発生した場合は、GitHubのissueを作成してください。
