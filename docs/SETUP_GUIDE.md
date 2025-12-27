# セットアップガイド

このガイドでは、AI Meeting Agent Systemのセットアップ手順を詳しく説明します。

## 目次

1. [前提条件](#前提条件)
2. [Recall.ai APIキーの取得](#recallai-apiキーの取得)
3. [プロジェクトのセットアップ](#プロジェクトのセットアップ)
4. [ngrokのセットアップ](#ngrokのセットアップ)
5. [動作確認](#動作確認)

## 前提条件

以下のソフトウェアがインストールされていることを確認してください：

- **Python 3.10以上**
  ```bash
  python --version
  # または
  python3 --version
  ```

- **Git**
  ```bash
  git --version
  ```

- **pip**（Pythonパッケージマネージャー）
  ```bash
  pip --version
  # または
  pip3 --version
  ```

## Recall.ai APIキーの取得

1. [Recall.ai Dashboard](https://dashboard.recall.ai) にアクセス
2. アカウントを作成（GitHubまたはGoogleアカウントでサインアップ可能）
3. ダッシュボードの「API Keys」セクションに移動
4. 「Create API Key」をクリック
5. APIキーをコピーして安全な場所に保存

## プロジェクトのセットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/YukiKunii0920/AITEST.git
cd AITEST
```

### 2. 仮想環境の作成（推奨）

```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

```bash
# .envファイルを作成
cp config/.env.example config/.env

# エディタで編集
nano config/.env
# または
vim config/.env
```

`config/.env` の内容を編集：

```env
# Recall.ai API設定
RECALL_API_KEY=your_actual_api_key_here  # ← ここに取得したAPIキーを貼り付け
RECALL_API_BASE_URL=https://us-east-1.recall.ai/api/v1

# Webhook設定（後でngrokのURLに更新）
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8000
WEBHOOK_PUBLIC_URL=http://localhost:8000  # ← 後でngrokのURLに更新

# OpenAI API設定（将来のマルチエージェント用、今は空でOK）
OPENAI_API_KEY=

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log
```

## ngrokのセットアップ

Recall.aiからのWebhookを受信するために、ローカルサーバーをインターネットに公開する必要があります。

### 1. ngrokのインストール

#### Linux/Mac:

```bash
# Homebrewを使用（Mac）
brew install ngrok

# または直接ダウンロード
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

#### Windows:

1. [ngrok公式サイト](https://ngrok.com/download) からダウンロード
2. ZIPファイルを解凍
3. `ngrok.exe` をPATHに追加

### 2. ngrokアカウントの作成（オプションだが推奨）

1. [ngrok.com](https://ngrok.com) でアカウントを作成
2. ダッシュボードから認証トークンを取得
3. 認証トークンを設定：
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

### 3. ngrokの起動

```bash
ngrok http 8000
```

出力例：
```
ngrok

Session Status                online
Account                       your-email@example.com
Version                       3.x.x
Region                        Japan (jp)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123def456.ngrok-free.app -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

### 4. Webhook URLの更新

上記の `Forwarding` に表示されたHTTPS URLをコピーし、`config/.env` を更新：

```env
WEBHOOK_PUBLIC_URL=https://abc123def456.ngrok-free.app
```

**注意**: ngrokを再起動するたびにURLが変わります。有料プランでは固定URLを取得できます。

## 動作確認

### 1. Webhookサーバーの起動

新しいターミナルを開き：

```bash
cd AITEST
source venv/bin/activate  # 仮想環境を有効化
python src/main.py
```

正常に起動すると、以下のような出力が表示されます：

```
2025-12-27 10:00:00 [INFO] root: Logging configured: level=INFO, file=logs/bot.log
2025-12-27 10:00:00 [INFO] __main__: ================================================================================
2025-12-27 10:00:00 [INFO] __main__: Meeting AI Agent System - Webhook Server
2025-12-27 10:00:00 [INFO] __main__: ================================================================================
2025-12-27 10:00:00 [INFO] __main__: Webhook URL: https://abc123def456.ngrok-free.app/webhook/recall
2025-12-27 10:00:00 [INFO] __main__: Status endpoint: https://abc123def456.ngrok-free.app/status
2025-12-27 10:00:00 [INFO] __main__: Transcript endpoint: https://abc123def456.ngrok-free.app/transcript
2025-12-27 10:00:00 [INFO] __main__: ================================================================================
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 2. ヘルスチェック

ブラウザまたはcurlで確認：

```bash
curl http://localhost:8000/
```

レスポンス例：
```json
{
  "status": "ok",
  "service": "Meeting AI Agent Webhook Server",
  "timestamp": "2025-12-27T10:00:00.000000"
}
```

### 3. テスト会議の作成

Google Meetで新しい会議を作成：

1. [Google Meet](https://meet.google.com) にアクセス
2. 「新しい会議を作成」をクリック
3. 会議URLをコピー（例: `https://meet.google.com/abc-defg-hij`）

### 4. ボットを会議に参加させる

新しいターミナルを開き：

```bash
cd AITEST
source venv/bin/activate
python src/create_bot.py "https://meet.google.com/abc-defg-hij"
```

成功すると、以下のような出力が表示されます：

```
2025-12-27 10:01:00 [INFO] src.bot.recall_client: RecallAPIClient initialized with base_url: https://us-east-1.recall.ai/api/v1
2025-12-27 10:01:00 [INFO] src.bot.recall_client: Creating bot for meeting: https://meet.google.com/abc-defg-hij
2025-12-27 10:01:01 [INFO] src.bot.recall_client: Bot created successfully: 3fa85f64-5717-4562-b3fc-2c963f66afa6
2025-12-27 10:01:01 [INFO] __main__: ================================================================================
2025-12-27 10:01:01 [INFO] __main__: ✅ Bot created successfully!
2025-12-27 10:01:01 [INFO] __main__: ================================================================================
2025-12-27 10:01:01 [INFO] __main__: Bot ID: 3fa85f64-5717-4562-b3fc-2c963f66afa6
2025-12-27 10:01:01 [INFO] __main__: Status: {'code': 'ready'}
2025-12-27 10:01:01 [INFO] __main__: ================================================================================
```

### 5. ボットの動作確認

1. **会議に参加**: 作成した会議URLにブラウザでアクセス
2. **ボットの参加を確認**: 「AI Meeting Assistant」という名前の参加者が表示されるはず
3. **話してみる**: 何か話すと、Webhookサーバーのログに文字起こしが表示されます
4. **チャットメッセージを送信**:
   ```bash
   python src/send_message.py <bot_id> "こんにちは、テストメッセージです"
   ```

## トラブルシューティング

### ボットが会議に参加しない

- **原因1**: 会議がまだ開始されていない
  - **解決**: 先に会議URLにアクセスして、会議を開始してからボットを作成

- **原因2**: APIキーが無効
  - **解決**: `config/.env` のAPIキーを確認

- **原因3**: Recall.aiのクレジットが不足
  - **解決**: ダッシュボードでクレジット残高を確認

### Webhookが受信できない

- **原因1**: ngrokが起動していない
  - **解決**: `ngrok http 8000` を実行

- **原因2**: Webhook URLが古い
  - **解決**: ngrokを再起動した場合、新しいURLで `config/.env` を更新し、Webhookサーバーを再起動

- **原因3**: ファイアウォールがポートをブロック
  - **解決**: ポート8000を開放

### 文字起こしが表示されない

- **原因1**: 音声が小さすぎる
  - **解決**: マイクの音量を上げる

- **原因2**: 言語設定が間違っている
  - **解決**: `src/bot/recall_client.py` の `language` パラメータを確認

## 次のステップ

セットアップが完了したら、以下のドキュメントを参照してください：

- [API Reference](API_REFERENCE.md) - APIの詳細な使い方
- [Architecture](ARCHITECTURE.md) - システムアーキテクチャの詳細
- [Development Guide](DEVELOPMENT.md) - 開発者向けガイド

## サポート

問題が解決しない場合は、GitHubのissueを作成してください。
