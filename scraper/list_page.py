import re
import time
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.stats.gov.cn/sj/sjjd/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) macro-monitor-bot/0.1"}
REQUEST_DELAY_SECONDS = 1.5

LINK_PATTERN = re.compile(r"^\./(\d{6})/t(\d{8})_(\d+)\.html$")


def _page_url(page: int) -> str:
    if page <= 1:
        return BASE_URL
    return f"{BASE_URL}index_{page - 1}.html"


def fetch_list_page(page: int, client: httpx.Client) -> list[str]:
    """Return the list of absolute article URLs found on a given listing page (1-indexed)."""
    resp = client.get(_page_url(page), headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    urls: list[str] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if LINK_PATTERN.match(href):
            abs_url = BASE_URL + href.lstrip("./")
            if abs_url not in seen:
                seen.add(abs_url)
                urls.append(abs_url)
    return urls


def iter_new_urls(known_urls: set[str], max_pages: int = 20):
    """Yield article URLs not already in known_urls, walking pages until a full page of
    already-known articles is hit (i.e. we've caught up to the last crawl)."""
    with httpx.Client(follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            urls = fetch_list_page(page, client)
            if not urls:
                break
            new_on_page = [u for u in urls if u not in known_urls]
            for u in new_on_page:
                yield u
            if not new_on_page:
                break
            time.sleep(REQUEST_DELAY_SECONDS)
