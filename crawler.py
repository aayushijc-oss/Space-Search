import os
import random
import re
import time
import requests

URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "SchoolSearchEngine/1.0 (student project)"}
SAVE_DIR = os.path.join("data", "pages")

SEEDS = [
    "Apollo 11", "International Space Station", "Mars", "NASA", "Voyager 1",
    "SpaceX", "Hubble Space Telescope", "Moon", "Space Shuttle", "Rocket",
    "Sputnik 1", "Yuri Gagarin", "Neil Armstrong", "Artemis program",
    "James Webb Space Telescope", "Mars rover", "Black hole", "Galaxy",
    "Solar System", "Satellite", "Astronaut", "Space Race", "Saturn V",
    "Jupiter", "Europa (moon)", "European Space Agency", "ISRO", "Mir",
]
MAX_PAGES = 300
DELAY = 1  


def safe_name(title):
    
    return re.sub(r'[\\/:*?"<>|]', "_", title)


def api_get(params):
    response = requests.get(URL, params=params, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return response.json()


def get_links(title):
    data = api_get({
        "action": "query",
        "prop": "links",
        "titles": title,
        "pllimit": "max",
        "plnamespace": 0,  
        "redirects": 1,
        "format": "json",
    })
    page = list(data["query"]["pages"].values())[0]
    return [link["title"] for link in page.get("links", [])]


def download_article(title):
    """Returns True if it made a request, False if the file already existed."""
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


def collect_titles():
    titles = list(SEEDS)
    seen = set(titles)
    per_seed = (MAX_PAGES - len(SEEDS)) // len(SEEDS)

    for seed in SEEDS:
        try:
            links = get_links(seed)
        except Exception as e:
            print("Could not get links for", seed, e)
            continue
        random.shuffle(links)  
        added = 0
        for link in links:
            if link not in seen and added < per_seed:
                seen.add(link)
                titles.append(link)
                added += 1
        time.sleep(DELAY)
    return titles

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

if __name__ == "__main__":
    titles = collect_titles()
    print(len(titles), "titles to download")

    for i, title in enumerate(titles, 1):
        try:
            made_request = download_article(title)
        except Exception as e:
            print("Failed:", title, e)
            made_request = True
        print(f"{i}/{len(titles)}  {title}")
        if made_request:
            time.sleep(DELAY)