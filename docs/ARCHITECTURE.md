# システムアーキテクチャ

## 概要

AI Meeting Agent Systemは、会議プラットフォーム（Teams、Google Meet、Zoom）にBotとして参加し、リアルタイムで議論を分析し、専門家AIエージェントがチャットを通じてアドバイスを提供するシステムです。

## アーキテクチャ図

```
┌─────────────────────────────────────────────────────────────────┐
│                        会議プラットフォーム                          │
│                  (Google Meet / Teams / Zoom)                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ ① Bot参加リクエスト
                            │    (Create Bot API)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Recall.ai                                │
│                    Meeting Bot Service                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  - 会議への参加管理                                        │   │
│  │  - 音声/映像ストリームの取得                               │   │
│  │  - リアルタイム文字起こし (STT)                            │   │
│  │  - チャットメッセージ送信                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ ② Webhook通知
                            │    (リアルタイムイベント)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Webhook Server (FastAPI)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  WebhookHandler                                          │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ - transcript.data (確定した文字起こし)              │  │   │
│  │  │ - transcript.partial_data (部分的な文字起こし)      │  │   │
│  │  │ - participant_events.join (参加者参加)             │  │   │
│  │  │ - participant_events.leave (参加者退出)            │  │   │
│  │  │ - participant_events.chat_message (チャット受信)   │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ ③ イベント処理
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              マルチエージェントシステム (将来実装)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Supervisor Agent (LangGraph)                            │   │
│  │  - 議論の文脈管理                                         │   │
│  │  - 発言権の制御                                           │   │
│  │  - エージェント間の調整                                    │   │
│  └───────────────────┬──────────────────────────────────────┘   │
│                      │                                           │
│       ┌──────────────┼──────────────┬──────────────┐            │
│       ▼              ▼              ▼              ▼            │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐         │
│  │   PM   │    │マーケタ│    │  法務  │    │  営業  │         │
│  │ Agent  │    │ Agent  │    │ Agent  │    │ Agent  │         │
│  └────────┘    └────────┘    └────────┘    └────────┘         │
│       │              │              │              │            │
│       └──────────────┼──────────────┴──────────────┘            │
│                      ▼                                           │
│              ┌────────────┐                                      │
│              │コンサルタント│                                      │
│              │   Agent    │                                      │
│              └────────────┘                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ ④ チャットメッセージ送信
                            │    (Send Chat Message API)
                            ▼
                    Recall.ai → 会議チャット
```

## コンポーネント詳細

### 1. Recall.ai Meeting Bot Service

**役割**: 会議プラットフォームとの接続を抽象化し、統一されたAPIを提供

**主要機能**:
- 複数プラットフォーム（Teams、Meet、Zoom）への対応
- リアルタイム音声ストリームの取得
- STT（Speech-to-Text）による文字起こし
- 話者分離（Diarization）
- チャットメッセージの送受信

**API**:
- `POST /api/v1/bot/` - ボット作成
- `GET /api/v1/bot/{id}` - ボット状態取得
- `POST /api/v1/bot/{id}/send_chat_message/` - チャット送信
- `POST /api/v1/bot/{id}/leave_call/` - 会議退出

### 2. Webhook Server (FastAPI)

**役割**: Recall.aiからのリアルタイムイベントを受信し、適切なハンドラーに振り分け

**主要コンポーネント**:

#### WebhookHandler
- **transcript_handlers**: 文字起こしイベント処理
- **participant_handlers**: 参加者イベント処理
- **chat_handlers**: チャットイベント処理

**エンドポイント**:
- `POST /webhook/recall` - Webhook受信
- `GET /status` - システム状態確認
- `GET /transcript` - 文字起こし履歴取得
- `GET /` - ヘルスチェック

**データフロー**:
```
Recall.ai Webhook
    ↓
FastAPI Request Handler
    ↓
WebhookHandler.process_webhook()
    ↓
イベントタイプに応じて振り分け
    ├─ handle_transcript_event()
    ├─ handle_participant_event()
    └─ handle_chat_event()
    ↓
登録されたカスタムハンドラーを実行
```

### 3. RecallAPIClient

**役割**: Recall.ai APIとの通信を担当するクライアントライブラリ

**主要メソッド**:
- `create_bot()` - ボット作成
- `get_bot()` - ボット情報取得
- `send_chat_message()` - チャット送信
- `leave_call()` - 会議退出

**設定可能なパラメータ**:
- `meeting_url`: 会議URL
- `bot_name`: ボット名
- `webhook_url`: Webhook受信URL
- `transcript_provider`: STTプロバイダ（recallai_streaming, deepgram_streaming）
- `language`: 言語コード（ja, en等）
- `join_at`: 参加時刻
- `chat_on_join_message`: 参加時メッセージ

### 4. マルチエージェントシステム（将来実装）

**役割**: 複数の専門家AIエージェントが協調して会議を分析し、アドバイスを提供

**アーキテクチャパターン**: Supervisor-Worker Model

#### Supervisor Agent
- **責務**: 全体の指揮・調整
- **機能**:
  - 議論のフェーズ判定（アイディア出し、収束、紛糾等）
  - 各Workerエージェントへの分析指示
  - 発言案の収集とフィルタリング
  - 発言権の承認（Turn-taking制御）

#### Worker Agents

##### PM Agent
- **視点**: プロジェクト管理
- **監視項目**:
  - スケジュール遅延リスク
  - リソース不足
  - スコープクリープ
  - 決定事項の未記録

##### Marketer Agent
- **視点**: 市場・顧客
- **監視項目**:
  - 顧客ニーズとの乖離
  - 競合優位性
  - 市場トレンド
  - ブランディングへの影響

##### Legal Agent
- **視点**: 法務・コンプライアンス
- **監視項目**:
  - 契約リスク
  - 知的財産権侵害
  - NDA違反の可能性
  - 法規制への抵触

##### Sales Agent
- **視点**: 売上・顧客関係
- **監視項目**:
  - 売上機会
  - アップセル/クロスセル
  - 顧客満足度への影響
  - 競合との差別化

##### Consultant Agent
- **視点**: 論理構成・課題解決
- **監視項目**:
  - 議論の論理的整合性
  - MECE（漏れなくダブりなく）
  - フレームワークの適用可能性
  - 意思決定の構造化

#### 制御ロジック

**発言の衝突回避と質の担保**:

1. **自信スコア（Confidence Score）**:
   各エージェントは発言案と共に自信度（0.0-1.0）を出力
   ```json
   {
     "content": "スケジュールが遅延するリスクがあります",
     "confidence": 0.85,
     "urgency": 0.7,
     "relevance": 0.9
   }
   ```

2. **Supervisorによる評価**:
   - 現在の議論の文脈との関連性
   - 発言の緊急性
   - 新規性（既に言及されていないか）
   - 自信度

3. **発言許可とキューイング**:
   - 最も有益と判断された発言を1つだけ許可
   - 他の発言は却下または待機

4. **発言頻度の制御**:
   - 特定エージェントの連続発言を制限
   - 全体のバランスを維持

## データフロー

### 1. ボット作成フロー

```
ユーザー
  ↓ python src/create_bot.py <meeting_url>
RecallAPIClient
  ↓ POST /api/v1/bot/
Recall.ai
  ↓ ボットを会議に参加させる
会議プラットフォーム
  ↓ ボット参加完了
Recall.ai
  ↓ Webhook通知（bot.ready）
Webhook Server
```

### 2. リアルタイム文字起こしフロー

```
会議参加者が発言
  ↓
会議プラットフォーム（音声ストリーム）
  ↓
Recall.ai（音声取得）
  ↓
STTエンジン（文字起こし）
  ↓
Recall.ai（Webhook送信）
  ↓ POST /webhook/recall
Webhook Server
  ↓ transcript.partial_data（部分的）
WebhookHandler
  ↓ ログ出力
  ↓ transcript.data（確定）
WebhookHandler
  ↓ 保存 + カスタムハンドラー実行
マルチエージェント（将来）
  ↓ 分析 + 発言案生成
Supervisor Agent
  ↓ 発言許可
RecallAPIClient.send_chat_message()
  ↓ POST /api/v1/bot/{id}/send_chat_message/
Recall.ai
  ↓
会議チャット
```

## 技術選定の理由

### Recall.ai
- **選定理由**:
  - 複数プラットフォーム対応
  - リアルタイムストリーム取得
  - 双方向通信（読み書き）
  - エンタープライズ対応（SOC2、GDPR）
- **代替案**: 自前でヘッドレスブラウザ実装（保守コスト大）

### FastAPI
- **選定理由**:
  - 高速（非同期処理）
  - 型安全（Pydantic）
  - 自動ドキュメント生成
  - Pythonエコシステム
- **代替案**: Flask（同期処理のみ）、Node.js Express

### LangGraph（将来実装）
- **選定理由**:
  - グラフベースのワークフロー
  - ステートフル処理
  - 条件分岐・ループ対応
  - Human-in-the-loop対応
- **代替案**: AutoGen（会話ベース）、CrewAI（タスクベース）

## スケーラビリティ

### 現在の制約
- 単一サーバーインスタンス
- インメモリ状態管理
- ローカルログファイル

### 将来のスケーリング戦略

#### 水平スケーリング
- 複数のWebhookサーバーインスタンス
- ロードバランサー（nginx、AWS ALB）
- セッションアフィニティ（Sticky Session）

#### 状態管理
- Redis（分散キャッシュ）
- PostgreSQL（永続化）
- S3（録音・文字起こしアーカイブ）

#### メッセージキュー
- RabbitMQ / AWS SQS
- 非同期処理のデカップリング
- リトライ機構

#### モニタリング
- Prometheus + Grafana
- CloudWatch / Datadog
- エラートラッキング（Sentry）

## セキュリティ

### 現在の対策
- APIキーの環境変数管理
- `.env` ファイルの `.gitignore` 登録
- HTTPS通信（ngrok）

### 将来の強化策
- APIキーのシークレット管理（AWS Secrets Manager、HashiCorp Vault）
- Webhook署名検証
- レート制限
- IPホワイトリスト
- 監査ログ

## パフォーマンス

### レイテンシ目標
- Webhook受信 → ログ出力: < 100ms
- 文字起こし確定 → エージェント分析: < 2秒
- 発言決定 → チャット投稿: < 1秒
- **合計**: < 3秒（発言から介入まで）

### 最適化ポイント
- 非同期処理（asyncio）
- LLM並列呼び出し
- キャッシング（頻出パターン）
- ストリーミングレスポンス

## 今後の拡張

### Phase 2: マルチエージェント実装
- LangGraphの統合
- 5つの専門家エージェント実装
- Supervisorロジック

### Phase 3: 高度な機能
- Deepgram統合（高精度STT）
- RAG（検索拡張生成）による知識ベース参照
- 議事録自動生成
- アクションアイテム抽出

### Phase 4: エンタープライズ機能
- マルチテナント対応
- 権限管理
- カスタムエージェント作成UI
- ダッシュボード

## 参考資料

- [Recall.ai Documentation](https://docs.recall.ai)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [技術調査レポート](../docs/recall_ai_research.md)
