"""Read Google Chrome, Microsoft Edge and Mozilla Firefox browsing history and save it as JSON."""

import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_CHROME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)


class BrowserHistory:
    """Access Chrome / Firefox history and export it to the data directory."""

    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = Path(data_dir)

    # ---------- locating databases ----------
    @staticmethod
    def _chromium_history_paths(*parts):
        local = os.environ.get("LOCALAPPDATA", "")
        base = Path(local).joinpath(*parts, "User Data")
        if not base.is_dir():
            return []
        # "Default" plus any "Profile N" folders
        return [p / "History" for p in sorted(base.iterdir())
                if (p.name == "Default" or p.name.startswith("Profile ")) and (p / "History").is_file()]

    @staticmethod
    def _firefox_history_paths():
        roaming = os.environ.get("APPDATA", "")
        base = Path(roaming) / "Mozilla" / "Firefox" / "Profiles"
        if not base.is_dir():
            return []
        return [p / "places.sqlite" for p in sorted(base.iterdir()) if (p / "places.sqlite").is_file()]

    # ---------- reading ----------
    @staticmethod
    def _query_copy(db_path, sql, limit):
        """Copy the DB (the browser keeps it locked) and run a query on the copy."""
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "history.db"
            shutil.copy2(db_path, copy)
            for suffix in ("-wal", "-shm"):  # include uncommitted WAL data (Firefox)
                side = Path(str(db_path) + suffix)
                if side.is_file():
                    shutil.copy2(side, str(copy) + suffix)
            conn = sqlite3.connect(copy)
            try:
                return conn.execute(sql, (limit,)).fetchall()
            finally:
                conn.close()

    def get_chrome_history(self, limit=1000):
        return self._get_chromium_history("chrome", self._chromium_history_paths("Google", "Chrome"), limit)

    def get_edge_history(self, limit=1000):
        return self._get_chromium_history("edge", self._chromium_history_paths("Microsoft", "Edge"), limit)

    def _get_chromium_history(self, browser, paths, limit):
        sql = ("SELECT url, title, visit_count, last_visit_time FROM urls "
               "ORDER BY last_visit_time DESC LIMIT ?")
        entries = []
        for path in paths:
            profile = path.parent.name
            try:
                rows = self._query_copy(path, sql, limit)
            except (sqlite3.Error, OSError):
                continue
            for url, title, count, ts in rows:
                visited = _CHROME_EPOCH + timedelta(microseconds=ts) if ts else None
                entries.append(self._entry(browser, profile, url, title, count, visited))
        return self._sorted(entries, limit)

    def get_firefox_history(self, limit=1000):
        sql = ("SELECT url, title, visit_count, last_visit_date FROM moz_places "
               "WHERE last_visit_date IS NOT NULL ORDER BY last_visit_date DESC LIMIT ?")
        entries = []
        for path in self._firefox_history_paths():
            profile = path.parent.name
            try:
                rows = self._query_copy(path, sql, limit)
            except (sqlite3.Error, OSError):
                continue
            for url, title, count, ts in rows:
                visited = datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc) if ts else None
                entries.append(self._entry("firefox", profile, url, title, count, visited))
        return self._sorted(entries, limit)

    def get_all_history(self, limit=1000):
        return self._sorted(self.get_chrome_history(limit) + self.get_edge_history(limit) + self.get_firefox_history(limit), limit)

    # ---------- most visited ----------
    def most_visited(self, limit=10, pool=5000):
        """Top pages by visit count (same URL merged across browsers/profiles)."""
        pages = {}
        for e in self.get_all_history(pool):
            p = pages.setdefault(e["url"], {"url": e["url"], "title": e["title"],
                                            "visit_count": 0, "last_visit": e["last_visit"]})
            p["visit_count"] += e["visit_count"] or 0
        return sorted(pages.values(), key=lambda p: p["visit_count"], reverse=True)[:limit]

    def most_visited_sites(self, limit=10, pool=5000):
        """Top websites (by domain) with total visits."""
        sites = {}
        for e in self.get_all_history(pool):
            domain = (urlparse(e["url"]).hostname or "").removeprefix("www.")
            if domain:
                sites[domain] = sites.get(domain, 0) + (e["visit_count"] or 0)
        ranked = sorted(sites.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [{"site": d, "visit_count": c} for d, c in ranked]

    # ---------- saving ----------
    def save(self, limit=1000, filename="browser_history.json"):
        """Save Chrome + Edge + Firefox history to <data_dir>/<filename>. Returns the file path."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self.data_dir / filename
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "chrome": self.get_chrome_history(limit),
            "edge": self.get_edge_history(limit),
            "firefox": self.get_firefox_history(limit),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return path

    # ---------- helpers ----------
    @staticmethod
    def _entry(browser, profile, url, title, count, visited):
        return {
            "browser": browser,
            "profile": profile,
            "url": url,
            "title": title or "",
            "visit_count": count,
            "last_visit": visited.astimezone().isoformat() if visited else None,
        }

    @staticmethod
    def _sorted(entries, limit):
        entries.sort(key=lambda e: e["last_visit"] or "", reverse=True)
        return entries[:limit]


if __name__ == "__main__":
    out = BrowserHistory().save()
    print(f"Saved browser history to {out}")
