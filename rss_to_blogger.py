import feedparser
import os
import re
import time
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# ==========================================
# CONFIGURATIONS (Yahan Apni Details Daalein)
# ==========================================

# Apni 10 Gemini API keys yahan lagayen
GEMINI_API_KEYS = [
    "AQ.Ab8RN6JAcflDfIzmyvIJvxitac_5ryC5sCszEFP-sdQZHk0jhg", 
    "AQ.Ab8RN6KOn9OKY5PRb-B6n9klJ_CpoCQWhbmQZRGD3lVVgwx26w", 
    "AQ.Ab8RN6LXlpWMpvz8vegzY8pb3xpdFyuQX2HruwWx_XC3_7cBTg",
    "Key4",
    "Key5",
    "Key6",
    "Key7",
    "Key8",
    "Key9",
    "Key10"
]

# Daily Ausaf ki RSS Feeds
FEEDS = [
    "https://dailyausaf.com/pakistan/feed/",
    "https://dailyausaf.com/world/feed/",
    "https://dailyausaf.com/sports/feed/",
    "https://dailyausaf.com/showbiz/feed/",
    "https://dailyausaf.com/business/feed/",
    "https://dailyausaf.com/interesting-news/feed/",
    "https://dailyausaf.com/science-health/feed/",
    "https://dailyausaf.com/technology/feed/"
]

POSTED_URLS_FILE = "posted_urls.txt"

# Blogger API Credentials (Yahan apne credentials daalein)
CLIENT_ID = "406814434519-vj8a3i4b1e38n6b239pi2lf9o6tfhh37.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REFRESH_TOKEN = "1//04-7k2XcVtLUYCgYIARAAGAQSNwF-L9Ird9g7RNp9rc534rQtF0P61DpiqU6MyHqdmTnJcoi_ObYp7eDgB8TXiEbNr8AQYCdxof4" 
BLOG_ID = "3423631024307035197"

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_posted_urls():
    if os.path.exists(POSTED_URLS_FILE):
        with open(POSTED_URLS_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_posted_url(url):
    with open(POSTED_URLS_FILE, "a") as f:
        f.write(url + "\n")

def get_gemini_response(prompt):
    for key in GEMINI_API_KEYS:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            if response.text:
                return response.text.strip()
        except Exception as e:
            print(f"⚠️ Key failed, trying next... Error: {e}")
            time.sleep(2)
    return None

def process_content_with_ai(urdu_title, original_content):
    # 1. English Slug Generate Karna
    slug_prompt = f"Translate this Urdu title to English. Return ONLY the English translation without any extra words or quotes: {urdu_title}"
    english_title = get_gemini_response(slug_prompt)
    
    if english_title:
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', english_title).strip().replace(' ', '-').lower()
    else:
        slug = ""

    # 2. Suspenseful aur To-The-Point Urdu mein Rewrite Karna
    rewrite_prompt = f"Rewrite this news article in Urdu. Keep it to the point, engaging, and create suspense. Do not change the core real-time facts. Only provide the rewritten Urdu text without any markdown or extra text. Here is the news:\n\n{original_content}"
    urdu_rewritten_content = get_gemini_response(rewrite_prompt)

    return slug, urdu_rewritten_content

# ==========================================
# MAIN EXECUTION
# ==========================================
import requests

def fetch_and_post_news():
    print("🚀 Auto Blogger Script Started!")
    posted_urls = load_posted_urls()
    print(f"📂 Pehle se post shuda URLs ki tadad: {len(posted_urls)}")

    for feed_url in FEEDS:
        print(f"\n🔍 Checking feed: {feed_url}")
        category_label = feed_url.split('.com/')[1].split('/feed')[0].lower()
        
        try:
            # GitHub IP Block se bachne ke liye Free RSS Proxy ka istemal
            api_url = f"https://api.rss2json.com/v1/api.json?rss_url={feed_url}"
            res = requests.get(api_url, timeout=15)
            data = res.json()
            articles = data.get("items", [])
        except Exception as e:
            print(f"⚠️ Feed error: {e}")
            continue

        print(f"✅ Found {len(articles)} articles in this feed.")
        
        for entry in articles:
            news_link = entry.get("link", "")
            title = entry.get("title", "")
            
            if news_link in posted_urls:
                print(f"⏩ Skipping (Already Posted): {title}")
                continue
            
            raw_content = entry.get("content", "")
            if not raw_content:
                raw_content = entry.get("description", "")
                
            soup = BeautifulSoup(raw_content, 'html.parser')
            img_tag = soup.find('img')
            
            # Agar feed mein image na mile to original website se uthaye
            if not img_tag:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    article_req = requests.get(news_link, headers=headers, timeout=10)
                    article_soup = BeautifulSoup(article_req.text, 'html.parser')
                    meta_img = article_soup.find('meta', property='og:image')
                    if meta_img and meta_img.get('content'):
                        img_url = meta_img['content']
                        img_tag = BeautifulSoup(f"<img src='{img_url}' alt='Daily Ausaf News' />", 'html.parser').img
                except:
                    pass

            if not img_tag:
                print(f"🚫 Skipping (No Image Found anywhere): {title}")
                continue
            
            clean_text = soup.get_text(separator="\n").strip()
            
            print(f"✍️ Processing with AI: {title}")
            slug, rewritten_urdu = process_content_with_ai(title, clean_text)
            
            if not rewritten_urdu:
                print("❌ Skipping: AI failed to rewrite content.")
                continue 
                
            image_html = str(img_tag)
            final_html_content = f"{image_html}<br><br><p>{rewritten_urdu}</p><br><br><p><em>Image Credit: Daily Ausaf</em></p>"
            
            print(f"🌐 Ready to Post -> Label: {category_label} | Slug: {slug}")
            post_to_blogger(title, final_html_content, [category_label])
            
            save_posted_url(news_link)
            print("-" * 50)

if __name__ == "__main__":
    fetch_and_post_news()
    print("🏁 Script Finished Successfully!")
