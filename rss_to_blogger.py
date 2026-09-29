import feedparser
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ==========================================
# CONFIGURATIONS (GitHub Secrets se aayenge)
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

# ==========================================
# FEEDS (Alag naam, common label ke liye)
# ==========================================
FEEDS = {
    "Pakistan": "https://www.express.pk/pakistan/feed/",
    "World": "https://www.express.pk/world/feed/",
    "Sports": "https://www.express.pk/sports/feed/",
    "Business": "https://www.express.pk/business/feed/",
    "Science": "https://www.express.pk/science/feed/",
    "Health": "https://www.express.pk/feed/health",
    "Jobs": "https://www.shaheenleaderacademy.com/feed/",
    "Tech-Express": "https://www.express.pk/feed/technology",
    "Tech-Juice": "https://www.techjuice.pk/feed/",
    "Tech-ProPakistani": "https://propakistani.pk/category/tech-and-telecom/feed/",
    "Ent-Express": "https://www.express.pk/feed/saqafat",
    "Ent-SuchTV": "https://www.suchtv.pk/urdu/entertainment/itemlist.html?format=feed",
    "Ent-DailyShowbiz": "https://dailyshowbiz.net/feed/",
    "Ent-ThePen": "https://urdu.thepenpk.com/feed/",
}

# ==========================================
# LABEL MAP (Alag feeds ko common label dena)
# ==========================================
LABEL_MAP = {
    "Tech-Express": "Technology",
    "Tech-Juice": "Technology",
    "Tech-ProPakistani": "Technology",
    "Ent-Express": "Entertainment",
    "Ent-SuchTV": "Entertainment",
    "Ent-DailyShowbiz": "Entertainment",
    "Ent-ThePen": "Entertainment",
}

# Files
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

def fix_arabic_to_urdu(text):
    """
    Arabic characters ko Urdu characters mein convert karein.
    AI kabhi kabhi Arabic script use kar jata hai.
    """
    if not text:
        return text
    
    replacements = {
        '\u064A': '\u06CC',  # ي → ی (Arabic yeh → Urdu yeh)
        '\u0649': '\u06CC',  # ى → ی
        '\u0626': '\u06CC',  # ئ → ی
        '\u0643': '\u06A9',  # ك → ک (Arabic kaf → Urdu kaf)
        '\u0647': '\u06C1',  # ه → ہ (Arabic heh → Urdu heh)
        '\u06C0': '\u06C1',  # ۀ → ہ
        '\u0623': '\u0627',  # أ → ا
        '\u0625': '\u0627',  # إ → ا
        '\u0671': '\u0627',  # ٱ → ا
        '\u0624': '\u0648',  # ؤ → و
        '\u0629': '\u06C1',  # ة → ہ
    }
    
    for arabic, urdu in replacements.items():
        text = text.replace(arabic, urdu)
    
    # "آ" (alif + maddah) ko "آ" (alif madda) banayein
    text = text.replace('\u0627\u0653', '\u0622')
    
    return text

# ==========================================
# GEMINI FUNCTION
# ==========================================

def get_gemini_response(prompt):
    for model in GEMINI_MODELS:
        print("Gemini trying: " + model)
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
                        print("Gemini success: " + model)
                        return result['candidates'][0]['content']['parts'][0]['text'].strip()
                elif response.status_code == 429:
                    print("Gemini quota khatam: " + model)
                else:
                    print("Gemini " + model + " failed: " + str(response.status_code))
                time.sleep(1)
            except Exception as e:
                print("Gemini network error: " + str(e))
                time.sleep(1)
    print("Gemini saare fail.")
    return None

# ==========================================
# GROQ FUNCTION
# ==========================================

def get_groq_response(prompt):
    if not GROQ_API_KEY:
        print("Groq key nahi hai. Skip.")
        return None
    
    print("Groq trying: " + GROQ_MODEL)
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
            print("Groq success: " + GROQ_MODEL)
            return content
        elif response.status_code == 429:
            print("Groq quota khatam.")
        else:
            print("Groq failed: " + str(response.status_code))
    except Exception as e:
        print("Groq network error: " + str(e))
    return None

# ==========================================
# OPENROUTER FUNCTION
# ==========================================

def get_openrouter_response(prompt):
    if not OPENROUTER_API_KEY:
        print("OpenRouter key nahi hai. Skip.")
        return None
    
    print("OpenRouter trying: " + OPENROUTER_MODEL)
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
            print("OpenRouter success: " + OPENROUTER_MODEL)
            return content
        elif response.status_code == 429:
            print("OpenRouter quota khatam.")
        else:
            print("OpenRouter failed: " + str(response.status_code))
    except Exception as e:
        print("OpenRouter network error: " + str(e))
    return None

# ==========================================
# MASTER AI FUNCTION (Fallback Chain)
# ==========================================

def get_ai_response(prompt):
    print("=" * 50)
    print("Step 1: Gemini")
    response = get_gemini_response(prompt)
    if response:
        return response
    
    print("Step 2: Groq")
    response = get_groq_response(prompt)
    if response:
        return response
    
    print("Step 3: OpenRouter")
    response = get_openrouter_response(prompt)
    if response:
        return response
    
    print("Saare providers fail ho gaye.")
    return None

# ==========================================
# AI PROCESSING FUNCTION (Title + Content)
# ==========================================

def process_content_with_ai(english_title, original_content):
    combined_prompt = "You are a professional Pakistani Urdu news editor for a Pakistani news website.\n"
    combined_prompt += "Your task is to:\n"
    combined_prompt += "1. Translate the given English title into Pakistani Urdu.\n"
    combined_prompt += "2. Rewrite the given news article entirely in Pakistani Urdu.\n\n"
    combined_prompt += "CRITICAL RULES (MUST FOLLOW):\n"
    combined_prompt += "1. Output MUST be 100% in Pakistani Urdu script.\n"
    combined_prompt += "2. USE ONLY PAKISTANI URDU ALPHABET: ا آ ب پ ت ٹ ث ج چ ح خ د ڈ ذ ر ڑ ز ژ س ش ص ض ط ظ ع غ ف ق ک گ ل م ن ں و ہ ھ ء ی ے\n"
    combined_prompt += "3. DO NOT use Arabic script characters like: ي ك ه ة ؤ ئ أ إ ٱ\n"
    combined_prompt += "4. DO NOT use Bengali or Hindi characters.\n"
    combined_prompt += "5. Write 'آ' (alif madda), NOT 'آ' (alif + maddah).\n"
    combined_prompt += "6. Write 'ی' (Urdu yeh), NOT 'ي' (Arabic yeh).\n"
    combined_prompt += "7. Write 'ک' (Urdu kaf), NOT 'ك' (Arabic kaf).\n"
    combined_prompt += "8. Write 'ہ' (Urdu heh), NOT 'ه' (Arabic heh).\n"
    combined_prompt += "9. Do not change the core real-time facts or numbers.\n"
    combined_prompt += "10. Use EXACTLY the following format:\n"
    combined_prompt += "TITLE: [Urdu Title Here]\n"
    combined_prompt += "CONTENT: [Urdu Content Here]\n\n"
    combined_prompt += "Title: " + english_title + "\n"
    combined_prompt += "Article:\n" + original_content
    
    response = get_ai_response(combined_prompt)
    
    urdu_title = english_title
    urdu_content = None
    
    if response:
        try:
            if "TITLE:" in response and "CONTENT:" in response:
                parts = response.split("CONTENT:")
                urdu_title = parts[0].replace("TITLE:", "").strip()
                urdu_content = parts[1].strip()
            else:
                urdu_content = response
        except Exception as e:
            print("AI response parse error: " + str(e))
            urdu_content = response

    # Arabic characters ko Urdu mein convert karein
    urdu_title = fix_arabic_to_urdu(urdu_title)
    if urdu_content:
        urdu_content = fix_arabic_to_urdu(urdu_content)

    return urdu_title, urdu_content

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
        print("Blogger Post Published: " + res.get('url'))
        return res.get('url')
    except Exception as e:
        print("Blogger Post Error: " + str(e))
        return None

# ==========================================
# MAIN EXECUTION
# ==========================================

def fetch_and_post_news():
    print("Auto Blogger Script Started!")
    posted_urls = load_posted_urls()
    posted_titles = load_posted_titles()
    posted_images = load_posted_images()
    print("URLs: " + str(len(posted_urls)) + " | Titles: " + str(len(posted_titles)) + " | Images: " + str(len(posted_images)))

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36'}

    posts_published = 0
    MAX_POSTS_PER_RUN = len(FEEDS)

    for category_label, feed_url in FEEDS.items():
        if posts_published >= MAX_POSTS_PER_RUN:
            print("Max " + str(MAX_POSTS_PER_RUN) + " posts reached. Stopping.")
            break

        print("\nChecking: " + category_label)

        try:
            feed_response = requests.get(feed_url, headers=headers, timeout=15)
            parsed_feed = feedparser.parse(feed_response.content)
        except Exception as e:
            print("Feed error: " + str(e))
            continue

        print("Found " + str(len(parsed_feed.entries)) + " articles")

        for entry in parsed_feed.entries:
            if posts_published >= MAX_POSTS_PER_RUN:
                break

            news_link = entry.link
            news_title = entry.title

            if news_link in posted_urls:
                print("Skip URL: " + news_title[:50])
                continue

            normalized_title = normalize_title(news_title)
            if normalized_title in posted_titles:
                print("Skip Title: " + news_title[:50])
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
                print("No Image: " + news_title[:50])
                continue

            img_src = img_tag.get('src', '')
            if img_src and img_src in posted_images:
                print("Skip Image: " + news_title[:50])
                continue

            clean_text = soup.get_text(separator="\n").strip()

            print("AI Processing: " + news_title[:60])
            urdu_title, rewritten_urdu = process_content_with_ai(news_title, clean_text)

            if not rewritten_urdu:
                print("AI fail. Skip.")
                continue

            image_html = str(img_tag)
            final_html_content = image_html + "<br><br><p>" + rewritten_urdu + "</p><br><br><p><em>News Source: Express News</em></p>"

            # Common label apply karein
            final_label = LABEL_MAP.get(category_label, category_label)

            post_url = post_to_blogger(urdu_title, final_html_content, [final_label])

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
                print("Post " + str(posts_published) + "/" + str(MAX_POSTS_PER_RUN) + " published with label: " + final_label)
                print("=" * 50)

if __name__ == "__main__":
    fetch_and_post_news()
    print("Script Finished!")
