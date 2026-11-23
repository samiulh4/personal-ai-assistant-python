"""List the files and folders inside the Downloads directory."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DOWNLOADS = Path.home() / "Downloads"
GB = 1024 ** 3
DEFAULT_WARN_BYTES = 5 * GB  # warn when Downloads is bigger than this


def human_size(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _folder_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


class DownloadsService:
    """Get the files and folders in a Downloads directory (default: the user's Downloads)."""

    def __init__(self, downloads_dir=DEFAULT_DOWNLOADS, data_dir=DATA_DIR):
        self.downloads_dir = Path(downloads_dir)
        self.data_dir = Path(data_dir)

    def list_items(self, sort_by="modified"):
        """Return every file and folder directly inside the directory.

        sort_by: "modified" (newest first), "name", or "size" (largest first).
        """
        if not self.downloads_dir.is_dir():
            raise FileNotFoundError(f"Downloads folder not found: {self.downloads_dir}")

        items = []
        for entry in self.downloads_dir.iterdir():
            try:
                stat = entry.stat()
            except OSError:
                continue  # broken link or locked file
            is_dir = entry.is_dir()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "type": "folder" if is_dir else "file",
                "extension": "" if is_dir else entry.suffix.lower(),
                "size_bytes": None if is_dir else stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).astimezone().isoformat(),
            })

        if sort_by == "name":
            items.sort(key=lambda i: i["name"].lower())
        elif sort_by == "size":
            items.sort(key=lambda i: i["size_bytes"] or 0, reverse=True)
        else:
            items.sort(key=lambda i: i["modified"], reverse=True)
        return items

    def list_files(self, **kwargs):
        return [i for i in self.list_items(**kwargs) if i["type"] == "file"]

    def list_folders(self, **kwargs):
        return [i for i in self.list_items(**kwargs) if i["type"] == "folder"]

    def summary(self, warn_bytes=DEFAULT_WARN_BYTES, top=5):
        """Total size (folders included) plus a warning if it is huge."""
        sized = []
        for item in self.list_items():
            size = item["size_bytes"] if item["type"] == "file" else _folder_size(item["path"])
            sized.append({"name": item["name"], "type": item["type"], "size_bytes": size})
        total = sum(i["size_bytes"] for i in sized)
        sized.sort(key=lambda i: i["size_bytes"], reverse=True)
        warning = None
        if total > warn_bytes:
            warning = (f"WARNING: Downloads is {human_size(total)} "
                       f"(limit {human_size(warn_bytes)}). Consider cleaning it up.")
        return {"total_bytes": total, "total": human_size(total), "count": len(sized),
                "largest": sized[:top], "warning": warning}

    def save(self, filename="downloads.json"):
        """Save the listing to <data_dir>/<filename>. Returns the file path."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self.data_dir / filename
        items = self.list_items()
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "directory": str(self.downloads_dir),
            "folders": [i for i in items if i["type"] == "folder"],
            "files": [i for i in items if i["type"] == "file"],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return path


if __name__ == "__main__":
    service = DownloadsService()
    for item in service.list_items():
        print(f"[{item['type']:6}] {item['name']}")
    print(f"\nSaved to {service.save()}")
