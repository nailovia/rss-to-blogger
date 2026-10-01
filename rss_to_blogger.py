import feedparser
import os
import re
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ==========================================
# CONFIGURATIONS
# ==========================================

GEMINI_API_KEYS = os.environ.get("GEMINI_API_KEYS", "").split(",")
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
]

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

CLIENT_ID = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN", "")
BLOG_ID = os.environ.get("BLOG_ID", "")
YOUR_BLOG_URL = os.environ.get("BLOG_URL", "https://yourbolt.blogspot.com")

# ==========================================
# FEEDS (14 feeds - har ek se 1 post aayega)
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

LABEL_MAP = {
    "Tech-Express": "Technology",
    "Tech-Juice": "Technology",
    "Tech-ProPakistani": "Technology",
    "Ent-Express": "Entertainment",
    "Ent-SuchTV": "Entertainment",
    "Ent-DailyShowbiz": "Entertainment",
    "Ent-ThePen": "Entertainment",
}

POSTED_URLS_FILE = "posted_urls.txt"
POSTED_TITLES_FILE = "posted_titles.txt"
POSTED_IMAGES_FILE = "posted_images.txt"
POSTED_HASHES_FILE = "posted_hashes.txt"

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

def load_posted_hashes():
    return load_set_from_file(POSTED_HASHES_FILE)

def save_posted_url(url):
    save_to_file(POSTED_URLS_FILE, url)

def save_posted_title(title):
    save_to_file(POSTED_TITLES_FILE, title)

def save_posted_image(image_url):
    save_to_file(POSTED_IMAGES_FILE, image_url)

def save_posted_hash(h):
    save_to_file(POSTED_HASHES_FILE, h)

def normalize_title(title):
    title = re.sub(r'[^\w\s\u0600-\u06FF]', '', title)
    title = re.sub(r'\s+', ' ', title).strip().lower()
    return title

def content_hash(text):
    if not text:
        return ""
    snippet = re.sub(r'\s+', '', text[:200]).strip().lower()
    return hashlib.md5(snippet.encode('utf-8')).hexdigest()

# ==========================================
# TEXT CLEANING FUNCTIONS
# ==========================================

def has_non_urdu_script(text):
    if not text:
        return False
    bad_ranges = [
        (0x0900, 0x097F), (0x0980, 0x09FF), (0x0A00, 0x0A7F),
        (0x0A80, 0x0AFF), (0x0B00, 0x0B7F), (0x0B80, 0x0BFF),
        (0x0C00, 0x0C7F), (0x0C80, 0x0CFF), (0x0D00, 0x0D7F),
        (0x0D80, 0x0DFF), (0x0E00, 0x0E7F), (0x0E80, 0x0EFF),
    ]
    for char in text:
        code = ord(char)
        for start, end in bad_ranges:
            if start <= code <= end:
                return True
    return False

def has_latin_letters(text):
    """Check karein ke text mein English letters hain ya nahi"""
    if not text:
        return False
    return bool(re.search(r'[A-Za-z]', text))

def fix_arabic_to_urdu(text):
    """Arabic characters ko Urdu mein convert karein."""
    if not text:
        return text
    replacements = {
        '\u064A': '\u06CC',  # ي → ی
        '\u0649': '\u06CC',  # ى → ی
        '\u06D3': '\u0626',  # ۓ → ئ
        '\u0643': '\u06A9',  # ك → ک
        '\u0647': '\u06C1',  # ه → ہ
        '\u06C0': '\u06C1',  # ۀ → ہ
        '\u0623': '\u0627',  # أ → ا
        '\u0625': '\u0627',  # إ → ا
        '\u0671': '\u0627',  # ٱ → ا
        '\u0624': '\u0648',  # ؤ → و
        '\u0629': '\u06C1',  # ة → ہ
    }
    for arabic, urdu in replacements.items():
        text = text.replace(arabic, urdu)
    text = text.replace('\u0627\u0653', '\u0622')
    return text

def remove_bengali_hindi_chars(text):
    if not text:
        return text
    bad_ranges = [
        (0x0900, 0x097F), (0x0980, 0x09FF), (0x0A00, 0x0A7F),
        (0x0A80, 0x0AFF), (0x0B00, 0x0B7F), (0x0B80, 0x0BFF),
        (0x0C00, 0x0C7F), (0x0C80, 0x0CFF), (0x0D00, 0x0D7F),
        (0x0D80, 0x0DFF), (0x0E00, 0x0E7F), (0x0E80, 0x0EFF),
    ]
    result = []
    for char in text:
        code = ord(char)
        is_bad = False
        for start, end in bad_ranges:
            if start <= code <= end:
                is_bad = True
                break
        if not is_bad:
            result.append(char)
    return ''.join(result)

def clean_urdu_text(text):
    if not text:
        return text
    text = fix_arabic_to_urdu(text)
    text = remove_bengali_hindi_chars(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

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
# GROQ FUNCTION (With System Message)
# ==========================================

def get_groq_response(prompt):
    if not GROQ_API_KEY:
        print("Groq key nahi hai. Skip.")
        return None
    print("Groq trying: " + GROQ_MODEL)
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": "Bearer " + GROQ_API_KEY, "Content-Type": "application/json"}
        data = {
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a translation machine. You ONLY output the final Urdu result in the exact requested format. You NEVER explain, reason, think out loud, or write your thoughts. You NEVER write in English. You NEVER use placeholders like [Urdu Title Here]. If you cannot translate, output empty content."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 3000
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
# OPENROUTER FUNCTION (With System Message)
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
            "messages": [
                {
                    "role": "system",
                    "content": "You are a translation machine. You ONLY output the final Urdu result in the exact requested format. You NEVER explain, reason, think out loud, or write your thoughts. You NEVER write in English. You NEVER use placeholders like [Urdu Title Here]."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 3000
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
# MASTER AI FUNCTION
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
# PROMPT BUILDER (Improved - No Confusion)
# ==========================================

def build_prompt(source_title, original_content, strict_mode=False):
    prompt = "TASK: Translate and rewrite the following news into Pakistani Urdu.\n\n"
    prompt += "INPUT TITLE:\n"
    prompt += source_title + "\n\n"
    prompt += "INPUT ARTICLE:\n"
    prompt += original_content + "\n\n"
    prompt += "STRICT RULES:\n"
    prompt += "- Output ONLY the final result. Do NOT write your thinking, reasoning, or explanation.\n"
    prompt += "- Do NOT repeat the instructions. Do NOT write 'We need to...' or 'Let me...'.\n"
    prompt += "- Do NOT use placeholders like [Urdu Title Here] or [Urdu Content Here].\n"
    prompt += "- Output MUST be 100% Pakistani Urdu using ONLY these letters: ا آ ب پ ت ٹ ث ج چ ح خ د ڈ ذ ر ڑ ز ژ س ش ص ض ط ظ ع غ ف ق ک گ ل م ن ں و ہ ھ ء ی ے ئ\n"
    prompt += "- STRICTLY FORBIDDEN characters:\n"
    prompt += "  * English letters (A-Z, a-z)\n"
    prompt += "  * Arabic: ي ك ه ة ؤ أ إ ٱ\n"
    prompt += "  * Bengali: অ আ ই ঈ ক খ গ ঘ ঙ চ ছ জ ঝ ঞ ট ঠ ড ঢ ণ ত থ দ ধ ন প ফ ব ভ ম য র ল শ ষ স হ\n"
    prompt += "  * Hindi: अ आ इ ई क ख ग घ च छ ज झ ट ठ ड ढ त थ द ध न प फ ब भ म य र ल व श ष स ह\n"
    prompt += "- Numbers 0-9 allowed.\n"
    prompt += "- Use 'آ' (alif madda) NOT 'آ'. Use 'ی' NOT 'ي'. Use 'ک' NOT 'ك'. Use 'ہ' NOT 'ه'.\n"
    prompt += "- Wherever hamza is needed, use 'ئ' (e.g., شیئر، گئی، کوئی). NEVER replace ئ with ی.\n"
    prompt += "- Do NOT change facts, numbers, or names. Proper nouns can be transliterated.\n\n"

    if strict_mode:
        prompt += "!!!!! EXTREME WARNING !!!!!\n"
        prompt += "Your previous response was REJECTED because it contained:\n"
        prompt += "  - English reasoning text\n"
        prompt += "  - Placeholder brackets like [Urdu Title Here]\n"
        prompt += "  - Wrong characters from other scripts\n"
        prompt += "This time, output ONLY the final Urdu result in the exact format below.\n\n"

    prompt += "OUTPUT FORMAT (follow exactly, nothing else):\n"
    prompt += "TITLE: <urdu title here>\n"
    prompt += "CONTENT: <urdu content here>\n"
    return prompt

# ==========================================
# AI PROCESSING FUNCTION (With Garbage Detection)
# ==========================================

def parse_ai_response(response):
    urdu_title = None
    urdu_content = None
    if not response:
        return None, None

    # Step 1: Garbage detection
    response_lower = response.lower()
    garbage_signs = [
        "we need to",
        "let's see",
        "let me",
        "wait,",
        "actually",
        "we must",
        "[urdu title here]",
        "[urdu content here]",
        "task:",
        "input title:",
        "input article:",
        "strict rules:",
        "output format:",
        "here is the",
        "here's the",
    ]
    for sign in garbage_signs:
        if sign in response_lower:
            print("Garbage detected in AI response: " + sign)
            return None, None

    # Step 2: Parse TITLE: and CONTENT:
    try:
        if "TITLE:" in response and "CONTENT:" in response:
            parts = response.split("CONTENT:", 1)
            title_part = parts[0].replace("TITLE:", "").strip()
            content_part = parts[1].strip()

            # Remove any extra TITLE: prefix if AI duplicated
            title_part = title_part.replace("TITLE:", "").strip()

            urdu_title = title_part if title_part else None
            urdu_content = content_part if content_part else None
        else:
            print("AI response format invalid (missing TITLE/CONTENT markers)")
            return None, None
    except Exception as e:
        print("Parse error: " + str(e))
        return None, None

    return urdu_title, urdu_content

def process_content_with_ai(source_title, original_content):
    urdu_title = source_title
    urdu_content = None
    last_response = None
    for attempt in range(3):
        print("AI Attempt " + str(attempt + 1) + "/3")
        strict = (attempt > 0)
        prompt = build_prompt(source_title, original_content, strict_mode=strict)
        response = get_ai_response(prompt)
        if not response:
            print("AI ne jawab nahi diya. Retry...")
            time.sleep(2)
            continue
        last_response = response
        temp_title, temp_content = parse_ai_response(response)
        
        # Agar garbage detect hua to skip
        if not temp_title or not temp_content:
            print("Garbage response. Retrying...")
            time.sleep(2)
            continue
        
        temp_title = clean_urdu_text(temp_title) if temp_title else None
        temp_content = clean_urdu_text(temp_content) if temp_content else None
        
        title_has_bad = has_non_urdu_script(temp_title) if temp_title else True
        content_has_bad = has_non_urdu_script(temp_content) if temp_content else True
        title_has_latin = has_latin_letters(temp_title) if temp_title else True
        content_has_latin = has_latin_letters(temp_content) if temp_content else True
        
        if not title_has_bad and not content_has_bad and not title_has_latin and not content_has_latin and temp_content:
            urdu_title = temp_title
            urdu_content = temp_content
            print("Urdu content valid.")
            break
        else:
            print("Bad characters detected! Retrying...")
            time.sleep(2)
    
    if not urdu_content and last_response:
        print("Teen attempts fail. Aakhri response clean kar rahe hain.")
        urdu_title, urdu_content = parse_ai_response(last_response)
        if urdu_title:
            urdu_title = clean_urdu_text(urdu_title)
        if urdu_content:
            urdu_content = clean_urdu_text(urdu_content)
    
    if not urdu_title:
        urdu_title = source_title
    
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
        body = {"title": title, "content": content, "labels": labels_list}
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
    posted_hashes = load_posted_hashes()
    print("URLs: " + str(len(posted_urls)) + " | Titles: " + str(len(posted_titles)) + " | Images: " + str(len(posted_images)) + " | Hashes: " + str(len(posted_hashes)))

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36'}

    MAX_POSTS_PER_RUN = 14
    posts_published = 0

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

        posted_from_this_feed = False

        for entry in parsed_feed.entries:
            if posted_from_this_feed:
                break

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

            content_hash_value = content_hash(clean_text)
            if content_hash_value and content_hash_value in posted_hashes:
                print("Skip Content (duplicate): " + news_title[:50])
                continue

            print("AI Processing: " + news_title[:60])
            urdu_title, rewritten_urdu = process_content_with_ai(news_title, clean_text)

            if not rewritten_urdu:
                print("AI fail. Skip.")
                continue

            image_html = str(img_tag)
            final_html_content = image_html + "<br><br><p>" + rewritten_urdu + "</p><br><br><p><em>News Source: Express News</em></p>"

            final_label = LABEL_MAP.get(category_label, category_label)

            post_url = post_to_blogger(urdu_title, final_html_content, [final_label])

            if post_url:
                save_posted_url(news_link)
                save_posted_title(normalized_title)
                if img_src:
                    save_posted_image(img_src)
                save_posted_hash(content_hash_value)

                posted_urls.add(news_link)
                posted_titles.add(normalized_title)
                if img_src:
                    posted_images.add(img_src)
                posted_hashes.add(content_hash_value)

                posts_published += 1
                posted_from_this_feed = True

                print("Post " + str(posts_published) + "/" + str(MAX_POSTS_PER_RUN) + " published with label: " + final_label + " (from " + category_label + ")")
                print("=" * 50)

    print("\nTotal posts published this run: " + str(posts_published))

if __name__ == "__main__":
    fetch_and_post_news()
    print("Script Finished!")
