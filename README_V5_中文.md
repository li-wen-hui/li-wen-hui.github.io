# Wenhui Li Researcher Website V5 - 全自动研究者主页

这一版不是“静态 HTML 升级”，而是把主页重构成一个小型自动化学术数据系统。

## V5 的核心原则

你只维护少量“必须由本人决定”的内容：

- About / Research Interests
- News 中真正重要的消息
- Under Review / In Preparation 等无法由 DOI 数据库得知的状态
- 你希望展示的论文顺序、标签、代表图和 Code / Project 链接

其余尽量自动：

- ORCID -> 自动发现公开 Works
- Crossref -> DOI 元数据补全
- Google Scholar / SerpApi -> Citations、h-index、i10-index、年度引用曲线、单篇 Cited by
- GitHub API -> 论文代码仓库链接和 Stars（填写 `github_repo` 后）
- BibTeX -> 自动生成
- 论文卡片封面 -> 自动生成统一视觉封面
- CV PDF -> 和网页共用同一套 master data 自动生成
- publications.bib -> 自动生成
- academic-profile.json -> 自动生成
- RSS / sitemap / robots / llms.txt / humans.txt -> 自动生成
- GitHub Actions -> 每次 push 自动构建部署；每周自动同步外部数据并重新部署

---

# 一、仓库最终结构

```text
li-wen-hui.github.io/
├── config/
│   └── site.yml                  # 网站、身份、同步、统计、域名总配置
│
├── content/
│   ├── profile.yml               # About、兴趣、教育、荣誉、学术服务
│   ├── news.yml                  # 只维护重要 News
│   └── publications.yml          # 手工种子/覆盖项；DOI 后可自动补全
│
├── scripts/
│   ├── sync_sources.py           # ORCID/Crossref/Scholar/GitHub 同步
│   ├── build_site.py             # 生成网页、CV、BibTeX、SEO 文件等
│   └── local_build.sh            # 本地一键构建
│
├── site/                          # 页面模板；日常基本不用改
│   ├── index.html
│   ├── 404.html
│   └── assets/
│       ├── css/style.css
│       ├── js/app.js
│       └── img/profile.jpg
│
├── .github/workflows/
│   └── deploy.yml                # 自动同步 + 构建 + GitHub Pages 部署
│
├── requirements.txt
└── README_V5_中文.md
```

`dist/` 不需要提交；GitHub Actions 每次自动生成后直接部署。

---

# 二、你以后主要只改 3 个文件

## 1. `config/site.yml`

填个人账号和自动化配置：

```yaml
profile:
  orcid_id: "0000-0000-0000-0000"
  scholar_author_id: "xxxxxxxxxxxx"
  scholar_url: "https://scholar.google.com/citations?user=xxxxxxxxxxxx"
  orcid_url: "https://orcid.org/0000-0000-0000-0000"
```

以后买域名：

```yaml
site:
  url: "https://www.wenhuili.com/"
  custom_domain: "www.wenhuili.com"
```

V5 构建时会自动生成真正的 `CNAME`。

## 2. `content/profile.yml`

只管理你本人决定的内容：About、Research Interests、Education、Honors、Service。

## 3. `content/news.yml`

重要消息手工维护即可。不要把 News 完全交给 API，因为“什么值得作为新闻”属于学术叙事，而不是纯数据库字段。

---

# 三、论文现在如何自动化

`content/publications.yml` 里可以先只写最少信息。

例如以后已正式出版：

```yaml
- id: "my-new-paper"
  order: 1
  doi: "10.xxxx/xxxxx"
  tags: ["Image Representation", "Orthogonal Moments"]
  code_url: "https://github.com/..."
```

构建时：

```text
DOI
 ↓
Crossref
 ↓
Title / Authors / Journal / Year / URL
 ↓
Scholar title matching
 ↓
Cited by
 ↓
GitHub repo matching（如填写 github_repo）
 ↓
BibTeX
 ↓
Publication Card + Cover + CV + publications.bib
```

对于 **Under Review** 论文，因为不存在 DOI/Crossref 正式记录，继续保留手工 title / venue / status 即可。

---

# 四、ORCID 自动发现新论文

V5 支持从 ORCID Works 自动发现论文，然后用 DOI 去 Crossref 补全。

GitHub 仓库：

`Settings -> Secrets and variables -> Actions`

## Variables

添加：

```text
ORCID_ID
```

值例如：

```text
0000-0000-0000-0000
```

## Secrets

添加：

```text
ORCID_CLIENT_ID
ORCID_CLIENT_SECRET
```

这是 ORCID Public API 的 client credentials。

如果暂时没有 ORCID 或 credentials，**网站不会报错**，只会自动回退到你 YAML 中的手工论文。

---

# 五、Google Scholar 自动引用

GitHub Actions Variables 添加：

```text
SCHOLAR_AUTHOR_ID
```

例如 Scholar 地址：

```text
https://scholar.google.com/citations?user=ABC123AAAAJ
```

那么：

```text
SCHOLAR_AUTHOR_ID = ABC123AAAAJ
```

Secrets 添加：

```text
SERPAPI_KEY
```

之后每周自动刷新：

- Citations
- h-index
- i10-index
- Citations by year
- 单篇论文 Cited by

没有配置 SerpApi 时仍然正常显示，只是指标为 `—`。

---

# 六、GitHub Code / Stars 自动化

`config/site.yml` 已经有：

```yaml
profile:
  github_username: "li-wen-hui"
```

如果一篇论文对应某个仓库，在 `content/publications.yml` 里写：

```yaml
github_repo: "你的仓库名"
```

V5 会自动：

- 获取仓库 URL
- 如果 `code_url` 没手填，则自动使用仓库 URL
- 获取 Stars
- 显示在论文卡片中

---

# 七、自动 CV

V5 不再要求你每次网页更新后再手工同步 CV。

每次构建：

```text
Master Data
   ├─ Profile
   ├─ Education
   ├─ Publications
   ├─ Honors
   └─ Service
        ↓
Wenhui_Li_CV.pdf
```

网页和 CV 不会再出现“论文状态不一致”的问题。

如果以后你仍想上传自己排版的 CV，可在：

`config/site.yml`

把：

```yaml
auto_cv:
  enabled: true
```

改成 `false`，再自行把 PDF 放进模板/构建流程即可。

---

# 八、访问统计

`config/site.yml`：

```yaml
analytics:
  provider: "none"
```

可改成：

- `plausible`
- `umami`
- `ga4`

并填写对应 ID。默认 `none` 时不会加载任何统计代码。

---

# 九、GitHub Pages 必须改为 GitHub Actions

V5 不再推荐你之前的：

```text
Deploy from a branch
```

改成：

```text
Repository -> Settings -> Pages -> Build and deployment -> Source -> GitHub Actions
```

之后 `.github/workflows/deploy.yml` 接管：

```text
Push / Weekly Schedule / Manual Run
        ↓
Install dependencies
        ↓
Sync ORCID / Crossref / Scholar / GitHub
        ↓
Merge master data
        ↓
Generate publication covers
        ↓
Generate CV
        ↓
Generate BibTeX / JSON / RSS / SEO files
        ↓
Build dist/
        ↓
Deploy GitHub Pages
```

---

# 十、第一次上传以后怎么做

1. 把 V5 ZIP 全部解压。
2. 上传**整个目录内容**到 `li-wen-hui.github.io` 根目录。
3. Commit：

```text
Migrate academic homepage to automated V5 architecture
```

4. `Settings -> Pages -> Source -> GitHub Actions`。
5. 打开 `Actions`，等待 `Sync, build, and deploy researcher website` 变绿色。
6. 打开你的主页。

即使 ORCID / Scholar 都还没有配置，第一次也应该能正常部署，因为 V5 是 fail-soft 架构。

---

# 十一、真正做到“只填一次”

最终建议你的长期维护方式：

```text
ORCID                    Curated YAML
  │                           │
  ├─ 自动发现 Works           ├─ About
  │                           ├─ News
  ↓                           ├─ Under Review
Crossref                     └─ 展示顺序/标签
  │                           │
  └──────────┬────────────────┘
             ↓
         Master Data
        /     |      \
 Scholar   GitHub    SEO
    │        │        │
 Citations  Stars   Sitemap
    └───────┬────────┘
            ↓
      Automatic Build
       /      |      \
    Website   CV    BibTeX
            ↓
      GitHub Pages
```

这就是 V5 的设计目标。
