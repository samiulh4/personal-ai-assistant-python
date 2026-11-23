"""Scrape Prothom Alo (https://www.prothomalo.com/) with httpx + BeautifulSoup."""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BASE_URL = "https://www.prothomalo.com/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "bn,en;q=0.8",
}


class ProthomAloScraper:
    """Fetch headlines from the home page and the full text of single articles."""

    def __init__(self, base_url=BASE_URL, data_dir=DATA_DIR, timeout=20):
        self.base_url = base_url
        self.data_dir = Path(data_dir)
        self.client = httpx.Client(headers=HEADERS, timeout=timeout, follow_redirects=True)

    # ---------- context manager so the connection is closed ----------
    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---------- fetching ----------
    def _get_soup(self, url):
        response = self.client.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    # ---------- scraping ----------
    def get_headlines(self, limit=30):
        """Return headlines from the home page: [{title, url, section}, ...]."""
        soup = self._get_soup(self.base_url)
        headlines, seen = [], set()
        for a in soup.select("a.title-link"):
            url = a.get("href")
            title = a.get_text(" ", strip=True)
            if not url or not title or url in seen:
                continue
            seen.add(url)
            headlines.append({"title": title, "url": url, "section": self._section(url)})
            if len(headlines) >= limit:
                break
        return headlines

    def get_article(self, url):
        """Return {title, description, image, url, content} for one article."""
        soup = self._get_soup(url)
        h1 = soup.select_one("h1")
        paragraphs = []
        for block in soup.select("div.story-element-text"):
            text = block.get_text(" ", strip=True)
            if text and not text.startswith("আরও পড়ুন"):  # skip "Read more" links
                paragraphs.append(text)
        return {
            "url": url,
            "title": h1.get_text(strip=True) if h1 else self._meta(soup, "og:title"),
            "description": self._meta(soup, "og:description"),
            "image": self._meta(soup, "og:image"),
            "content": paragraphs,
        }

    def scrape_home(self, limit=10, with_articles=False):
        """Headlines, optionally with the full text of each article."""
        headlines = self.get_headlines(limit)
        if with_articles:
            for item in headlines:
                try:
                    item["article"] = self.get_article(item["url"])
                except httpx.HTTPError as e:
                    item["article"] = {"error": str(e)}
        return headlines

    # ---------- saving ----------
    def save(self, limit=30, with_articles=False, filename="prothomalo.json"):
        """Save the scraped data to <data_dir>/<filename>. Returns the file path."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self.data_dir / filename
        payload = {
            "source": self.base_url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "items": self.scrape_home(limit, with_articles),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return path

    # ---------- helpers ----------
    @staticmethod
    def _meta(soup, prop):
        tag = soup.find("meta", property=prop)
        return tag.get("content", "") if tag else ""

    @staticmethod
    def _section(url):
        # https://www.prothomalo.com/<section>/... -> "<section>"
        parts = url.replace("https://www.prothomalo.com/", "").split("/")
        return parts[0] if len(parts) > 1 else ""


if __name__ == "__main__":
    with ProthomAloScraper() as scraper:
        path = scraper.save(limit=10, with_articles=True)
    print(f"Saved to {path}")
