import feedparser
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from pymongo import MongoClient
import datetime
import schedule
import time
import socket

# Set timeout for slow feeds
socket.setdefaulttimeout(10)

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

# List of RSS feeds
rss_feeds = [
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,GOOG,MSFT&region=US&lang=en-US",
    "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
    "https://www.investing.com/rss/news_25.rss",
]

def fetch_and_analyze():
    print(f"\n[RUN] Starting fetch cycle at {datetime.datetime.utcnow()}\n")

    for rss_url in rss_feeds:
        print(f"[INFO] Fetching RSS feed: {rss_url}")
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                print("⚠️ No entries found, skipping.")
                continue
        except Exception as e:
            print(f"❌ Failed to fetch from {rss_url}: {e}")
            continue

        for entry in feed.entries[:10]:  # limit per feed
            title = entry.title

            # Check for duplicate
            if collection.find_one({"title": title}):
                print(f"⚠️ Already in DB: {title}")
                continue

            try:
                result = nlp(title)[0]
                sentiment_doc = {
                    "title": title,
                    "link": entry.link,
                    "published": entry.get("published", ""),
                    "sentiment": result["label"],
                    "confidence": float(result["score"]),
                    "source": rss_url,
                    "timestamp": datetime.datetime.utcnow()
                }
                collection.insert_one(sentiment_doc)
                print(f"✅ Saved: {title}")
            except Exception as e:
                print("❌ Sentiment error:", e)

        print("-" * 60)

# Schedule the job every 10 minutes
schedule.every(10).minutes.do(fetch_and_analyze)

print("[INFO] Scheduler started. Running every 10 minutes.\n")

# Initial run
fetch_and_analyze()

while True:
    schedule.run_pending()
    time.sleep(1)
