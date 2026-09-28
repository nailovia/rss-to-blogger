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
    "AQ.Ab8RN6KP2hoh_Rj4FjBonqFRdHn-3p6WO4G2__5cLf601NDtcg",
    "AQ.Ab8RN6KWBEjkqJWrZ_HvC2sOU4mhCP4pzBw3VSOu4ICptv1kVw",
    "AQ.Ab8RN6KWBEjkqJWrZ_HvC2sOU4mhCP4pzBw3VSOu4ICptv1kVw",
    "AQ.Ab8RN6LR_8VXxuwj8NHoUqJNOwp63zLuGXBshWAkkc9mEKuuow",
    "AQ.Ab8RN6I_eq23_pwzQEfxt3hvbAdtZwPZFMPLqrVSsnCUUtMLHg",
    "AQ.Ab8RN6Iah04pShp5wYpU-ZS6jd28oEYRtQr3Gl4nRY3RXkYAUw",
    "AQ.Ab8RN6LbEcWl4XTeAginoJWs6kyjbbA3A9bRPSyJlhHLhXJqlQ"
]
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-flash-latest",
]
# Nayi Feeds (Express News) aur unki Categories
FEEDS = {
    "Pakistan": "https://www.express.pk/pakistan/feed/",
    "World": "https://www.express.pk/world/feed/",
    "Sports": "https://www.express.pk/sports/feed/",
    "Business": "https://www.express.pk/business/feed/",
    "Science": "https://www.express.pk/science/feed/",
    "Entertainment": "https://www.express.pk/feed/saqafat",
     "Health": "https://www.express.pk/feed/health",
"Jobs": "https://ntslogin.pk/feed/",
}

POSTED_URLS_FILE = "posted_urls.txt"
POSTED_URLS_FILE = "posted_urls.txt"
POSTED_TITLES_FILE = "posted_titles.txt"   # NEW
POSTED_IMAGES_FILE = "posted_images.txt"   # NEW
# Blogger API Credentials (Apne Client ID aur Tokens yahan wapas paste karein)
CLIENT_ID = "406814434519-vj8a3i4b1e38n6b239pi2lf9o6tfhh37.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REFRESH_TOKEN = "1//04-7k2XcVtLUYCgYIARAAGAQSNwF-L9Ird9g7RNp9rc534rQtF0P61DpiqU6MyHqdmTnJcoi_ObYp7eDgB8TXiEbNr8AQYCdxof4" 
BLOG_ID = "3423631024307035197"
# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_set_from_file(filename):
    """Generic function - kisi bhi file se set load karein"""
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_file(filename, value):
    """Generic function - kisi bhi file mein ek line append karein"""
    with open(filename, "a", encoding="utf-8") as f:
        f.write(value + "\n")

def load_posted_urls():
    return load_set_from_file(POSTED_URLS_FILE)

def load_posted_titles():
    return load_set_from_file(POSTED_TITLES_FILE)

def load_posted_images():
    return load_set_from_file(POSTED_IMAGES_FILE)

def save_posted_url(url):
    save_to_file(POSTED_URLS_FILE, url)

def save_posted_title(title):
    save_to_file(POSTED_TITLES_FILE, title)

def save_posted_image(image_url):
    save_to_file(POSTED_IMAGES_FILE, image_url)

def normalize_title(title):
    """Title ko normalize karein - extra spaces, punctuation hata kar lowercase"""
    title = re.sub(r'[^\w\s\u0600-\u06FF]', '', title)  # Sirf Urdu/Arabic letters, numbers, spaces rakhein
    title = re.sub(r'\s+', ' ', title).strip().lower()
    return title

WORKING_MODEL = None

def get_gemini_response(prompt):
    # Pehle models, phir keys
    for model in GEMINI_MODELS:
        print(f"🔄 Trying model: {model}")
        for key in GEMINI_API_KEYS:
            key = key.strip()
            if not key or key.startswith("Key"):
                continue
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                headers = {'Content-Type': 'application/json'}
                data = {"contents": [{"parts": [{"text": prompt}]}]}
                
                response = requests.post(url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and result['candidates']:
                        print(f"✅ Success with {model} using key ending ...{key[-6:]}")
                        return result['candidates'][0]['content']['parts'][0]['text'].strip()
                elif response.status_code == 429:
                    print(f"⚠️ Quota khatam: {model} key ...{key[-6:]}")
                else:
                    print(f"⚠️ {model} key ...{key[-6:]} failed: {response.status_code}")
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ Network error: {e}")
                time.sleep(1)
    print("❌ Saare models aur keys fail ho gaye.")
    return None

def process_content_with_ai(urdu_title, original_content):
    # Slug skip (Blogger khud bana lega)
    slug = ""
    
    # Sirf content rewrite
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
        return True     # ✅ Success
    except Exception as e:
        print(f"❌ Blogger Post Error: {e}")
        return False    # ❌ Fail

# ==========================================
# MAIN EXECUTION
# ==========================================

def fetch_and_post_news():
    print("🚀 Auto Blogger Script Started!")
    posted_urls = load_posted_urls()
    posted_titles = load_posted_titles()
    posted_images = load_posted_images()
    print(f"📂 Pehle se post shuda URLs: {len(posted_urls)} | Titles: {len(posted_titles)} | Images: {len(posted_images)}")

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
            news_title = entry.title
            
            # ✅ CHECK 1: URL repeat
            if news_link in posted_urls:
                print(f"⏩ Skipping (URL Already Posted): {news_title}")
                continue
            
            # ✅ CHECK 2: Title repeat (normalized)
            normalized_title = normalize_title(news_title)
            if normalized_title in posted_titles:
                print(f"⏩ Skipping (Same Title Already Posted): {news_title}")
                continue
            
            raw_content = entry.content[0].value if 'content' in entry else entry.summary
            soup = BeautifulSoup(raw_content, 'html.parser')
            img_tag = soup.find('img')
            
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
                print(f"🚫 Skipping (No Image Found anywhere): {news_title}")
                continue
            
            # ✅ CHECK 3: Image repeat
            img_src = img_tag.get('src', '')
            if img_src and img_src in posted_images:
                print(f"⏩ Skipping (Same Thumbnail Already Posted): {news_title}")
                continue
            
            clean_text = soup.get_text(separator="\n").strip()
            
            print(f"✍️ Processing with AI: {news_title}")
            slug, rewritten_urdu = process_content_with_ai(news_title, clean_text)
            
            if not rewritten_urdu:
                print("❌ Skipping: AI failed to rewrite content.")
                continue 
                
            image_html = str(img_tag)
            final_html_content = f"{image_html}<br><br><p>{rewritten_urdu}</p><br><br><p><em>News Source: Express News</em></p>"
            
            print(f"🌐 Ready to Post -> Label: {category_label} | Slug: {slug}")
            success = post_to_blogger(news_title, final_html_content, [category_label])
            
            # ✅ Sirf tab save karein jab post successfully publish ho
            if success:
                save_posted_url(news_link)
                save_posted_title(normalized_title)
                if img_src:
                    save_posted_image(img_src)
                print("💾 Data saved (URL, Title, Image)")
            else:
                print("⚠️ Post fail hua - kuch bhi save nahi kiya")
            
            print("-" * 50)
            break


if __name__ == "__main__":
    fetch_and_post_news()
    print("🏁 Script Finished Successfully!")
