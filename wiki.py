import os
import re
import requests

URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "SchoolSearchEngine/1.0 (student project)"}
SAVE_DIR = os.path.join("data", "pages")


def safe_name(title):
    # Windows doesn't allow these characters in file names
    return re.sub(r'[\\/:*?"<>|]', "_", title)


def api_get(params):
    response = requests.get(URL, params=params, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return response.json()


def search_titles(query, limit=3):
    """Ask Wikipedia's search for the best matching article titles."""
    data = api_get({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
    })
    return [item["title"] for item in data["query"]["search"]]


def download_article(title):
    """Save one article as a text file. Returns False if it was already saved."""
    path = os.path.join(SAVE_DIR, safe_name(title) + ".txt")
    if os.path.exists(path):
        return False

    data = api_get({
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "titles": title,
        "redirects": 1,
        "format": "json",
    })
    page = list(data["query"]["pages"].values())[0]
    text = page.get("extract")
    if text:
        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return True 