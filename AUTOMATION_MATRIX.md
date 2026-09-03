# V5 Automation Matrix

| Item | Automation | Source / mechanism | Manual fallback |
|---|---|---|---|
| Publication discovery | Automatic | ORCID Works | `content/publications.yml` |
| DOI metadata | Automatic | Crossref REST API | YAML override |
| Title/authors/journal/year | Automatic with DOI | Crossref | YAML override |
| Citations | Automatic | Scholar via SerpApi | `—` |
| h-index / i10-index | Automatic | Scholar via SerpApi | `—` |
| Citation history chart | Automatic | Scholar via SerpApi | Empty state |
| Per-paper Cited by | Automatic title match | Scholar | Hidden |
| Code link | Automatic if `github_repo` set | GitHub API | `code_url` |
| GitHub Stars | Automatic if `github_repo` set | GitHub API | Hidden |
| BibTeX | Automatic | Master metadata | Always generated |
| Publication abstract cover | Automatic | V5 SVG generator | Replace with custom image later |
| CV PDF | Automatic | Master data -> ReportLab | Can disable |
| publications.bib | Automatic | Master data | None needed |
| academic-profile.json | Automatic | Master data | None needed |
| sitemap / robots | Automatic | Build script | None needed |
| RSS | Automatic from curated News | Build script | Edit News |
| Open Graph | Automatic metadata | Build script | Replace share image later |
| Deployment | Automatic | GitHub Actions + Pages | Manual workflow run |
| Weekly refresh | Automatic | GitHub Actions schedule | Manual workflow run |
| About | Curated | YAML | Manual by design |
| Research Interests | Curated | YAML | Manual by design |
| News importance | Curated | YAML | Manual by design |
| Custom domain DNS | Semi-automatic | GitHub Pages + DNS provider | Must configure DNS once |
