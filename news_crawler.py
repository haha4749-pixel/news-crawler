import feedparser
import hashlib
import re
import html
import requests
from datetime import datetime, timedelta, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# ✅ 사용자 설정
SPREADSHEET_ID = "1XJGb6i7ti-ltoxQ1X3upXKyws1i-I-bQopcddLKbgDc"
WEBHOOK_URL = "https://hook.us2.make.com/u5hkjqysq8xut3ndqekvr5r2e7kcudw8"
KEYWORDS = [
    "피클", "오이피클", "pickles", "피자", "파파존스", "버거킹", "KFC", "맥도날드",
    "쉑쉑버거", "치킨", "삼성웰스토리", "또래오래", "오뚜기", "노랑통닭", "왕비돈까스", "고급양식"
]
EXCLUDE_KEYWORDS = ["피클볼", "치킨게임"]

# ✅ 중복 제거 조건
def is_duplicate(a, b):
    if not a or not b:
        return False
    a_words = set(re.findall(r'\w+', a))
    b_words = set(re.findall(r'\w+', b))
    return len(a_words & b_words) >= 3

# ✅ HTML 정리
def clean_html(text):
    text = re.sub(r"<.*?>", "", text)
    text = html.unescape(text)
    return text.strip()

# ✅ 최근 기사 여부
def is_recent(published_time):
    try:
        dt = datetime(*published_time[:6], tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
        return datetime.now(timezone(timedelta(hours=9))) - dt < timedelta(days=1)
    except:
        return False

# ✅ 뉴스 수집
def fetch_news():
    news_list = []
    for keyword in KEYWORDS:
        url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(url)
        print(f"[INFO] '{keyword}' - {len(feed.entries)}건 수집됨")
        for entry in feed.entries:
            title = clean_html(entry.title)
            summary = clean_html(getattr(entry, "summary", ""))
            if any(k in title or k in summary for k in EXCLUDE_KEYWORDS):
                continue
            if not is_recent(entry.published_parsed):
                continue
            news_list.append({
                "summary": summary,
                "link": entry.link.split("?")[0],
                "date": datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d"),
                "time": datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9))).strftime("%H:%M:%S"),
                "hash": hashlib.sha1(f"{title}{summary}".encode()).hexdigest()
            })
    return news_list

# ✅ 중복 제거
def remove_duplicates(news_list):
    filtered = []
    seen_hashes = set()
    for news in news_list:
        if news["hash"] in seen_hashes:
            continue
        is_dup = False
        for prev in filtered:
            if is_duplicate(news["summary"], prev["summary"]):
                is_dup = True
                break
        if not is_dup:
            filtered.append(news)
            seen_hashes.add(news["hash"])
    print(f"[INFO] 중복 제거 후 최종 뉴스: {len(filtered)}건")
    return filtered

# ✅ Google Sheets 연결
def connect_sheet(sheet_name):
    # GitHub Secrets에서 JSON 가져오기
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        raise Exception("GOOGLE_CREDENTIALS 환경변수가 설정되지 않았습니다")
    
    creds_dict = json.loads(creds_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredent
