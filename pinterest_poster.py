import feedparser
import os
import re
import time
import requests
from bs4 import BeautifulSoup

# ==========================================
# ⚙️ CONFIGURATIONS — YAHAN APNI DETAILS DAALEIN
# ==========================================

# Pinterest Credentials
PINTEREST_ACCESS_TOKEN = "pina_AMA25KYYAAV6QAQAGDANKDPRZS56PIABQBIQDWMJO2TM3WCBSFLTQZ3PU3GX2EWWL4DZKKK37V6TGIGAE5PQV6E64PBSBXYA"
PINTEREST_BOARD_ID = "996914136205890271"

# Aap ki Blogger site ka URL
BLOG_URL = "https://yourbolt.blogspot.com"

# Repost rokne ke liye file
PINNED_FILE = "pinned_posts.txt"

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_pinned():
    if os.path.exists(PINNED_FILE):
        with open(PINNED_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_pinned(value):
    with open(PINNED_FILE, "a", encoding="utf-8") as f:
        f.write(value + "\n")

def extract_first_image(html_content):
    """Post ke HTML se pehli image nikalein"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        img = soup.find('img')
        if img and img.get('src'):
            return img['src']
    except:
        pass
    return None

# ==========================================
# PINTEREST FUNCTION
# ==========================================

def post_to_pinterest(title, image_url, post_url):
    if not PINTEREST_ACCESS_TOKEN or not PINTEREST_BOARD_ID:
        print("⚠️ Pinterest credentials missing.")
        return False
    
    if not image_url:
        print("⚠️ Image nahi mili. Skip.")
        return False
    
    url = "https://api.pinterest.com/v5/pins"
    headers = {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "board_id": PINTEREST_BOARD_ID,
        "title": title[:100],
        "description": title[:500],
        "link": post_url,
        "media_source": {
            "source_type": "image_url",
            "url": image_url
        }
    }
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        if r.status_code == 201:
            print(f"✅ Pinterest pin banaya! ID: {r.json().get('id')}")
            return True
        else:
            print(f"❌ Pinterest error: {r.status_code} - {r.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Pinterest network error: {e}")
        return False

# ==========================================
# MAIN EXECUTION
# ==========================================

def fetch_and_pin():
    print("🚀 Pinterest Auto Poster Started!")
    
    pinned = load_pinned()
    print(f"📂 Pehle se pinned posts: {len(pinned)}")
    
    # Blogger ka RSS feed
    feed_url = f"{BLOG_URL}/feeds/posts/default?alt=rss&max-results=20"
    
    try:
        feed_response = requests.get(feed_url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0'
        })
        parsed_feed = feedparser.parse(feed_response.content)
    except Exception as e:
        print(f"⚠️ Feed error: {e}")
        return
    
    print(f"✅ Found {len(parsed_feed.entries)} posts")
    
    pinned_count = 0
    max_pins_per_run = 3   # Ek run mein max 3 pins (spam se bachne ke liye)
    
    for entry in parsed_feed.entries:
        if pinned_count >= max_pins_per_run:
            print(f"⚠️ Max {max_pins_per_run} pins per run. Stopping.")
            break
        
        post_url = entry.link
        post_title = entry.title
        
        # Check: Pehle se pin hua?
        if post_url in pinned:
            print(f"⏩ Skip (Already Pinned): {post_title[:50]}")
            continue
        
        # Image nikalein
        raw_content = entry.content[0].value if 'content' in entry else entry.get('summary', '')
        image_url = extract_first_image(raw_content)
        
        if not image_url:
            print(f"🚫 No Image: {post_title[:50]}")
            continue
        
        # Pinterest par pin karein
        print(f"📌 Pinning: {post_title[:60]}")
        if post_to_pinterest(post_title, image_url, post_url):
            save_pinned(post_url)
            pinned_count += 1
        
        time.sleep(3)   # Pinterest rate limit ke liye
    
    print(f"\n🏁 Total {pinned_count} pins banaye gaye!")

if __name__ == "__main__":
    fetch_and_pin()
