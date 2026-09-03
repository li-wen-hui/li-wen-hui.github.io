const $=id=>document.getElementById(id);
let DATA=null,bib="",pubState={category:"All",q:""};
const safe=u=>u&&u!=="#"&&!u.includes("EDIT-ME");
const norm=s=>(s||"").toLowerCase().replace(/<[^>]*>/g," ").replace(/[^a-z0-9]+/g," ").trim();

async function boot(){
  const r=await fetch(`assets/data/site.json?v=${Date.now()}`,{cache:"no-store"});
  DATA=await r.json();
  renderProfile();renderNews();initPublicationControls();renderPublications();initUI();loadAnalytics();
}
function renderProfile(){
  const p=DATA.profile,c=DATA.curated,m=DATA.metrics||{};
  $("brandName").textContent=p.name;$("heroName").textContent=p.name;$("heroNameZh").textContent=p.name_zh||"";
  $("headline").textContent=p.headline||"";$("affiliation").textContent=p.affiliation||"";$("department").textContent=p.department||"";
  $("heroBio").textContent=c.bio||"";$("footerName").textContent=p.name||"";$("footerAffiliation").textContent=p.affiliation||"";
  $("cvTop").href="Wenhui_Li_CV.pdf";$("emailLink").textContent=p.email||"";$("emailLink").href=`mailto:${p.email||""}`;
  $("interests").innerHTML=(c.interests||[]).map(x=>`<span>${x}</span>`).join("");
  const profiles=[["Google Scholar",p.scholar_url],["ORCID",p.orcid_url],["GitHub",p.github_username?`https://github.com/${p.github_username}`:""],["LinkedIn",p.linkedin_url],["ResearchGate",p.researchgate_url]];
  $("profileLinks").innerHTML=profiles.filter(([,u])=>safe(u)).map(([l,u])=>`<a href="${u}" target="_blank" rel="noopener">${l}</a>`).join("");
  if(safe(p.scholar_url)){$("scholarAll").href=p.scholar_url;$("scholarAll").hidden=false}
  if(m.citations!==null&&m.citations!==undefined){
    $("scholarMini").hidden=false;
    $("scholarMini").innerHTML=`<span><strong>${m.citations}</strong><br>Citations</span>${m.h_index!==null&&m.h_index!==undefined?`<span><strong>${m.h_index}</strong><br>h-index</span>`:""}`;
  }
}
function renderNews(){
  const items=DATA.news||[];
  $("newsList").innerHTML=items.map((n,i)=>`<div class="news-item ${n.pinned?"pinned":""} ${i>=4?"news-hidden":""}"><time>${n.date||""}</time><p>${n.pinned?'<span class="news-pin">Pinned</span>':""}${n.text||""}</p></div>`).join("");
  if(items.length>4){
    $("showNews").hidden=false;let expanded=false;
    $("showNews").onclick=()=>{expanded=!expanded;document.querySelectorAll(".news-hidden").forEach(x=>x.style.display=expanded?"grid":"none");$("showNews").textContent=expanded?"Show fewer updates":"Show all updates"};
  }
}
function initPublicationControls(){
  const categories=["All",...new Set((DATA.publications||[]).map(p=>p.category||"Other Publications"))];
  $("categoryFilters").innerHTML=categories.map(c=>`<button class="category-filter ${c==="All"?"active":""}" data-category="${c}">${c}</button>`).join("");
  document.querySelectorAll("[data-category]").forEach(b=>b.onclick=()=>{pubState.category=b.dataset.category;document.querySelectorAll("[data-category]").forEach(x=>x.classList.toggle("active",x===b));renderPublications()});
  $("pubSearch").oninput=e=>{pubState.q=e.target.value;renderPublications()};
}
function link(label,url){return safe(url)?`<a class="pub-link" href="${url}" target="_blank" rel="noopener">${label}</a>`:`<span class="pub-link disabled">${label}</span>`}
function renderPublications(){
  const q=norm(pubState.q);
  const pubs=(DATA.publications||[]).filter(p=>{
    const cat=p.category||"Other Publications",catOk=pubState.category==="All"||cat===pubState.category;
    const hay=norm([p.title,p.authors_html,p.venue,(p.tags||[]).join(" ")].join(" "));
    return catOk&&(!q||hay.includes(q))
  });
  if(!pubs.length){$("pubGroups").innerHTML='<div class="empty">No publications match the current selection.</div>';return}
  const order=["Image Representation","Multimedia Security","Other Publications"];
  const categories=[...new Set(pubs.map(p=>p.category||"Other Publications"))].sort((a,b)=>(order.indexOf(a)<0?99:order.indexOf(a))-(order.indexOf(b)<0?99:order.indexOf(b))||a.localeCompare(b));
  $("pubGroups").innerHTML=categories.map(cat=>`<section class="pub-group"><h3 class="pub-group-title">${cat}</h3><div class="pub-list">${pubs.filter(p=>(p.category||"Other Publications")===cat).map(pubRow).join("")}</div></section>`).join("");
  document.querySelectorAll(".bib-button").forEach(b=>b.onclick=()=>{const p=DATA.publications.find(x=>x.id===b.dataset.id);bib=p?.bibtex||"";$("bibCode").textContent=bib;$("bibTitle").textContent=p?.title||"BibTeX";$("modal").classList.add("open");$("modal").setAttribute("aria-hidden","false")});
}
function pubRow(p){
  const cite=(p.citations!==null&&p.citations!==undefined)?`<span class="citation-line">Cited by ${p.citations}</span>`:"";
  const stars=(p.github_stars!==undefined&&p.github_stars!==null)?`<span class="citation-line">★ ${p.github_stars}</span>`:"";
  return `<article class="pub-row"><div class="pub-thumb"><img src="${p.cover}" alt="Visual thumbnail for ${p.title}"></div><div><span class="pub-venue-badge">${p.venue_short||"Publication"}</span><h3>${p.title}</h3><p class="authors">${p.authors_html||""}</p><p class="venue-line">${p.venue||""}${p.year?`, ${p.year}`:""} ${p.status?`· <span class="status ${p.status_class||""}">${p.status}</span>`:""}</p><div class="pub-links">${link("Paper",p.paper_url)}${link("DOI",p.doi_url)}${link("Code",p.code_url)}${link("Project",p.project_url)}<button class="bib-button" data-id="${p.id}">BibTeX</button>${cite}${stars}</div></div></article>`;
}
function initUI(){
  if(localStorage.getItem("theme")==="dark")document.body.classList.add("dark");
  $("theme").onclick=()=>{document.body.classList.toggle("dark");localStorage.setItem("theme",document.body.classList.contains("dark")?"dark":"light")};
  window.addEventListener("scroll",()=>{const d=document.documentElement,max=d.scrollHeight-d.clientHeight;$("progress").style.width=max>0?`${d.scrollTop/max*100}%`:"0%"});
  const ob=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add("visible");ob.unobserve(e.target)}}),{threshold:.06});
  document.querySelectorAll(".reveal").forEach(e=>ob.observe(e));document.querySelectorAll("[data-close]").forEach(e=>e.onclick=closeModal);
  document.addEventListener("keydown",e=>{if(e.key==="Escape")closeModal()});
  $("copyBib").onclick=async()=>{try{await navigator.clipboard.writeText(bib);const old=$("copyBib").textContent;$("copyBib").textContent="Copied ✓";setTimeout(()=>$("copyBib").textContent=old,1200)}catch{}};
  $("year").textContent=new Date().getFullYear();
}
function closeModal(){$("modal").classList.remove("open");$("modal").setAttribute("aria-hidden","true")}
function loadAnalytics(){
  const a=DATA.analytics||{},p=(a.provider||"none").toLowerCase(),add=(src,attrs={})=>{const s=document.createElement("script");s.defer=true;s.src=src;Object.entries(attrs).forEach(([k,v])=>s.setAttribute(k,v));document.head.appendChild(s)};
  if(p==="plausible"&&a.plausible_domain)add(a.plausible_script||"https://plausible.io/js/script.js",{"data-domain":a.plausible_domain});
  else if(p==="umami"&&a.umami_website_id)add(a.umami_script||"https://cloud.umami.is/script.js",{"data-website-id":a.umami_website_id});
  else if(p==="ga4"&&a.ga4_measurement_id){add(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(a.ga4_measurement_id)}`);window.dataLayer=window.dataLayer||[];window.gtag=function(){dataLayer.push(arguments)};gtag("js",new Date());gtag("config",a.ga4_measurement_id)}
}
boot().catch(e=>{console.error(e);document.body.insertAdjacentHTML("beforeend",'<div style="position:fixed;bottom:18px;left:18px;padding:10px 12px;background:#8c3f4b;color:white;border-radius:6px;font:13px system-ui">Site data failed to load. Run the automated build workflow.</div>')});
