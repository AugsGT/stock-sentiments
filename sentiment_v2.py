import feedparser
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from transformers import pipeline
from pymongo import MongoClient
import datetime

# Load FinBERT
print("[INFO] Loading FinBERT model...")
model_name = "yiyanghkust/finbert-tone"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
nlp = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)
print("[INFO] FinBERT ready.\n")

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["stock_sentiment_db"]
collection = db["news_sentiment"]

# List of multiple RSS feeds
rss_feeds = [
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # CNBC Top News
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,GOOG,MSFT&region=US&lang=en-US",  # Yahoo Finance
    "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",  # Reuters
    "https://www.nasdaq.com/feed/rssoutbound",  # Nasdaq
    "https://www.investing.com/rss/news_25.rss",  # Investing.com
]

import socket
socket.setdefaulttimeout(10)  # timeout all socket ops to 10s

for rss_url in rss_feeds:
    print(f"[INFO] Fetching RSS feed: {rss_url}")
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            print("⚠️ No entries found, skipping.\n")
            continue
    except Exception as e:
        print(f"❌ Failed to fetch from {rss_url}: {e}\n")
        continue

    print(f"[DEBUG] Number of entries fetched: {len(feed.entries)}\n")

    for entry in feed.entries[:10]:  # Limit to 10 per feed
        print("📰 Title:", entry.title)

        # Avoid duplicates
        if collection.find_one({"title": entry.title}):
            print("⚠️ Already in DB, skipping.")
            print("-" * 60)
            continue

        try:
            result = nlp(entry.title)[0]
            sentiment_doc = {
                "title": entry.title,
                "link": entry.link,
                "published": entry.get("published", ""),
                "sentiment": result["label"],
                "confidence": float(result["score"]),
                "source": rss_url,
                "timestamp": datetime.datetime.utcnow()
            }
            collection.insert_one(sentiment_doc)
            print("✅ Saved to MongoDB")
        except Exception as e:
            print("❌ Sentiment error:", e)

        print("-" * 60)
