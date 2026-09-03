# V8 Automatic Academic Website Architecture

Goal:
- profile.yml: manual identity information only
- publications.yml: single source of publication records
- activity/news: generated automatically
- Scholar/Crossref/ORCID/GitHub: metadata synchronization

Workflow:
content -> sync -> cache -> build -> GitHub Pages

No separate manual news maintenance is required.
