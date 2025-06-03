import streamlit as st
from pymongo import MongoClient
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["stock_sentiment_db"]
collection = db["news_sentiment"]

st.set_page_config(page_title="📈 Stock Sentiment", layout="wide")
st.title("📉 Stock News Sentiment Dashboard")

# Refresh every 30 seconds
st_autorefresh(interval=30000, key="refresh")


# Fetch latest 30 entries
data = list(collection.find().sort("timestamp", -1).limit(30))

# Convert to DataFrame
df = pd.DataFrame(data)

if df.empty:
    st.warning("No data found. Run the scheduler first.")
else:
    df["timestamp"] = df["timestamp"].dt.strftime('%Y-%m-%d %H:%M:%S')
    df = df[["timestamp", "title", "sentiment", "confidence", "link"]]

    def color_sentiment(val):
        if val == "positive":
            return "background-color: #68d10d"
        elif val == "negative":
            return "background-color: #c21313"
        else:
            return "background-color: #d9cc14"

    st.dataframe(
        df.style.applymap(color_sentiment, subset=["sentiment"]),
        height=600
    )

    st.caption("Data auto-refreshes. Source: multiple RSS feeds.")

