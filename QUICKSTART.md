# 🚀 クイックスタートガイド

このガイドでは、AI Meeting Agent Systemを最速で起動して、実際の会議で試す方法を説明します。

---

## ⏱️ 所要時間

**約10分**

---

## 📋 前提条件

- [x] Python 3.10以上がインストールされている
- [x] Recall.ai APIキーを取得済み（[https://dashboard.recall.ai](https://dashboard.recall.ai)）
- [x] OpenAI APIキーを取得済み（[https://platform.openai.com](https://platform.openai.com)）
- [x] ngrokをインストール済み（[https://ngrok.com](https://ngrok.com)）

---

## 🎯 ステップ1: セットアップ（5分）

### 1.1 リポジトリをクローン

```bash
git clone https://github.com/YukiKunii0920/AITEST.git
cd AITEST
```

### 1.2 仮想環境を作成

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 1.3 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 1.4 環境変数を設定

`config/.env` ファイルを編集：

```bash
# Recall.ai API設定
RECALL_API_KEY=your_recall_api_key_here

# OpenAI API設定（必須）
OPENAI_API_KEY=your_openai_api_key_here

# Webhook設定（後で更新）
WEBHOOK_PUBLIC_URL=https://your-ngrok-url.ngrok.io
```

---

## 🌐 ステップ2: ngrokでWebhookを公開（2分）

### 2.1 ngrokを起動

```bash
ngrok http 8000
```

### 2.2 URLをコピー

ngrokの画面に表示される `Forwarding` のURLをコピー：

```
Forwarding  https://xxxx-yyyy-zzzz.ngrok.io -> http://localhost:8000
```

### 2.3 環境変数を更新

`config/.env` の `WEBHOOK_PUBLIC_URL` を更新：

```env
WEBHOOK_PUBLIC_URL=https://xxxx-yyyy-zzzz.ngrok.io
```

---

## 🤖 ステップ3: システムを起動（3分）

### 3.1 Webhookサーバーを起動

**ターミナル1**:

```bash
cd AITEST
source venv/bin/activate
python src/main_with_agents.py
```

以下のログが表示されればOK：

```
================================================================================
Meeting AI Agent System - Multi-Agent Webhook Server
================================================================================
Webhook URL: https://xxxx-yyyy-zzzz.ngrok.io/webhook/recall
================================================================================
Multi-Agent System:
  - PM Agent (プロジェクト管理)
  - Marketer Agent (市場・顧客)
  - Legal Agent (法務・コンプライアンス)
  - Sales Agent (売上・顧客関係)
  - Consultant Agent (論理構成・課題解決)
================================================================================
```

### 3.2 Google Meetの会議を作成

1. [Google Meet](https://meet.google.com) にアクセス
2. 「新しい会議を作成」をクリック
3. 会議URLをコピー（例: `https://meet.google.com/xxx-yyyy-zzz`）

### 3.3 ボットを会議に参加させる

**ターミナル2**:

```bash
cd AITEST
source venv/bin/activate
python src/create_bot_with_agents.py "https://meet.google.com/xxx-yyyy-zzz"
```

成功すると以下のように表示されます：

```
================================================================================
✅ Bot created successfully!
================================================================================
Bot ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Status: {'code': 'joining_call'}
================================================================================
```

---

## 🎉 ステップ4: 会議で試す

### 4.1 会議に参加

Google Meetの会議URLにアクセスして参加します。

### 4.2 Botが参加するのを待つ

数秒後、「Recall.ai Bot」という名前の参加者が表示されます。

### 4.3 チャットで挨拶メッセージを確認

チャット欄に以下のメッセージが表示されます：

```
🤖 **AI Meeting Assistant** が会議に参加しました。

この会議は5人の専門家AIエージェントによってリアルタイムで分析されます：
📊 PM - プロジェクト管理
📈 マーケター - 市場・顧客
⚖️ 法務 - コンプライアンス
💼 営業 - 売上・顧客関係
💡 コンサルタント - 論理構成

重要な指摘がある場合、適切なタイミングでアドバイスを提供します。
```

### 4.4 会議で話す

以下のような議論をしてみてください：

**例1: スケジュールが曖昧**
```
あなた: 「新機能の開発、いつまでに完成しますか？」
同僚: 「うーん、まだ決まってないですね」
あなた: 「じゃあ、とりあえず進めましょう」
```

**期待される反応**:
```
📊 **PM Agent**

スケジュールについて明確な決定がされていません。
次回ミーティングまでに担当者とデッドラインを確定することをお勧めします。
```

**例2: 顧客視点が欠けている**
```
あなた: 「この機能、技術的には実装できます」
同僚: 「じゃあ、追加しましょう」
```

**期待される反応**:
```
📈 **Marketer Agent**

顧客の視点が不足しています。
この機能が実際のユーザーにどのような価値を提供するか、
もう一度検討することをお勧めします。
```

---

## 📊 ステップ5: ログを確認

### 5.1 Webhookサーバーのログ

**ターミナル1** に以下のようなログが表示されます：

```
[TRANSCRIPT] あなた: 新機能の開発、いつまでに完成しますか？
[TRANSCRIPT] 同僚: うーん、まだ決まってないですね
Starting meeting analysis...
PM Agent wants to speak: priority=0.75
Selected: PM Agent (priority=0.75)
Posting message from PM Agent
Message posted successfully
```

### 5.2 ボットの状態を確認

```bash
python src/get_bot_status.py <bot_id>
```

---

## 🛑 停止方法

### 1. ボットを会議から退出させる

```bash
python src/send_message.py <bot_id> --leave
```

### 2. Webhookサーバーを停止

**ターミナル1** で `Ctrl+C` を押す

### 3. ngrokを停止

**ngrokのターミナル** で `Ctrl+C` を押す

---

## 🎛️ カスタマイズ

### 発言頻度を調整

`src/agents/meeting_analyzer.py` の設定を変更：

```python
analyzer = MeetingAnalyzer(
    bot_id=bot_id,
    min_transcript_count=3,  # 3件の発言で分析開始（デフォルト: 5）
    analysis_interval=5      # 5件ごとに分析（デフォルト: 10）
)
```

### 発言の閾値を調整

`src/agents/supervisor.py` の設定を変更：

```python
supervisor = SupervisorAgent(
    min_interval_seconds=20,      # 20秒間隔（デフォルト: 30）
    max_responses_per_agent=10,   # 最大10回（デフォルト: 5）
    priority_threshold=0.5        # 閾値0.5（デフォルト: 0.6）
)
```

---

## 🐛 トラブルシューティング

### Botが会議に参加しない

**原因**: 会議URLが間違っている、またはRecall.ai APIキーが無効

**解決策**:
1. 会議URLを確認
2. `config/.env` の `RECALL_API_KEY` を確認
3. ボットの状態を確認: `python src/get_bot_status.py <bot_id>`

### エージェントが発言しない

**原因**: OpenAI APIキーが設定されていない、または優先度が低い

**解決策**:
1. `config/.env` の `OPENAI_API_KEY` を確認
2. ログを確認: `logs/bot.log`
3. 優先度閾値を下げる（上記「カスタマイズ」参照）

### Webhookが受信できない

**原因**: ngrokのURLが間違っている、またはngrokが停止している

**解決策**:
1. ngrokが起動しているか確認
2. `config/.env` の `WEBHOOK_PUBLIC_URL` を確認
3. Webhookサーバーを再起動

---

## 📚 次のステップ

- [詳細なセットアップガイド](docs/SETUP_GUIDE.md)
- [アーキテクチャ](docs/ARCHITECTURE.md)
- [Step 2完了レポート](docs/STEP2_COMPLETION.md)
- [README（完全版）](README_STEP2.md)

---

**実装者**: Manus AI Agent  
**日付**: 2025年12月27日
