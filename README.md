# RSS要約bot（LM Studio連携）

RSSフィードを取得し、LM Studioで記事を要約してDiscord webhookに投稿するボットです。複数のフィードとwebhookに対応し、フィードごとに個別設定が可能です。

## ✨ 主な機能

- **複数RSS対応**: 複数のRSSフィードを個別設定で管理
- **フィード別Discord投稿**: 各フィードを異なるDiscordチャンネルに投稿可能  
- **AI要約機能**: LM Studioを使用した高品質な記事要約
- **フィード別設定**: フィードごとに記事数上限などを個別設定
- **重複処理防止**: 処理済み記事をフィード別に記録し重複を防止
- **Docker対応**: Docker Composeで簡単デプロイ
- **柔軟なスケジューリング**: 手動実行、cron、Webサーバーによるスケジュール実行

## 🚀 クイックスタート

### 1. リポジトリのクローンとセットアップ

```bash
git clone https://github.com/your-username/rss-summarizer-lm.git
cd rss-summarizer-lm
```

### 2. 環境設定

```bash
cp .env.example .env
```

`.env`ファイルを編集：

```bash
# LM Studio設定
LM_STUDIO_URL=http://192.168.1.10:1234/v1/chat/completions
LM_STUDIO_MODEL=llama3

# 全般設定
LOG_LEVEL=INFO
SUMMARY_MAX_CHARS=1800

# 複数フィード設定（JSON配列）
FEEDS='[
  {
    "feed_name": "raspberry-pi",
    "url": "https://www.xda-developers.com/tag/raspberry-pi/feed/",
    "webhook": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN",
    "max_articles": 5
  },
  {
    "feed_name": "tech-news", 
    "url": "https://example.com/tech/rss",
    "webhook": "https://discord.com/api/webhooks/ANOTHER_WEBHOOK_ID/ANOTHER_TOKEN",
    "max_articles": 3
  }
]'
```

### 3. Docker実行（推奨）

```bash
docker-compose up -d
```

### 4. 手動実行

```bash
# 依存関係をインストール
pip install -r requirements.txt

# 1回実行
python main.py

# Webサーバー（スケジュール機能付き）を起動
python app.py
```

## 📁 プロジェクト構成

```
/
├── main.py               # RSS処理のメインオーケストレーター
├── app.py               # Flaskウェブサーバー（スケジュール機能付き）
├── src/                 # ソースモジュール
│   ├── config.py        # 設定管理
│   ├── feed_fetcher.py  # RSSフィード取得・追跡
│   ├── article_extractor.py # 記事コンテンツ抽出
│   ├── summarizer.py    # LM Studio要約処理
│   └── discord_poster.py # Discord webhook投稿
├── data/                # 実行時データ
│   ├── processed_feed1.json # フィード別処理済み記事追跡
│   ├── processed_feed2.json
│   └── ...
├── .env                 # 環境設定
├── .env.example         # 設定テンプレート
├── requirements.txt     # Python依存関係
├── dockerfile          # Dockerイメージ定義
└── docker-compose.yml  # Docker Compose設定
```

## ⚙️ 設定方法

### 環境変数

| 変数名 | 必須 | 説明 | デフォルト値 |
|--------|------|------|-------------|
| `LM_STUDIO_URL` | ✅ | LM Studio APIエンドポイント | - |
| `LM_STUDIO_MODEL` | ❌ | 使用モデル名 | `llama3` |
| `LOG_LEVEL` | ❌ | ログレベル | `INFO` |
| `SUMMARY_MAX_CHARS` | ❌ | 要約の最大文字数 | `1800` |
| `FEEDS` | ✅ | フィード設定のJSON配列 | `[]` |

### フィード設定

`FEEDS`配列の各フィードには以下が必要：

- `feed_name`: 一意な識別子（処理済みファイル名に使用）
- `url`: RSSフィードのURL
- `webhook`: Discord webhookのURL
- `max_articles`: （オプション）1回あたりの最大記事数、デフォルトは5

## 🐳 Docker デプロイ

永続データストレージ付きでDockerで実行：

```yaml
# docker-compose.yml
services:
  rss_bot:
    build: .
    volumes:
      - ./data:/app/data  # 記事追跡の永続化
    env_file:
      - .env
```

`./data/`に保存されるデータ：
- `processed_フィード名.json` - フィード別の処理済み記事追跡

## 📊 実行モード

### 1. 1回限りの実行
```bash
python main.py
```

### 2. スケジュール実行（Docker）
デフォルトのDocker設定では1時間ごとにbashループで実行。

### 3. Webサーバー＋スケジュール
```bash
python app.py
```
- ポート8000でFlaskウェブサーバーを起動
- 毎日午前7:00にRSS処理を実行
- `/`でヘルスチェックエンドポイント提供

### 4. Cronジョブ
```bash
# 1時間ごとの実行をcrontabに追加
0 * * * * cd /path/to/rss-summarizer-lm && python main.py
```

## 🔧 必要な環境

- **Python 3.11以上**
- **LM Studio**（ローカルまたはリモート）
- **Discord Webhooks**（要約投稿用）

Python パッケージ（`requirements.txt`参照）：
- `feedparser` - RSS解析
- `requests` - HTTP リクエスト
- `beautifulsoup4` - HTML解析
- `readability-lxml` - 記事コンテンツ抽出
- `flask` - Webサーバー（app.pyのみ）
- `schedule` - タスクスケジューリング（app.pyのみ）

## 📝 ログ出力

タイムスタンプ付きでstdoutにログを出力：

```
2023-08-10 10:00:00 [INFO] === RSS Bot start ===
2023-08-10 10:00:01 [INFO] Processing 2 feed(s)
2023-08-10 10:00:01 [INFO] === Processing feed: raspberry-pi ===
2023-08-10 10:00:02 [INFO] Found 3 new items for feed: raspberry-pi
2023-08-10 10:00:05 [INFO] Posted 3 articles to Discord for feed: raspberry-pi
2023-08-10 10:00:05 [INFO] === Finished processing feed: raspberry-pi ===
2023-08-10 10:00:06 [INFO] === RSS Bot finished ===
```

## 🛠️ 開発・カスタマイズ

### 新しいフィードの追加

`FEEDS`環境変数を更新するだけ：

```bash
FEEDS='[
  {
    "feed_name": "new-feed",
    "url": "https://example.com/new/feed.xml", 
    "webhook": "https://discord.com/api/webhooks/...",
    "max_articles": 3
  }
]'
```

### 要約のカスタマイズ

`src/summarizer.py`で以下を調整可能：
- プロンプトテンプレート
- 要約の長さ
- 言語設定  
- LM Studioパラメータ

## 🚨 トラブルシューティング

### よくある問題

1. **LM Studioに接続できない**
   - `LM_STUDIO_URL`が正しいか確認
   - LM Studioが起動しているか確認
   - ネットワーク設定を確認

2. **Discord投稿が失敗する**
   - Webhook URLが正しいか確認
   - Discordサーバーの権限を確認

3. **RSSフィードが取得できない**
   - フィードURLが有効か確認
   - ネットワーク接続を確認
   - User-Agentの設定を確認

### ログの確認

Docker実行時：
```bash
docker-compose logs -f rss_bot
```

## 🤝 コントリビューション

1. リポジトリをフォーク
2. 機能ブランチを作成
3. 変更を実装
4. RSSフィードでテスト
5. プルリクエストを送信

## 📄 ライセンス

このプロジェクトはMITライセンスの下で提供されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 🙋 サポート

- バグ報告は[issue](https://github.com/your-username/rss-summarizer-lm/issues)を作成
- 新しいissueを作成する前に既存のissueを確認
- トラブルシューティングの際はログと設定詳細を提供してください