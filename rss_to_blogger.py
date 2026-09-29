import feedparser
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ==========================================
# CONFIGURATIONS
# ==========================================

# Gemini
GEMINI_API_KEYS = os.environ.get("GEMINI_API_KEYS", "").split(",")
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
]

# Groq
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# OpenRouter
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

# Blogger
CLIENT_ID = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN", "")
BLOG_ID = os.environ.get("BLOG_ID", "")
YOUR_BLOG_URL = os.environ.get("BLOG_URL", "https://yourbolt.blogspot.com")

# Feeds
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
POSTED_TITLES_FILE = "posted_titles.txt"
POSTED_IMAGES_FILE = "posted_images.txt"

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_set_from_file(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_file(filename, value):
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
    title = re.sub(r'[^\w\s\u0600-\u06FF]', '', title)
    title = re.sub(r'\s+', ' ', title).strip().lower()
    return title

# ==========================================
# GEMINI FUNCTION
# ==========================================

def get_gemini_response(prompt):
    for model in GEMINI_MODELS:
        print("🔄 Gemini trying: " + model)
        for key in GEMINI_API_KEYS:
            key = key.strip()
            if not key:
                continue
            try:
                url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent?key=" + key
                headers = {'Content-Type': 'application/json'}
                data = {"contents": [{"parts": [{"text": prompt}]}]}
                response = requests.post(url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and result['candidates']:
                        print("✅ Gemini success: " + model)
                        return result['candidates'][0]['content']['parts'][0]['text'].strip()
                elif response.status_code == 429:
                    print("⚠️ Gemini quota khatam: " + model)
                else:
                    print("⚠️ Gemini " + model + " failed: " + str(response.status_code))
                time.sleep(1)
            except Exception as e:
                print("⚠️ Gemini network error: " + str(e))
                time.sleep(1)
    print("❌ Gemini saare fail.")
    return None

# ==========================================
# GROQ FUNCTION
# ==========================================

def get_groq_response(prompt):
    if not GROQ_API_KEY:
        print("⚠️ Groq key nahi hai. Skip.")
        return None
    
    print("🔄 Groq trying: " + GROQ_MODEL)
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": "Bearer " + GROQ_API_KEY,
            "Content-Type": "application/json"
        }
        data = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            print("✅ Groq success: " + GROQ_MODEL)
            return content
        elif response.status_code == 429:
            print("⚠️ Groq quota khatam.")
        else:
            print("⚠️ Groq failed: " + str(response.status_code))
    except Exception as e:
        print("⚠️ Groq network error: " + str(e))
    return None

# ==========================================
# OPENROUTER FUNCTION
# ==========================================

def get_openrouter_response(prompt):
    if not OPENROUTER_API_KEY:
        print("⚠️ OpenRouter key nahi hai. Skip.")
        return None
    
    print("🔄 OpenRouter trying: " + OPENROUTER_MODEL)
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": "Bearer " + OPENROUTER_API_KEY,
            "Content-Type": "application/json",
            "HTTP-Referer": YOUR_BLOG_URL,
            "X-Title": "YourBolt News"
        }
        data = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            print("✅ OpenRouter success: " + OPENROUTER_MODEL)
            return content
        elif response.status_code == 429:
            print("⚠️ OpenRouter quota khatam.")
        else:
            print("⚠️ OpenRouter failed: " + str(response.status_code))
    except Exception as e:
        print("⚠️ OpenRouter network error: " + str(e))
    return None

# ==========================================
# MASTER AI FUNCTION (Fallback Chain)
# ==========================================

def get_ai_response(prompt):
    print("=" * 50)
    print("🔄 Step 1: Gemini")
    response = get_gemini_response(prompt)
    if response:
        return response
    
    print("🔄 Step 2: Groq")
    response = get_groq_response(prompt)
    if response:
        return response
    
    print("🔄 Step 3: OpenRouter")
    response = get_openrouter_response(prompt)
    if response:
        return response
    
    print("❌ Saare providers fail ho gaye.")
    return None

def process_content_with_ai(urdu_title, original_content):
    slug = ""
    rewrite_prompt = "Rewrite this news article in Urdu. Keep it to the point, engaging, and create suspense. Do not change the core real-time facts. Only provide the rewritten Urdu text without any markdown or extra text. Here is the news:\n\n" + original_content
    urdu_rewritten_content = get_ai_response(rewrite_prompt)
    return slug, urdu_rewritten_content

# ==========================================
# BLOGGER FUNCTION
# ==========================================

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
        print("✅ Blogger Post Published: " + res.get('url'))
        return res.get('url')
    except Exception as e:
        print("❌ Blogger Post Error: " + str(e))
        return None

# ==========================================
# MAIN EXECUTION
# ==========================================

def fetch_and_post_news():
    print("🚀 Auto Blogger Script Started!")
    posted_urls = load_posted_urls()
    posted_titles = load_posted_titles()
    posted_images = load_posted_images()
    print("📂 URLs: " + str(len(posted_urls)) + " | Titles: " + str(len(posted_titles)) + " | Images: " + str(len(posted_images)))

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36'}

    posts_published = 0
    MAX_POSTS_PER_RUN = len(FEEDS)

    for category_label, feed_url in FEEDS.items():
        if posts_published >= MAX_POSTS_PER_RUN:
            print("⚠️ Max " + str(MAX_POSTS_PER_RUN) + " posts reached. Stopping.")
            break

        print("\n🔍 Checking: " + category_label)

        try:
            feed_response = requests.get(feed_url, headers=headers, timeout=15)
            parsed_feed = feedparser.parse(feed_response.content)
        except Exception as e:
            print("⚠️ Feed error: " + str(e))
            continue

        print("✅ Found " + str(len(parsed_feed.entries)) + " articles")

        for entry in parsed_feed.entries:
            if posts_published >= MAX_POSTS_PER_RUN:
                break

            news_link = entry.link
            news_title = entry.title

            if news_link in posted_urls:
                print("⏩ Skip URL: " + news_title[:50])
                continue

            normalized_title = normalize_title(news_title)
            if normalized_title in posted_titles:
                print("⏩ Skip Title: " + news_title[:50])
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
                        img_tag = BeautifulSoup("<img src='" + img_url + "' alt='News Image' />", 'html.parser').img
                except:
                    pass

            if not img_tag:
                print("🚫 No Image: " + news_title[:50])
                continue

            img_src = img_tag.get('src', '')
            if img_src and img_src in posted_images:
                print("⏩ Skip Image: " + news_title[:50])
                continue

            clean_text = soup.get_text(separator="\n").strip()

            print("✍️ AI Processing: " + news_title[:60])
            slug, rewritten_urdu = process_content_with_ai(news_title, clean_text)

            if not rewritten_urdu:
                print("❌ AI fail. Skip.")
                continue

            image_html = str(img_tag)
            final_html_content = image_html + "<br><br><p>" + rewritten_urdu + "</p><br><br><p><em>News Source: Express News</em></p>"

            post_url = post_to_blogger(news_title, final_html_content, [category_label])

            if post_url:
                save_posted_url(news_link)
                save_posted_title(normalized_title)
                if img_src:
                    save_posted_image(img_src)

                posted_urls.add(news_link)
                posted_titles.add(normalized_title)
                if img_src:
                    posted_images.add(img_src)

                posts_published += 1
                print("✅ Post " + str(posts_published) + "/" + str(MAX_POSTS_PER_RUN) + " published.")
                print("=" * 50)

if __name__ == "__main__":
    fetch_and_post_news()
    print("🏁 Script Finished!")
