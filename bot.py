"""
AI Agent Security Risk Slack Bot
毎日1回、AIエージェント系セキュリティリスク情報を収集してSlackに投稿する
"""

import json
import time
import logging
import hashlib
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import feedparser
from bs4 import BeautifulSoup

from config import (
    SLACK_WEBHOOK_URL,
    RSS_FEEDS,
    NIST_API_URL,
    NIST_KEYWORDS,
    TWITTER_BEARER_TOKEN,
    TWITTER_SEARCH_QUERY,
    MAX_ITEMS_PER_SOURCE,
    SEEN_ITEMS_FILE,
    LOG_LEVEL,
)

# ─────────────────────────────────────────
# Logging
# ─────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────
# 既出アイテム管理（重複投稿防止）
# ─────────────────────────────────────────
def load_seen_ids() -> set:
    if Path(SEEN_ITEMS_FILE).exists():
        with open(SEEN_ITEMS_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen_ids(seen: set):
    with open(SEEN_ITEMS_FILE, "w") as f:
        json.dump(list(seen), f)


def item_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


# ─────────────────────────────────────────
# ソース 1: RSS フィード
# ─────────────────────────────────────────
def fetch_rss(seen: set) -> list[dict]:
    results = []
    for feed_url in RSS_FEEDS:
        log.info(f"RSS取得中: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:MAX_ITEMS_PER_SOURCE]:
                uid = item_id(entry.get("link", entry.get("title", "")))
                if uid in seen:
                    continue
                title = entry.get("title", "(タイトルなし)")
                link = entry.get("link", "")
                summary = BeautifulSoup(
                    entry.get("summary", ""), "html.parser"
                ).get_text()[:200]
                published = entry.get("published", "")
                results.append(
                    {
                        "uid": uid,
                        "source": "📰 ニュース/RSS",
                        "title": title,
                        "url": link,
                        "summary": summary,
                        "date": published,
                    }
                )
        except Exception as e:
            log.warning(f"RSS取得失敗 {feed_url}: {e}")
    return results


# ─────────────────────────────────────────
# ソース 2: NIST NVD (CVE / AI関連キーワード)
# ─────────────────────────────────────────
def fetch_nist(seen: set) -> list[dict]:
    results = []
    today = datetime.now(timezone.utc)
    pub_start = (today - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00.000")
    pub_end = today.strftime("%Y-%m-%dT23:59:59.999")

    for keyword in NIST_KEYWORDS:
        log.info(f"NIST NVD検索中: {keyword}")
        try:
            params = {
                "keywordSearch": keyword,
                "pubStartDate": pub_start,
                "pubEndDate": pub_end,
                "resultsPerPage": MAX_ITEMS_PER_SOURCE,
            }
            resp = requests.get(NIST_API_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for vuln in data.get("vulnerabilities", []):
                cve = vuln.get("cve", {})
                cve_id = cve.get("id", "")
                uid = item_id(cve_id)
                if uid in seen:
                    continue
                descriptions = cve.get("descriptions", [])
                desc_en = next(
                    (d["value"] for d in descriptions if d["lang"] == "en"), ""
                )[:200]
                link = f"https://nvd.nist.gov/vuln/detail/{cve_id}"
                published = cve.get("published", "")[:10]
                score = ""
                metrics = cve.get("metrics", {})
                if metrics.get("cvssMetricV31"):
                    score = metrics["cvssMetricV31"][0]["cvssData"].get(
                        "baseScore", ""
                    )
                elif metrics.get("cvssMetricV30"):
                    score = metrics["cvssMetricV30"][0]["cvssData"].get(
                        "baseScore", ""
                    )
                title = f"{cve_id}" + (f" (CVSS: {score})" if score else "")
                results.append(
                    {
                        "uid": uid,
                        "source": "🔴 NIST NVD",
                        "title": title,
                        "url": link,
                        "summary": desc_en,
                        "date": published,
                    }
                )
        except Exception as e:
            log.warning(f"NIST取得失敗 ({keyword}): {e}")
        time.sleep(0.6)  # NVD rate limit: 5 req/30s (without API key)
    return results


# ─────────────────────────────────────────
# ソース 3: X/Twitter (Bearer Token 必要)
# ─────────────────────────────────────────
def fetch_twitter(seen: set) -> list[dict]:
    if not TWITTER_BEARER_TOKEN:
        log.info("Twitter Bearer Token未設定のためスキップ")
        return []

    results = []
    log.info("Twitter検索中...")
    try:
        headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
        params = {
            "query": TWITTER_SEARCH_QUERY,
            "max_results": MAX_ITEMS_PER_SOURCE,
            "tweet.fields": "created_at,author_id,text",
            "expansions": "author_id",
            "user.fields": "username",
        }
        resp = requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # ユーザー名マップ
        users = {
            u["id"]: u["username"]
            for u in data.get("includes", {}).get("users", [])
        }

        for tweet in data.get("data", []):
            uid = item_id(tweet["id"])
            if uid in seen:
                continue
            username = users.get(tweet.get("author_id", ""), "unknown")
            text = tweet.get("text", "")[:200]
            link = f"https://twitter.com/{username}/status/{tweet['id']}"
            date = tweet.get("created_at", "")[:10]
            results.append(
                {
                    "uid": uid,
                    "source": "🐦 X/Twitter",
                    "title": f"@{username}",
                    "url": link,
                    "summary": text,
                    "date": date,
                }
            )
    except Exception as e:
        log.warning(f"Twitter取得失敗: {e}")
    return results


# ─────────────────────────────────────────
# Slack 投稿
# ─────────────────────────────────────────
def build_slack_message(items: list[dict]) -> dict:
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y年%m月%d日")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🤖 AIエージェント セキュリティリスク情報 — {today}",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*{len(items)}件* の新着情報 | ソース: RSS/ニュース・NIST NVD・X/Twitter",
                }
            ],
        },
        {"type": "divider"},
    ]

    if not items:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "✅ 本日の新着情報はありませんでした。",
                },
            }
        )
        return {"blocks": blocks}

    # ソースごとにグループ化
    grouped: dict[str, list] = {}
    for item in items:
        grouped.setdefault(item["source"], []).append(item)

    for source, source_items in grouped.items():
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{source}*"},
            }
        )
        for item in source_items:
            date_str = f"  _{item['date']}_" if item["date"] else ""
            summary = item["summary"].strip().replace("\n", " ")
            text = (
                f"*<{item['url']}|{item['title']}>*{date_str}\n"
                f"{summary}{'…' if len(item['summary']) >= 200 else ''}"
            )
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": text}}
            )
        blocks.append({"type": "divider"})

    return {"blocks": blocks}


def post_to_slack(message: dict):
    log.info("Slackに投稿中...")
    resp = requests.post(
        SLACK_WEBHOOK_URL,
        json=message,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Slack投稿失敗: {resp.status_code} {resp.text}")
    log.info("Slack投稿完了")


# ─────────────────────────────────────────
# メイン
# ─────────────────────────────────────────
def main():
    log.info("=== AI Security Bot 起動 ===")

    if not SLACK_WEBHOOK_URL:
        log.error("SLACK_WEBHOOK_URL が設定されていません。終了します。")
        return

    seen = load_seen_ids()

    # 各ソースから収集
    all_items: list[dict] = []
    all_items.extend(fetch_rss(seen))
    all_items.extend(fetch_nist(seen))
    all_items.extend(fetch_twitter(seen))

    log.info(f"新着アイテム数: {len(all_items)}")

    # Slack投稿
    message = build_slack_message(all_items)
    post_to_slack(message)

    # 既出IDを更新
    for item in all_items:
        seen.add(item["uid"])
    save_seen_ids(seen)

    log.info("=== 完了 ===")


if __name__ == "__main__":
    main()
