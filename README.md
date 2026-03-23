# 🤖 AI Agent Security Risk Slack Bot

AIエージェント系のセキュリティリスク情報を毎日自動収集してSlackに投稿するボットです。

---

## 収集ソース

| ソース | 内容 |
|--------|------|
| 📰 RSS/ニュース | The Hacker News, Dark Reading, Krebs on Security, OWASP, Google Project Zero, Anthropic, OpenAI |
| 🔴 NIST NVD | AIエージェント・LLM・Prompt Injection 関連 CVE（過去7日分） |
| 🐦 X/Twitter | AI agent / LLM / セキュリティ関連ツイート（Bearer Token 設定時のみ） |

---

## セットアップ

### 1. リポジトリ配置

```bash
git clone <this-repo>
cd ai_security_bot
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. Slack Webhook URL の取得

1. [Slack API](https://api.slack.com/apps) → 「Create New App」
2. 「Incoming Webhooks」を有効化
3. 「Add New Webhook to Workspace」でチャンネルを選択
4. 生成された URL をコピー

### 4. 環境変数の設定

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"

# オプション: NIST API Key（レート制限緩和）
export NIST_API_KEY="your_nist_api_key"

# オプション: Twitter Bearer Token
export TWITTER_BEARER_TOKEN="your_twitter_bearer_token"
```

または `config.py` に直接記入することも可能です。

### 5. 動作確認（手動実行）

```bash
python bot.py
```

---

## 毎日自動実行の設定

### cron（Linux / macOS）

毎朝9時（JST）に実行する例：

```bash
crontab -e
```

以下を追加：

```cron
0 0 * * * cd /path/to/ai_security_bot && SLACK_WEBHOOK_URL="https://..." python bot.py >> /var/log/ai_security_bot.log 2>&1
```

> ※ cron は UTC なので JST 9:00 = UTC 0:00

### GitHub Actions（無料・推奨）

`.github/workflows/daily_bot.yml` を作成：

```yaml
name: AI Security Bot

on:
  schedule:
    - cron: "0 0 * * *"   # 毎日 JST 9:00
  workflow_dispatch:        # 手動実行も可能

jobs:
  run-bot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run bot
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          NIST_API_KEY: ${{ secrets.NIST_API_KEY }}
          TWITTER_BEARER_TOKEN: ${{ secrets.TWITTER_BEARER_TOKEN }}
        run: python bot.py
```

Secrets は GitHub リポジトリの `Settings → Secrets and variables → Actions` で設定。

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

---

## カスタマイズ

### RSS フィードの追加・変更

`config.py` の `RSS_FEEDS` リストに URL を追加するだけです。

```python
RSS_FEEDS = [
    "https://your-favorite-security-blog.com/feed/",
    ...
]
```

### NIST 検索キーワードの変更

```python
NIST_KEYWORDS = [
    "AI agent",
    "LLM",
    "prompt injection",   # ← 変更・追加可能
]
```

### 取得件数の調整

```python
MAX_ITEMS_PER_SOURCE = 5  # 1ソースあたりの最大件数
```

---

## ファイル構成

```
ai_security_bot/
├── bot.py            # メインスクリプト
├── config.py         # 設定ファイル
├── requirements.txt  # 依存パッケージ
├── seen_items.json   # 既出アイテムID（自動生成・重複防止）
└── README.md         # このファイル
```

---

## 注意事項

- Twitter API v2 の無料プランは検索に制限があります（月100件程度）。有料プランを推奨。
- NIST NVD API は API Key なしで 1リクエスト/6秒 の制限があります。`NIST_API_KEY` 設定で緩和されます。
- `seen_items.json` は実行のたびに更新され、一度投稿した記事は再投稿されません。
