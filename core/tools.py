"""Tools the AI can choose from. Each tool returns plain text for the model to explain."""

from services.browser_history import BrowserHistory
from services.downloads import DownloadsService
from services.web_scraper import ProthomAloScraper


def get_news():
    with ProthomAloScraper() as scraper:
        items = scraper.get_headlines(10)
    return "Today's headlines (Prothom Alo):\n" + "\n".join(f"- {i['title']}" for i in items)


def downloads_status():
    d = DownloadsService().summary()
    lines = [f"Downloads folder: {d['count']} items, {d['total']} total. Largest:"]
    lines += [f"- {i['name']} ({i['size_bytes'] // 1024 // 1024} MB)" for i in d["largest"]]
    if d["warning"]:
        lines.append(d["warning"])
    return "\n".join(lines)


def most_visited_sites():
    rows = BrowserHistory().most_visited_sites(10)
    return "Most visited websites:\n" + "\n".join(f"- {r['site']} ({r['visit_count']} visits)" for r in rows)


def most_visited_pages():
    rows = BrowserHistory().most_visited(10)
    return "Most visited pages:\n" + "\n".join(
        f"- {(r['title'] or r['url'])[:70]} ({r['visit_count']} visits)" for r in rows)


# name -> (description shown to the model, function, keywords for fallback routing)
TOOLS = {
    "get_news": ("today's news, headlines, what is happening", get_news,
                 ("news", "headline", "খবর")),
    "downloads_status": ("status/size/contents of the Downloads folder, files, disk usage",
                         downloads_status, ("download", "folder", "file")),
    "most_visited_sites": ("which websites the user visits most (browser history)",
                           most_visited_sites, ("site", "website", "visit", "browser")),
    "most_visited_pages": ("which specific pages the user visits most",
                           most_visited_pages, ("page", "history")),
}


def run_tool(name):
    return TOOLS[name][1]()


def keyword_matches(message):
    """Names of tools whose keywords appear in the message."""
    text = message.lower()
    return [name for name, (_, _, keywords) in TOOLS.items()
            if any(k in text for k in keywords)]
