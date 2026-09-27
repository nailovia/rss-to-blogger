import feedparser
import os
import re
import time
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ==========================================
# CONFIGURATIONS (Yahan Apni Details Daalein)
# ==========================================

# Apni 10 Gemini API keys yahan lagayen (Security ke liye maine aapki keys hata di hain, unhein yahan paste karein)
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

# Nayi Feeds (Express News) aur unki Categories
FEEDS = {
    "Pakistan": "https://www.express.pk/pakistan/feed/",
    "World": "https://www.express.pk/world/feed/",
    "Sports": "https://www.express.pk/sports/feed/",
    "Business": "https://www.express.pk/business/feed/",
    "Science": "https://www.express.pk/science/feed/"
}

POSTED_URLS_FILE = "posted_urls.txt"

# Blogger API Credentials (Apne Client ID aur Tokens yahan wapas paste karein)
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

WORKING_MODEL = None

def get_gemini_response(prompt):
    for key in GEMINI_API_KEYS:
        if key.startswith("Key") or "YOUR_" in key:
            continue
        try:
            # Stable aur tested endpoint with gemini-1.5-flash
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={key}"
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text'].strip()
            else:
                print(f"⚠️ Key failed (Status {response.status_code}: {response.text}). Trying next...")
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Network error with key: {e}")
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

def post_to_blogger(title, content, labels_list):
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    try:
        service = build('blogger', 'v3', credentials=creds)
        body = {
            "title": title,
            "content": content,
            "labels": labels_list
        }
        posts = service.posts()
        res = posts.insert(blogId=BLOG_ID, body=body, isDraft=False).execute()
        print(f"✅ Post Published Successfully! Link: {res.get('url')}")
    except Exception as e:
        print(f"❌ Blogger Post Error: {e}")

# ==========================================
# MAIN EXECUTION
# ==========================================

def fetch_and_post_news():
    print("🚀 Auto Blogger Script Started!")
    posted_urls = load_posted_urls()
    print(f"📂 Pehle se post shuda URLs ki tadad: {len(posted_urls)}")

    # GitHub Actions ko block hone se bachanay ke liye Chrome header
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36'}

    for category_label, feed_url in FEEDS.items():
        print(f"\n🔍 Checking feed: {feed_url} (Category: {category_label})")
        
        try:
            feed_response = requests.get(feed_url, headers=headers, timeout=15)
            parsed_feed = feedparser.parse(feed_response.content)
        except Exception as e:
            print(f"⚠️ Feed error: {e}")
            continue

        print(f"✅ Found {len(parsed_feed.entries)} articles in this feed.")
        
        for entry in parsed_feed.entries:
            news_link = entry.link
            
            if news_link in posted_urls:
                print(f"⏩ Skipping (Already Posted): {entry.title}")
                continue
            
            raw_content = entry.content[0].value if 'content' in entry else entry.summary
            soup = BeautifulSoup(raw_content, 'html.parser')
            img_tag = soup.find('img')
            
            # Agar feed mein image na mile to original website se uthaye
            if not img_tag:
                try:
                    article_req = requests.get(news_link, headers=headers, timeout=10)
                    article_soup = BeautifulSoup(article_req.text, 'html.parser')
                    meta_img = article_soup.find('meta', property='og:image')
                    if meta_img and meta_img.get('content'):
                        img_url = meta_img['content']
                        img_tag = BeautifulSoup(f"<img src='{img_url}' alt='News Image' />", 'html.parser').img
                except:
                    pass

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
            final_html_content = f"{image_html}<br><br><p>{rewritten_urdu}</p><br><br><p><em>News Source: Express News</em></p>"
            
            print(f"🌐 Ready to Post -> Label: {category_label} | Slug: {slug}")
            post_to_blogger(entry.title, final_html_content, [category_label])
            
            save_posted_url(news_link)
            print("-" * 50)
            
            # Ek category se sirf 1 post karega taake Blogger spam mein na daale
            break

if __name__ == "__main__":
    fetch_and_post_news()
    print("🏁 Script Finished Successfully!")
