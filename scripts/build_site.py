#!/usr/bin/env python3
"""Build the complete static researcher website into dist/."""
from __future__ import annotations

import html
import json
import math
import re
import shutil
from datetime import datetime
from pathlib import Path

import yaml
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
CACHE = ROOT / "data" / "cache"
SITE = ROOT / "site"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(text) -> str:
    return html.escape(str(text or ""))


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:56] or "publication"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def generate_cover(pub: dict, out: Path) -> None:
    # Generate a restrained academic thumbnail when no manual figure is supplied.
    venue = esc(pub.get("venue_short") or pub.get("venue") or "PUBLICATION")
    title = pub.get("title") or "Selected Publication"
    words = title.split()
    lines, current = [], []
    for w in words:
        if len(" ".join(current + [w])) > 31 and current:
            lines.append(" ".join(current))
            current = [w]
        else:
            current.append(w)
        if len(lines) == 2:
            break
    if current and len(lines) < 3:
        lines.append(" ".join(current))
    lines = lines[:3]
    palette = [
        ("#e8f0f6","#315c7d","#7396af"),
        ("#edf1f0","#496c67","#8ba49e"),
        ("#f3eee9","#755c49","#aa8a72"),
        ("#eceff5","#4d6386","#8294af"),
    ]
    bg, ink, accent = palette[(int(pub.get("number", "1")) - 1) % len(palette)]
    tspans = "".join(f'<tspan x="46" dy="39">{esc(line)}</tspan>' for line in lines)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 460">
<rect width="720" height="460" fill="{bg}"/>
<rect x="1" y="1" width="718" height="458" fill="none" stroke="#cfd9e2" stroke-width="2"/>
<g opacity=".28" stroke="{accent}" fill="none">
  <circle cx="555" cy="215" r="116"/><circle cx="555" cy="215" r="78"/><circle cx="555" cy="215" r="42"/>
  <path d="M435 215h240M555 95v240"/><path d="M467 138c62 39 116 102 162 156"/>
</g>
<g fill="{ink}"><rect x="46" y="42" width="70" height="28" rx="3" opacity=".95"/></g>
<g font-family="Arial,Helvetica,sans-serif">
  <text x="81" y="62" text-anchor="middle" font-size="16" font-weight="700" fill="#ffffff">{venue}</text>
  <text x="46" y="133" font-size="30" font-weight="700" fill="{ink}">{tspans}</text>
  <text x="46" y="393" font-size="17" fill="#68788a">WENHUI LI - SELECTED PUBLICATION</text>
  <text x="633" y="392" font-size="62" font-weight="700" fill="{ink}" opacity=".12">{esc(pub.get("number"))}</text>
</g>
</svg>'''
    write(out, svg)

def generate_og(master: dict, out: Path) -> None:
    profile = master["profile"]
    interests = master.get("curated", {}).get("interests", [])[:3]
    W,H=1200,630
    im=Image.new("RGB",(W,H),(245,247,250))
    d=ImageDraw.Draw(im)
    for y in range(H):
        t=y/(H-1); col=(int(245-4*t),int(247-4*t),int(250-3*t)); d.line((0,y,W,y),fill=col)
    glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow); gd.ellipse((720,-80,1280,480),fill=(92,133,164,55)); glow=glow.filter(ImageFilter.GaussianBlur(75)); im=Image.alpha_composite(im.convert("RGBA"),glow); d=ImageDraw.Draw(im)
    font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold_path="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    def ft(path,size):
        try:return ImageFont.truetype(path,size)
        except:return ImageFont.load_default()
    f1,f2,f3=ft(bold_path,76),ft(font_path,31),ft(font_path,23)
    d.text((72,105),str(profile.get("name") or "Wenhui Li"),font=f1,fill=(32,51,70,255))
    d.text((76,210),"Academic Homepage",font=f2,fill=(55,92,121,255))
    d.text((76,275),f"{profile.get('affiliation','')} · {profile.get('department','')}",font=f3,fill=(102,117,138,255))
    d.text((76,326)," · ".join(interests),font=f3,fill=(102,117,138,255))
    for rad,alpha in [(150,80),(110,95),(72,120)]: d.ellipse((930-rad,310-rad,930+rad,310+rad),outline=(82,122,154,alpha),width=3)
    d.line((780,310,1080,310),fill=(82,122,154,70),width=2);d.line((930,160,930,460),fill=(82,122,154,70),width=2)
    d.rounded_rectangle((76,455,400,515),radius=17,outline=(82,122,154,255),width=2);d.text((98,470),"li-wen-hui.github.io",font=f3,fill=(45,74,99,255))
    out.parent.mkdir(parents=True,exist_ok=True);im.convert("RGB").save(out.with_suffix(".png"),quality=95)


def generate_cv(master: dict, out_pdf: Path) -> None:
    profile = master["profile"]
    curated = master.get("curated", {})
    pubs = master.get("publications", [])

    doc = SimpleDocTemplate(
        str(out_pdf), pagesize=A4,
        rightMargin=17*mm, leftMargin=17*mm, topMargin=15*mm, bottomMargin=15*mm,
        title=f"{profile.get('name')} - Academic CV",
        author=profile.get("name", ""),
    )
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle("Name", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21, leading=24, textColor=colors.HexColor("#163a59"), spaceAfter=4)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontName="Helvetica", fontSize=9.5, leading=13, textColor=colors.HexColor("#4c6071"), spaceAfter=2)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#163a59"), spaceBefore=9, spaceAfter=6, borderWidth=0, borderPadding=0)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontName="Helvetica", fontSize=9.2, leading=13, textColor=colors.HexColor("#202a33"), spaceAfter=5)
    pub_style = ParagraphStyle("Pub", parent=body_style, leftIndent=0, firstLineIndent=0, spaceAfter=7)
    small_style = ParagraphStyle("Small", parent=body_style, fontSize=8.4, leading=11.5, textColor=colors.HexColor("#526578"))

    story = []
    story.append(Paragraph(esc(profile.get("name")), name_style))
    contact = " · ".join(filter(None, [profile.get("headline"), profile.get("affiliation"), profile.get("email"), profile.get("location")]))
    story.append(Paragraph(esc(contact), sub_style))
    links = []
    if profile.get("scholar_url"): links.append(f'Google Scholar: {esc(profile["scholar_url"])}')
    if profile.get("orcid_url"): links.append(f'ORCID: {esc(profile["orcid_url"])}')
    if profile.get("github_username"): links.append(f'GitHub: https://github.com/{esc(profile["github_username"])}')
    if links: story.append(Paragraph(" · ".join(links), small_style))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("Research Profile", section_style))
    story.append(Paragraph(esc(curated.get("bio", "")), body_style))
    interests = curated.get("interests", [])
    if interests: story.append(Paragraph("<b>Research interests:</b> " + esc(", ".join(interests)), body_style))

    story.append(Paragraph("Education", section_style))
    for e in curated.get("education", []):
        data = [[Paragraph(f'<b>{esc(e.get("school"))}</b><br/>{esc(e.get("degree"))}<br/><font color="#526578">{esc(e.get("detail"))}</font>', body_style), Paragraph(f'<b>{esc(e.get("period"))}</b><br/>GPA: {esc(e.get("gpa", ""))}', small_style)]]
        t = Table(data, colWidths=[145*mm, 28*mm])
        t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("ALIGN",(1,0),(1,-1),"RIGHT"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
        story.append(t)

    story.append(Paragraph("Publications", section_style))
    for i, p in enumerate(pubs, 1):
        authors = esc(strip_tags(p.get("authors_html", "")))
        title = esc(p.get("title", ""))
        venue = esc(p.get("venue", ""))
        year = esc(p.get("year", ""))
        status = esc(p.get("status", ""))
        doi = esc(p.get("doi", ""))
        extra = " · ".join(x for x in [venue, str(year), status] if x)
        doi_line = f'<br/><font color="#526578">DOI: {doi}</font>' if doi else ""
        story.append(Paragraph(f'<b>[{i}] {title}</b><br/>{authors}<br/><i>{extra}</i>{doi_line}', pub_style))

    if curated.get("honors"):
        story.append(Paragraph("Honors", section_style))
        for h in curated["honors"]:
            story.append(Paragraph(f'<b>{esc(h.get("title"))}</b> - {esc(h.get("organization"))} <font color="#526578">({esc(h.get("year"))})</font>', body_style))

    if curated.get("service"):
        story.append(Paragraph("Academic Service", section_style))
        for s in curated["service"]:
            story.append(Paragraph(f'<b>{esc(s.get("role"))}</b>, {esc(s.get("organization"))} <font color="#526578">({esc(s.get("period"))})</font><br/>{esc(s.get("detail"))}', body_style))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#718092"))
        canvas.drawString(17*mm, 8*mm, f"Automatically generated from the same master data as {profile.get('name')}'s academic homepage.")
        canvas.drawRightString(A4[0]-17*mm, 8*mm, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def bib_database(master: dict) -> str:
    return "\n\n".join((p.get("bibtex") or "").strip() for p in master.get("publications", []) if p.get("bibtex")) + "\n"


def rss_feed(master: dict, base_url: str) -> str:
    items = []
    for n in master.get("news", [])[:10]:
        items.append(f'''<item><title>{esc(n.get('date'))} academic update</title><link>{esc(base_url)}</link><guid>{esc(base_url)}#{slug(n.get('date','')+n.get('text',''))}</guid><description>{esc(n.get('text'))}</description></item>''')
    return f'''<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{esc(master['profile'].get('name'))} - Academic Updates</title><link>{esc(base_url)}</link><description>{esc(master['site'].get('description'))}</description>{''.join(items)}</channel></rss>'''


def main() -> None:
    master_path = CACHE / "master.json"
    if not master_path.exists():
        raise SystemExit("Run scripts/sync_sources.py first")
    master = load_json(master_path)
    site_cfg = load_yaml(ROOT / "config" / "site.yml")

    if DIST.exists(): shutil.rmtree(DIST)
    shutil.copytree(SITE, DIST)
    (DIST / "assets" / "data").mkdir(parents=True, exist_ok=True)
    (DIST / "assets" / "img" / "covers").mkdir(parents=True, exist_ok=True)

    # Site data
    dump = json.dumps(master, ensure_ascii=False, separators=(",", ":"))
    write(DIST / "assets" / "data" / "site.json", dump)
    write(DIST / "academic-profile.json", json.dumps(master, ensure_ascii=False, indent=2))
    write(DIST / "publications.bib", bib_database(master))

    # Covers
    for p in master.get("publications", []):
        cover_name = f"{p.get('number','00')}-{slug(p.get('title',''))}.svg"
        p["cover"] = f"assets/img/covers/{cover_name}"
        generate_cover(p, DIST / p["cover"])
    # Rewrite data now with cover paths
    write(DIST / "assets" / "data" / "site.json", json.dumps(master, ensure_ascii=False, separators=(",", ":")))
    write(DIST / "academic-profile.json", json.dumps(master, ensure_ascii=False, indent=2))

    # CV
    cv_name = site_cfg.get("auto_cv", {}).get("filename", "Wenhui_Li_CV.pdf")
    if site_cfg.get("auto_cv", {}).get("enabled", True):
        generate_cv(master, DIST / cv_name)

    base_url = (master.get("site", {}).get("url") or "https://li-wen-hui.github.io/").rstrip("/") + "/"
    custom = (master.get("site", {}).get("custom_domain") or "").strip()
    if custom:
        host = custom.replace("https://", "").replace("http://", "").strip("/")
        write(DIST / "CNAME", host + "\n")
        base_url = "https://" + host + "/"

    # SEO supporting files
    write(DIST / "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {base_url}sitemap.xml\n")
    write(DIST / "sitemap.xml", f'''<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{esc(base_url)}</loc><changefreq>weekly</changefreq><priority>1.0</priority></url></urlset>''')
    write(DIST / "rss.xml", rss_feed(master, base_url))
    write(DIST / "humans.txt", f"Wenhui Li\nAcademic homepage\nBuilt automatically from ORCID/Crossref/Scholar/GitHub + curated YAML.\n{base_url}\n")
    write(DIST / "llms.txt", f"# {master['profile'].get('name')}\n\nAcademic homepage: {base_url}\nResearch interests: {', '.join(master.get('curated',{}).get('interests',[]))}\nPublications metadata: {base_url}academic-profile.json\nBibTeX: {base_url}publications.bib\n")
    cff = f"""cff-version: 1.2.0\nmessage: \"If you use material from this academic homepage, please cite the original publications listed on the site.\"\ntitle: \"{master['profile'].get('name')} Academic Homepage\"\nauthors:\n  - family-names: \"Li\"\n    given-names: \"Wenhui\"\nurl: \"{base_url}\"\n"""
    write(DIST / "CITATION.cff", cff)

    generate_og(master, DIST / "assets" / "img" / "og-image")

    # Inject SEO/config placeholders into index template.
    idx = (DIST / "index.html").read_text(encoding="utf-8")
    replacements = {
        "__TITLE__": master["site"].get("title") or "Wenhui Li | Academic Homepage",
        "__DESCRIPTION__": master["site"].get("description") or "Academic homepage",
        "__CANONICAL__": base_url,
        "__OG_IMAGE__": base_url + "assets/img/og-image.png",
        "__NAME__": master["profile"].get("name") or "Wenhui Li",
        "__AFFILIATION__": master["profile"].get("affiliation") or "Henan University",
        "__EMAIL__": master["profile"].get("email") or "",
    }
    for a,b in replacements.items(): idx = idx.replace(a, esc(b))
    write(DIST / "index.html", idx)

    # Web manifest
    write(DIST / "site.webmanifest", json.dumps({
        "name": master["site"].get("title"), "short_name": master["profile"].get("name"),
        "start_url": "./", "display": "standalone", "background_color": "#f5f7fa",
        "theme_color": "#f5f7fa", "icons": [{"src":"assets/img/favicon.svg","sizes":"any","type":"image/svg+xml"}]
    }, ensure_ascii=False, indent=2))

    print(f"Built site in {DIST}")
    print(f"Publications: {len(master.get('publications', []))}")
    print(f"CV: {DIST / cv_name}")


if __name__ == "__main__":
    main()
