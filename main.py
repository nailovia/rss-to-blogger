import os
import re
import time
import feedparser
from bs4 import BeautifulSoup
import google.oauth2.credentials
from googleapiclient.discovery import build

# Environment Variables (Secrets from GitHub)
BLOG_ID = "8444463613201429945"
CLIENT_ID = os.environ.get("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN")

# High-Quality RSS Feeds List
RSS_FEEDS = [
    "https://www.naildesignsdaily.com/feed",
    "https://www.nailsmag.com/rss",
    "https://polishgalore.com/feed/",
]

HISTORY_FILE = "posted_links.txt"
MAX_DAILY_POSTS = 10
MAX_ALLOWED_LINKS = 5  # Article ke andar maximum 3 to 5 links hone chahiye


def load_posted_links():
  """Loads previously posted URLs to prevent duplicates."""
  if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
      return set(f.read().splitlines())
  return set()


def save_posted_link(link):
  """Saves published link to history file."""
  with open(HISTORY_FILE, "a", encoding="utf-8") as f:
    f.write(link + "\n")


def clean_html_content(html_content):
  """Cleans content: Removes spam links, keeps images, and limits external links to 3-5."""
  soup = BeautifulSoup(html_content, "html.parser")

  # 1. Remove unwanted tags (scripts, ads, social sharing widgets)
  for element in soup(["script", "iframe", "style", "ins", "form"]):
    element.decompose()

  # 2. Filter Links (Keep images intact, limit links to 3-5)
  links = soup.find_all("a")
  link_count = 0

  for a in links:
    href = a.get("href", "")

    # Skip/Remove known spam/affiliate link patterns
    if any(
        spam_word in href.lower()
        for spam_word in ["amazon", "affiliate", "bit.ly", "amzn.to", "utm_"]
    ):
      a.replace_with(a.text)  # Link strip kar do, text rehne do
      continue

    # Keep a maximum of 3 to 5 valid links
    if link_count < MAX_ALLOWED_LINKS:
      link_count += 1
    else:
      # Exceeded limit: remove link hyperlinking but keep anchor text
      a.replace_with(a.text)

  return str(soup)


def get_blogger_service():
  """Authenticates with Google Cloud API."""
  creds = google.oauth2.credentials.Credentials(
      token=None,
      refresh_token=REFRESH_TOKEN,
      token_uri="https://oauth2.googleapis.com/token",
      client_id=CLIENT_ID,
      client_secret=CLIENT_SECRET,
  )
  return build("blogger", "v3", credentials=creds)


def run_automation():
  service = get_blogger_service()
  posted_links = load_posted_links()
  posts_published_today = 0

  print(f"Loaded {len(posted_links)} previously published links.")

  for feed_url in RSS_FEEDS:
    if posts_published_today >= MAX_DAILY_POSTS:
      break

    print(f"Parsing feed: {feed_url}")
    feed = feedparser.parse(feed_url)

    for entry in feed.entries:
      if posts_published_today >= MAX_DAILY_POSTS:
        print(f"Reached daily target of {MAX_DAILY_POSTS} posts.")
        break

      post_link = entry.link

      # Duplicate Check
      if post_link in posted_links:
        continue

      title = entry.title

      # Raw HTML extract
      raw_content = ""
      if "content" in entry and len(entry.content) > 0:
        raw_content = entry.content[0].value
      elif "description" in entry:
        raw_content = entry.description

      if not raw_content or len(raw_content.strip()) < 100:
        continue

      # Clean HTML (Images retained, spam removed, links capped)
      cleaned_content = clean_html_content(raw_content)

      body = {
          "kind": "blogger#post",
          "title": title,
          "content": cleaned_content,
      }

      try:
        service.posts().insert(blogId=BLOG_ID, body=body).execute()
        print(
            f"[{posts_published_today + 1}/{MAX_DAILY_POSTS}] Published:"
            f" {title}"
        )

        save_posted_link(post_link)
        posted_links.add(post_link)

        posts_published_today += 1
        time.sleep(3)  # Rate limiting
      except Exception as e:
        print(f"Error publishing '{title}': {e}")

  print(f"Job completed. Total posts created today: {posts_published_today}")


if __name__ == "__main__":
  run_automation()
