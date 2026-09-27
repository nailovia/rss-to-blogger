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

    # Website ko dhoka dene ke liye Chrome browser ka User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }

    for feed_url in FEEDS:
        print(f"\n🔍 Checking feed: {feed_url}")
        category_label = feed_url.split('.com/')[1].split('/feed')[0].lower()
        
        try:
            # Pehle feed ka data browser ban kar download karo
            feed_response = requests.get(feed_url, headers=headers, timeout=15)
            parsed_feed = feedparser.parse(feed_response.content)
        except Exception as e:
            print(f"⚠️ Feed block ho gayi ya network error: {e}")
            continue

        print(f"✅ Found {len(parsed_feed.entries)} articles in this feed.")
        
        for entry in parsed_feed.entries:
            news_link = entry.link
            
            if news_link in posted_urls:
                print(f"⏩ Skipping (Already Posted): {entry.title}")
                continue
            
            raw_content = entry.content[0].value if 'content' in entry else entry.summary
            soup = BeautifulSoup(raw_content, 'html.parser')
            
            # Pehle feed mein image check karega
            img_tag = soup.find('img')
            
            # Agar feed mein image nahi mili, to website ke link se image uthayega
            if not img_tag:
                try:
                    article_req = requests.get(news_link, headers=headers, timeout=10)
                    article_soup = BeautifulSoup(article_req.text, 'html.parser')
                    meta_img = article_soup.find('meta', property='og:image')
                    
                    if meta_img and meta_img.get('content'):
                        img_url = meta_img['content']
                        img_tag = BeautifulSoup(f"<img src='{img_url}' alt='Daily Ausaf News' />", 'html.parser').img
                except Exception as e:
                    print(f"Error extracting image from website: {e}")

            # Agar website se bhi image na mili, phir skip kar dega
            if not img_tag:
                print(f"🚫 Skipping (No Image Found anywhere): {entry.title}")
                continue
            
            clean_text = soup.get_text(separator="\n").strip()
            
            print(f"✍️ Processing with AI: {entry.title}")
            slug, rewritten_urdu = process_content_with_ai(entry.title, clean_text)
            
            if not rewritten_urdu:
                print("❌ Skipping: AI failed to rewrite content.")
                continue 
                
            image_html = str(img_tag)
            final_html_content = f"{image_html}<br><br><p>{rewritten_urdu}</p><br><br><p><em>Image Credit: Daily Ausaf</em></p>"
            
            print(f"🌐 Ready to Post -> Label: {category_label} | Slug: {slug}")
            post_to_blogger(entry.title, final_html_content, [category_label])
            
            save_posted_url(news_link)
            print("-" * 50)

if __name__ == "__main__":
    fetch_and_post_news()
    print("🏁 Script Finished Successfully!")
