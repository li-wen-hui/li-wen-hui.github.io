# V6：Academic-first 国际学术主页

V6 不再把首页设计成“申博 CV / 仪表盘”，而是把主页核心压缩为：

1. Home：头像、姓名、机构、学术简介、Research Interests、Contact、Profiles
2. News：近期学术动态
3. Selected Publications：按研究主题分组的论文，是全站视觉核心

主页不再突出 GPA、教育经历、荣誉、h-index 大数字卡片等“履历感”元素。
这些数据仍然保留在统一数据层，并可自动进入 CV。

## 自动化仍全部保留

- ORCID：发现公开 works
- Crossref：DOI metadata
- Google Scholar / SerpApi：citations / h-index / i10-index / per-paper citations
- GitHub API：代码仓库 / stars
- GitHub Actions：自动同步、build、deploy
- 自动生成 CV
- 自动生成 BibTeX
- academic-profile.json
- RSS
- sitemap / robots
- SEO / Open Graph
- custom domain
- analytics

## GPA

`content/profile.yml` 中仍保留 `gpa: "4.15 / 4.7"`。
V6 默认不在主页显示 GPA，只在自动 CV 中显示。

## Publications 分类

每篇论文增加 `category:`：
- Image Representation
- Multimedia Security
- Other Publications

自动从 ORCID 发现、但没有手工分类的论文会进入 `Other Publications`。
