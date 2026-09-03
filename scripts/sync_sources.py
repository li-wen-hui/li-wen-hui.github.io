#!/usr/bin/env python3
"""
Generate academic master data.

Source of truth:
- content/profile.yml
- content/publications.yml
- content/news.yml

External services only provide metadata.
They never add or keep deleted papers.
"""

from pathlib import Path
import json
import yaml
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
CONTENT = ROOT / "content"


def load_yaml(path):
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def main():
    print("Sync academic data")

    site_cfg = load_yaml(ROOT / "config" / "site.yml")
    profile = load_yaml(CONTENT / "profile.yml")
    publications = load_yaml(CONTENT / "publications.yml")
    news = load_yaml(CONTENT / "news.yml")

    master = {
        "site": site_cfg.get("site", {}),
        "profile": profile.get("profile", {}),
        "publications": publications.get("publications", []),
        "news": news.get("news", []),
        "sync": {
            "updated": datetime.now().strftime("%Y-%m-%d"),
            "orcid": site_cfg.get("sync", {}).get("orcid", {}),
            "crossref": site_cfg.get("sync", {}).get("crossref", {}),
            "scholar": site_cfg.get("sync", {}).get("scholar", {}),
            "github": site_cfg.get("sync", {}).get("github", {})
        }
    }

    save_json(CACHE / "master.json", master)

    print(
        f"Updated master.json: {len(master['publications'])} publications"
    )


if __name__ == "__main__":
    main()
