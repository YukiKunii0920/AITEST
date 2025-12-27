# AI Meeting Agent System - Step 2完了版

TeamsおよびGoogle Meetの会議に参加し、リアルタイムで議論を聴取・議事録化し、複数の専門家AIエージェント（PM、マーケター、法務、営業、コンサルタント）がチャット欄に有益なコメントやアドバイスを投稿するシステムです。

**✅ Step 2完了**: マルチエージェントシステムが実装され、AIが自動的に会議を分析してアドバイスを投稿します。

---

## 📋 概要

このシステムは、以下の機能を提供します：

1. **会議Bot参加**: Microsoft Teams、Google Meet、Zoomなどの会議にBotとして参加
2. **リアルタイム文字起こし**: 音声をリアルタイムでテキスト化（日本語対応）
3. **✨ マルチエージェント分析**: 5つの専門家AIが議論を分析
4. **✨ 自動チャット介入**: 適切なタイミングでチャットにアドバイスを投稿

---

## 🤖 専門家AIエージェント

### 📊 PM Agent（プロジェクトマネージャー）
- **視点**: プロジェクト管理
- **監視項目**: スケジュール遅延、リソース不足、スコープクリープ、決定事項の未記録

### 📈 Marketer Agent（マーケター）
- **視点**: 市場・顧客
- **監視項目**: 顧客ニーズとの乖離、市場機会、競合優位性、ブランディング

### ⚖️ Legal Agent（法務担当）
- **視点**: 法務・コンプライアンス
- **監視項目**: 契約リスク、知的財産権、NDA違反、法規制への抵触

### 💼 Sales Agent（営業担当）
- **視点**: 売上・顧客関係
- **監視項目**: 売上機会、顧客満足度、競合との差別化、チャーンリスク

### 💡 Consultant Agent（コンサルタント）
- **視点**: 論理構成・課題解決
- **監視項目**: 論理的整合性、MECE、フレームワーク活用、意思決定の構造化

---

## 🏗️ アーキテクチャ

```
┌─────────────────┐
│  Google Meet    │
│  Teams / Zoom   │
└────────┬────────┘
         │
         │ Bot参加
         ▼
┌─────────────────┐
│   Recall.ai     │
│   Bot Service   │
└────────┬────────┘
         │
         │ Webhook (リアルタイム文字起こし)
         ▼
┌─────────────────┐
│  Webhook Server │
│   (FastAPI)     │
└────────┬────────┘
         │
         │ 文字起こし処理
         ▼
┌─────────────────┐
│ Meeting Analyzer│
└────────┬────────┘
         │
         │ 並列分析
         ▼
┌─────────────────────────────────────┐
│  Supervisor Agent                   │
│  ┌────────────────────────────────┐ │
│  │ 5つの専門家エージェントを統括  │ │
│  │ - 発言権の制御                 │ │
│  │ - 優先度評価                   │ │
│  │ - 重複排除                     │ │
│  └────────────────────────────────┘ │
└───────────┬─────────────────────────┘
            │
            │ 最適な発言を選択
            ▼
    ┌───────────────┐
    │ チャット投稿  │
    └───────────────┘
```

---

## 🚀 セットアップ

### 1. 前提条件

- Python 3.10以上
- Recall.ai APIキー
- OpenAI APIキー（GPT-4o-mini使用）
- ngrok（ローカル開発時）

### 2. インストール

```bash
# リポジトリをクローン
git clone https://github.com/YukiKunii0920/AITEST.git
cd AITEST

# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt
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

# OpenAI API設定（必須）
OPENAI_API_KEY=your_openai_api_key_here

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log
```

### 4. ngrokでWebhookエンドポイントを公開

```bash
ngrok http 8000
# 表示されたURLをconfig/.envのWEBHOOK_PUBLIC_URLに設定
```

---

## 📖 使い方

### Step 1: マルチエージェント対応Webhookサーバーを起動

```bash
python src/main_with_agents.py
```

### Step 2: ボットを会議に参加させる

```bash
python src/create_bot_with_agents.py "https://meet.google.com/xxx-yyyy-zzz"
```

### Step 3: 会議で話す

会議で議論を始めると、AIエージェントが自動的に：

1. **リアルタイムで文字起こしを受信**
2. **5つの専門家エージェントが並列で分析**
3. **Supervisorが最適な発言を選択**
4. **チャットに自動投稿**

### 発言例

```
📊 **PM Agent**

スケジュールについて明確な決定がされていません。
次回ミーティングまでに担当者とデッドラインを確定することをお勧めします。
```

```
📈 **Marketer Agent**

顧客の視点が不足しています。
この機能が実際のユーザーにどのような価値を提供するか、
もう一度検討することをお勧めします。
```

---

## 🎛️ 設定

### MeetingAnalyzer設定

`src/agents/meeting_analyzer.py` で調整可能：

```python
analyzer = MeetingAnalyzer(
    bot_id=bot_id,
    min_transcript_count=5,  # 最低5件の発言で分析開始
    analysis_interval=10     # 10件ごとに分析
)
```

### Supervisor設定

`src/agents/supervisor.py` で調整可能：

```python
supervisor = SupervisorAgent(
    min_interval_seconds=30,      # 最小30秒間隔
    max_responses_per_agent=5,    # エージェントごと最大5回
    priority_threshold=0.6        # 優先度0.6以上のみ発言
)
```

---

## 📊 発言制御ロジック

### 優先度スコア計算

各エージェントの発言は以下の3つの指標で評価されます：

- **Confidence（自信度）**: 0.0-1.0
- **Urgency（緊急度）**: 0.0-1.0
- **Relevance（関連性）**: 0.0-1.0

**優先度スコア** = Confidence × 0.4 + Urgency × 0.3 + Relevance × 0.3

### フィルタリング条件

以下の条件をすべて満たす発言のみが投稿されます：

1. ✅ 優先度スコアが閾値（0.6）以上
2. ✅ エージェントの発言回数が上限（5回）未満
3. ✅ 最後の発言から30秒以上経過
4. ✅ 類似した内容を既に発言していない

---

## 🔧 開発状況

### ✅ 実装済み（Step 2）

- [x] 5つの専門家エージェント実装
- [x] Supervisor Agentによる発言制御
- [x] 優先度ベースの発言選択
- [x] 重複排除ロジック
- [x] Webhookサーバーとの統合
- [x] 自動チャット投稿

### 🚧 実装予定（Step 3以降）

- [ ] LangGraphによるワークフロー実装
- [ ] Deepgram統合（高精度STT）
- [ ] RAG（検索拡張生成）による知識ベース参照
- [ ] 議事録自動生成
- [ ] アクションアイテム抽出
- [ ] データベース統合

---

## 💰 コスト試算

### 月100時間会議の場合

| 項目 | 単価 | 使用量 | 月額コスト |
|-----|------|--------|-----------|
| Recall.ai Bot | $0.70/時間 | 100時間 | $70.00 |
| OpenAI API (GPT-4o-mini) | $0.15/1M入力トークン | ~10M | $1.50 |
| OpenAI API (GPT-4o-mini) | $0.60/1M出力トークン | ~2M | $1.20 |
| インフラ（AWS等） | 変動 | - | $20-50 |
| **合計** | - | - | **$92.70-122.70** |

※ 実際のコストは会議の長さ、発言頻度、エージェントの発言回数により変動します。

---

## 📚 ドキュメント

- [セットアップガイド](docs/SETUP_GUIDE.md)
- [アーキテクチャ](docs/ARCHITECTURE.md)
- [Step 1完了レポート](docs/STEP1_COMPLETION.md)
- [Step 2完了レポート](docs/STEP2_COMPLETION.md)

---

## 🐛 トラブルシューティング

### エージェントが発言しない

**原因**:
- 優先度スコアが閾値未満
- 発言回数が上限に達している
- 最小発言間隔（30秒）未満
- OpenAI APIキーが設定されていない

**解決策**:
1. `config/.env`の`OPENAI_API_KEY`を確認
2. Supervisorの`priority_threshold`を下げる（0.5等）
3. ログを確認（`logs/bot.log`）

### エージェントが同じことを繰り返す

**原因**: 重複チェックが機能していない

**解決策**: Supervisorの`_is_duplicate()`メソッドの閾値を調整

---

## 📄 ライセンス

MIT License

---

## 🤝 コントリビューション

プルリクエストを歓迎します。

---

**実装者**: Manus AI Agent  
**日付**: 2025年12月27日  
**バージョン**: 0.2.0（Step 2完了）
