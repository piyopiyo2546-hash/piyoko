"""
設定ファイル — 環境変数 or ここで直接編集
"""
import os

# ─────────────────────────────────────────
# Slack Webhook URL（必須）
# 環境変数 SLACK_WEBHOOK_URL を優先、なければここに直接記入
# ─────────────────────────────────────────
SLACK_WEBHOOK_URL = os.getenv(
    "SLACK_WEBHOOK_URL",
    ""  # ← ここに貼り付けても OK: "https://hooks.slack.com/services/XXX/YYY/ZZZ"
)

# ─────────────────────────────────────────
# RSS フィード一覧（AIエージェント・セキュリティ系）
# ─────────────────────────────────────────
RSS_FEEDS = [
    # The Hacker News - AI & Security
    "https://feeds.feedburner.com/TheHackersNews",
    # Dark Reading
    "https://www.darkreading.com/rss.xml",
    # Krebs on Security
    "https://krebsonsecurity.com/feed/",
    # OWASP Blog
    "https://owasp.org/feed.xml",
    # Google Project Zero
    "https://googleprojectzero.blogspot.com/feeds/posts/default",
    # Anthropic News
    "https://www.anthropic.com/news/rss",
    # OpenAI Blog
    "https://openai.com/blog/rss.xml",
]

# ─────────────────────────────────────────
# NIST NVD API
# ─────────────────────────────────────────
NIST_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

# 検索キーワード（AIエージェント関連 CVE を狙い撃ち）
NIST_KEYWORDS = [
    "AI agent",
    "LLM",
    "prompt injection",
    "RAG",
    "model security",
]

# NIST API Key（任意。設定するとレート制限が緩和される）
# https://nvd.nist.gov/developers/request-an-api-key
NIST_API_KEY = os.getenv("NIST_API_KEY", "")

# ─────────────────────────────────────────
# X/Twitter API v2（任意）
# Bearer Token がなければ Twitter 収集はスキップ
# ─────────────────────────────────────────
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")

TWITTER_SEARCH_QUERY = (
    "(AI agent OR LLM OR \"prompt injection\" OR \"agentic AI\") "
    "(security OR vulnerability OR attack OR hijack OR exploit) "
    "-is:retweet lang:en"
)

# ─────────────────────────────────────────
# 共通設定
# ─────────────────────────────────────────
# 1ソースあたりの最大取得件数
MAX_ITEMS_PER_SOURCE = 5

# 既出アイテムIDの保存先（重複投稿防止）
SEEN_ITEMS_FILE = "seen_items.json"

# ログレベル: DEBUG / INFO / WARNING / ERROR
LOG_LEVEL = "INFO"
