#!/usr/bin/env python3
"""Fetch external academic metadata and build data/cache/master.json.

Sources are optional and fail-soft:
- ORCID Public API (requires ORCID_CLIENT_ID + ORCID_CLIENT_SECRET + profile.orcid_id)
- Crossref REST API (public; DOI enrichment)
- Google Scholar via SerpApi (requires SERPAPI_KEY + scholar author ID)
- GitHub REST API (public; GITHUB_TOKEN improves rate limit)

Manual YAML always wins on fields explicitly supplied by the user.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

UA = "WenhuiLiAcademicHomepage/6.0 (+https://li-wen-hui.github.io/)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def norm_title(value: str | None) -> str:
    value = html.unescape(value or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def clean_doi(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.I)
    return value.strip()


def env_or_config(env_name: str, config_value: str | None) -> str:
    return (os.environ.get(env_name) or config_value or "").strip()


def request_json(method: str, url: str, *, headers=None, data=None, timeout=35) -> dict | list | None:
    try:
        r = SESSION.request(method, url, headers=headers, data=data, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        print(f"[warn] {method} {url}: {exc}", file=sys.stderr)
        return None


def get_orcid_token(client_id: str, client_secret: str) -> str:
    if not client_id or not client_secret:
        return ""
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "/read-public",
        "grant_type": "client_credentials",
    }
    try:
        r = SESSION.post(
            "https://orcid.org/oauth/token",
            data=payload,
            headers={"Accept": "application/json"},
            timeout=35,
        )
        r.raise_for_status()
        return r.json().get("access_token", "")
    except Exception as exc:
        print(f"[warn] ORCID token: {exc}", file=sys.stderr)
        return ""


def sync_orcid(site_cfg: dict) -> dict:
    profile = site_cfg.get("profile", {})
    sync_cfg = site_cfg.get("sync", {}).get("orcid", {})
    orcid_id = env_or_config("ORCID_ID", profile.get("orcid_id"))
    if not sync_cfg.get("enabled", True) or not orcid_id:
        return {"configured": False, "orcid_id": orcid_id, "works": []}

    client_id = os.environ.get("ORCID_CLIENT_ID", "").strip()
    client_secret = os.environ.get("ORCID_CLIENT_SECRET", "").strip()
    token = get_orcid_token(client_id, client_secret)
    if not token:
        return {
            "configured": False,
            "orcid_id": orcid_id,
            "works": [],
            "note": "ORCID_ID is set but API credentials are missing or invalid.",
        }

    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    raw = request_json("GET", f"https://pub.orcid.org/v3.0/{orcid_id}/works", headers=headers)
    works: list[dict] = []
    if isinstance(raw, dict):
        for group in raw.get("group", []) or []:
            summaries = group.get("work-summary", []) or []
            if not summaries:
                continue
            s = summaries[0]
            title = (((s.get("title") or {}).get("title") or {}).get("value") or "").strip()
            ext = s.get("external-ids", {}).get("external-id", []) or []
            doi = ""
            for e in ext:
                if (e.get("external-id-type") or "").lower() == "doi":
                    doi = clean_doi(e.get("external-id-value"))
                    break
            pub_date = s.get("publication-date") or {}
            year = ((pub_date.get("year") or {}).get("value"))
            url = ((s.get("url") or {}).get("value"))
            works.append({
                "title": title,
                "doi": doi,
                "year": int(year) if str(year).isdigit() else None,
                "url": url,
                "type": s.get("type"),
                "put_code": s.get("put-code"),
            })
    result = {
        "configured": True,
        "orcid_id": orcid_id,
        "profile_url": f"https://orcid.org/{orcid_id}",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "works": works,
    }
    dump_json(CACHE / "orcid.json", result)
    return result


def crossref_authors_to_html(authors: list[dict], user_name: str) -> str:
    parts = []
    user_norm = norm_title(user_name)
    for a in authors or []:
        given = (a.get("given") or "").strip()
        family = (a.get("family") or "").strip()
        name = " ".join(x for x in [given, family] if x).strip()
        if not name:
            continue
        if norm_title(name) == user_norm:
            parts.append(f"<strong>{html.escape(name)}</strong>")
        else:
            parts.append(html.escape(name))
    return ", ".join(parts)


def crossref_year(msg: dict) -> int | None:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        val = msg.get(key) or {}
        parts = val.get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            try:
                return int(parts[0][0])
            except Exception:
                pass
    return None


def sync_crossref(site_cfg: dict, dois: set[str]) -> dict[str, dict]:
    cfg = site_cfg.get("sync", {}).get("crossref", {})
    if not cfg.get("enabled", True):
        return {}
    email = cfg.get("polite_email") or site_cfg.get("profile", {}).get("email", "")
    user_name = site_cfg.get("profile", {}).get("name", "")
    out: dict[str, dict] = {}
    for doi in sorted(d for d in dois if d):
        url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
        if email:
            url += f"?mailto={quote(email)}"
        raw = request_json("GET", url)
        if not isinstance(raw, dict) or not isinstance(raw.get("message"), dict):
            continue
        m = raw["message"]
        title = (m.get("title") or [""])[0]
        container = (m.get("container-title") or [""])[0]
        link = ""
        for item in m.get("link", []) or []:
            if item.get("URL"):
                link = item["URL"]
                break
        out[doi] = {
            "doi": doi,
            "title": title,
            "authors_html": crossref_authors_to_html(m.get("author") or [], user_name),
            "venue": container,
            "year": crossref_year(m),
            "publisher": m.get("publisher"),
            "volume": m.get("volume"),
            "issue": m.get("issue"),
            "pages": m.get("page"),
            "type": m.get("type"),
            "url": m.get("URL") or (f"https://doi.org/{doi}"),
            "fulltext_url": link,
        }
        time.sleep(0.08)
    result = {"updated_at": datetime.now(timezone.utc).isoformat(), "works": out}
    dump_json(CACHE / "crossref.json", result)
    return out


def sync_scholar(site_cfg: dict) -> dict:
    sync_cfg = site_cfg.get("sync", {}).get("scholar", {})
    profile = site_cfg.get("profile", {})
    author_id = env_or_config("SCHOLAR_AUTHOR_ID", profile.get("scholar_author_id"))
    api_key = os.environ.get("SERPAPI_KEY", "").strip()
    if not sync_cfg.get("enabled", True) or not author_id or not api_key:
        return {"configured": False, "author_id": author_id, "articles": [], "annual_citations": []}
    params = {
        "engine": "google_scholar_author",
        "author_id": author_id,
        "hl": "en",
        "num": 100,
        "api_key": api_key,
        "output": "json",
    }
    try:
        r = SESSION.get("https://serpapi.com/search", params=params, timeout=60)
        r.raise_for_status()
        raw = r.json()
    except Exception as exc:
        print(f"[warn] Scholar: {exc}", file=sys.stderr)
        return {"configured": False, "author_id": author_id, "articles": [], "annual_citations": []}

    table = (raw.get("cited_by") or {}).get("table") or []
    metrics = {"citations": None, "h_index": None, "i10_index": None}
    for row in table:
        label = norm_title(str(row.get("name") or row.get("key") or ""))
        if not label:
            # SerpApi often returns keys as labels.
            for k in row.keys():
                nk = norm_title(k)
                if "citation" in nk:
                    label = "citations"
                elif nk in {"h index", "indice h", "hindex"}:
                    label = "h index"
                elif "i10" in nk:
                    label = "i10 index"
        def numeric(v):
            if isinstance(v, dict):
                return v.get("all") or v.get("since_2019") or v.get("since_2021")
            return v if isinstance(v, (int, float)) else None
        values = [numeric(v) for v in row.values()]
        value = next((v for v in values if v is not None), None)
        if "citation" in label:
            metrics["citations"] = value
        elif label == "h index":
            metrics["h_index"] = value
        elif "i10" in label:
            metrics["i10_index"] = value

    graph = []
    for p in (raw.get("cited_by") or {}).get("graph", []) or []:
        try:
            graph.append({"year": int(p.get("year")), "citations": int(p.get("citations") or 0)})
        except Exception:
            pass

    articles = []
    for a in raw.get("articles", []) or []:
        cited = a.get("cited_by") or {}
        articles.append({
            "title": a.get("title") or "",
            "year": a.get("year"),
            "citations": cited.get("value", 0) if isinstance(cited, dict) else 0,
            "link": a.get("link"),
        })
    result = {
        "configured": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "profile_url": f"https://scholar.google.com/citations?user={author_id}",
        **metrics,
        "annual_citations": graph,
        "articles": articles,
    }
    dump_json(CACHE / "scholar.json", result)
    return result


def sync_github(site_cfg: dict) -> dict:
    cfg = site_cfg.get("sync", {}).get("github", {})
    username = site_cfg.get("profile", {}).get("github_username", "").strip()
    if not cfg.get("enabled", True) or not username:
        return {"configured": False, "repos": []}
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    raw = request_json("GET", f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated", headers=headers)
    repos = []
    if not isinstance(raw, list):
        return {"configured": False, "username": username, "repos": []}
    if isinstance(raw, list):
        for r in raw:
            repos.append({
                "name": r.get("name"),
                "url": r.get("html_url"),
                "description": r.get("description"),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "language": r.get("language"),
                "updated_at": r.get("updated_at"),
            })
    result = {"configured": True, "username": username, "updated_at": datetime.now(timezone.utc).isoformat(), "repos": repos}
    dump_json(CACHE / "github.json", result)
    return result


def simple_bibtex(pub: dict) -> str:
    key = re.sub(r"[^a-z0-9]", "", norm_title(pub.get("id") or pub.get("title")))[:24] or "publication"
    title = (pub.get("title") or "").replace("{", "").replace("}", "")
    venue = pub.get("venue") or ""
    year = pub.get("year") or ""
    doi = pub.get("doi") or ""
    lines = [f"@article{{{key},", f"  title = {{{title}}},", f"  journal = {{{venue}}},", f"  year = {{{year}}},"]
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)


def best_scholar_match(title: str, scholar: dict) -> dict | None:
    nt = norm_title(title)
    if not nt:
        return None
    exact = None
    contains = None
    for a in scholar.get("articles", []) or []:
        at = norm_title(a.get("title"))
        if at == nt:
            exact = a
            break
        if at and (at in nt or nt in at):
            contains = contains or a
    return exact or contains


def merge_master(site_cfg: dict, manual_profile: dict, news: dict, manual_pubs: list[dict], orcid: dict, crossref: dict, scholar: dict, github: dict) -> dict:
    profile = deepcopy(site_cfg.get("profile", {}))
    if orcid.get("configured"):
        profile["orcid_url"] = orcid.get("profile_url") or profile.get("orcid_url")
    if scholar.get("configured"):
        profile["scholar_url"] = scholar.get("profile_url") or profile.get("scholar_url")

    # ORCID discoveries first, then manual publications override/merge.
    discovered = []
    for w in orcid.get("works", []) or []:
        doi = clean_doi(w.get("doi"))
        cr = crossref.get(doi, {}) if doi else {}
        title = cr.get("title") or w.get("title") or ""
        if not title:
            continue
        discovered.append({
            "id": "auto-" + re.sub(r"[^a-z0-9]+", "-", norm_title(title))[:48].strip("-"),
            "title": title,
            "authors_html": cr.get("authors_html") or "",
            "venue": cr.get("venue") or "",
            "venue_short": "",
            "year": cr.get("year") or w.get("year"),
            "status": "Published" if doi else "Public Work",
            "status_class": "published",
            "doi": doi,
            "paper_url": cr.get("fulltext_url") or w.get("url") or cr.get("url") or "",
            "code_url": "",
            "project_url": "",
            "github_repo": "",
            "tags": [],
            "featured": False,
            "category": "Other Publications",
            "source": "orcid",
        })

    merged: list[dict] = []
    seen_doi: set[str] = set()
    seen_title: set[str] = set()
    for p in discovered:
        d = clean_doi(p.get("doi")); t = norm_title(p.get("title"))
        if d: seen_doi.add(d)
        seen_title.add(t)
        merged.append(p)

    for manual in manual_pubs:
        m = deepcopy(manual)
        doi = clean_doi(m.get("doi")); title_norm = norm_title(m.get("title"))
        target = None
        for p in merged:
            if doi and clean_doi(p.get("doi")) == doi:
                target = p; break
            if title_norm and norm_title(p.get("title")) == title_norm:
                target = p; break
        cr = crossref.get(doi, {}) if doi else {}
        enriched = {}
        if cr:
            enriched.update({
                "title": cr.get("title"),
                "authors_html": cr.get("authors_html"),
                "venue": cr.get("venue"),
                "year": cr.get("year"),
                "paper_url": cr.get("fulltext_url") or cr.get("url"),
            })
        if target is None:
            target = {k: v for k, v in enriched.items() if v not in (None, "")}
            target["source"] = "manual"
            merged.append(target)
        else:
            for k, v in enriched.items():
                if v not in (None, "") and not target.get(k):
                    target[k] = v
        # Manual explicit values win, blank manual values do not erase enriched values.
        for k, v in m.items():
            if v not in (None, "", []):
                target[k] = v
        if doi:
            target["doi"] = doi

    repo_map = {r.get("name", "").lower(): r for r in github.get("repos", []) or []}
    for p in merged:
        p.setdefault("id", "pub-" + re.sub(r"[^a-z0-9]+", "-", norm_title(p.get("title")))[:48].strip("-"))
        p.setdefault("venue_short", "")
        p.setdefault("tags", [])
        p.setdefault("featured", False)
        p.setdefault("category", "Other Publications")
        p.setdefault("status", "Published")
        p.setdefault("status_class", "published")
        p.setdefault("doi", "")
        p.setdefault("paper_url", "")
        p.setdefault("code_url", "")
        p.setdefault("project_url", "")
        repo_name = (p.get("github_repo") or "").strip()
        if repo_name and repo_name.lower() in repo_map:
            repo = repo_map[repo_name.lower()]
            if not p.get("code_url"):
                p["code_url"] = repo.get("url") or ""
            p["github_stars"] = repo.get("stars", 0)
        sm = best_scholar_match(p.get("title", ""), scholar)
        p["citations"] = sm.get("citations") if sm else None
        p["scholar_url"] = sm.get("link") if sm else ""
        if p.get("doi"):
            p["doi_url"] = f"https://doi.org/{p['doi']}"
        else:
            p["doi_url"] = ""
        p["bibtex"] = simple_bibtex(p)

    def sort_key(p):
        order = p.get("order")
        if order is not None:
            return (0, int(order), 0, "")
        return (1, 9999, -int(p.get("year") or 0), p.get("title") or "")
    merged.sort(key=sort_key)
    for idx, p in enumerate(merged, 1):
        p["number"] = f"{idx:02d}"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site": site_cfg.get("site", {}),
        "profile": profile,
        "curated": manual_profile,
        "news": news.get("news", []),
        "publications": merged,
        "metrics": {
            "publications": len(merged),
            "citations": scholar.get("citations"),
            "h_index": scholar.get("h_index"),
            "i10_index": scholar.get("i10_index"),
            "annual_citations": scholar.get("annual_citations", []),
            "scholar_updated_at": scholar.get("updated_at"),
        },
        "analytics": site_cfg.get("analytics", {}),
        "sync_state": {
            "orcid": bool(orcid.get("configured")),
            "crossref": bool(crossref),
            "scholar": bool(scholar.get("configured")),
            "github": bool(github.get("configured")),
        },
    }


def main() -> None:
    site_cfg = load_yaml(ROOT / "config" / "site.yml")
    profile = load_yaml(ROOT / "content" / "profile.yml")
    news = load_yaml(ROOT / "content" / "news.yml")
    manual_pubs = load_yaml(ROOT / "content" / "publications.yml").get("publications", [])

    orcid = sync_orcid(site_cfg)
    doi_set = {clean_doi(p.get("doi")) for p in manual_pubs if p.get("doi")}
    doi_set.update(clean_doi(w.get("doi")) for w in orcid.get("works", []) if w.get("doi"))
    crossref = sync_crossref(site_cfg, doi_set)
    scholar = sync_scholar(site_cfg)
    github = sync_github(site_cfg)
    master = merge_master(site_cfg, profile, news, manual_pubs, orcid, crossref, scholar, github)
    dump_json(CACHE / "master.json", master)
    print(f"Built data/cache/master.json with {len(master['publications'])} publications")
    print("Sync state:", master["sync_state"])


if __name__ == "__main__":
    main()
