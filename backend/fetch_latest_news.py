import os
import yfinance as yf
import json
from config import *
from datetime import datetime
import boto3


AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "fetch-latest-news")

def clean_time(news):
    for item in news:
        timestamp = item['providerPublishTime']
        datetime_object = datetime.fromtimestamp(timestamp)
        item['publishTime'] = datetime_object.strftime("%Y-%m-%d %H:%M:%S")
    return news





def fetch_news(ticker):
    stock = yf.Ticker(ticker)
    news = stock.get_news()
    return news



def main():
    all_news = []
    for ticker in selected_symbols:
        ticker_news = fetch_news(ticker)
        ticker_news = clean_time(ticker_news)
        all_news.extend(ticker_news)

    news_sorted = sorted(all_news, key=lambda x: x['providerPublishTime'], reverse=True)
    latest_articles = news_sorted[:4]

    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)


    news_json = json.dumps(latest_articles)
    s3.put_object(Bucket=S3_BUCKET_NAME, Key='latest_articles.json', Body=news_json)
    #print(news_json)

    # return {
    #     'statusCode': 200,
    #     'body': news_json
    # }

if __name__ == '__main__':
    main()
