#!/usr/bin/env python3
"""Public RSS topic discovery. No secrets or third-party dependencies."""
import datetime as dt, json, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET, html, os
from email.utils import parsedate_to_datetime
from pathlib import Path

QUERIES = [
 ("财经价值投资", "site:bilibili.com/video 价值投资 股票"),
 ("财经价值投资", "site:bilibili.com/video 投资 估值 商业模式"),
 ("财经价值投资", "site:douyin.com/video 价值投资 财经"),
 ("财经价值投资", "site:xiaohongshu.com/explore 价值投资 财经"),
 ("财经价值投资", "港股 消费 公司 估值"),
 ("财经价值投资", "价值投资 投资观点 争议 股票"),
 ("AI科技访谈", "人工智能 大模型 Agent 具身智能"),
 ("AI科技访谈", "AI 科学研究 机器人 世界模型"),
]
def clean(s):
 return re.sub(r"\s+"," ",html.unescape(re.sub("<[^>]*>","",s or ""))).strip()
def getfeed(query):
 url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":query+" when:3d","hl":"zh-CN","gl":"CN","ceid":"CN:zh-Hans"})
 req=urllib.request.Request(url,headers={"User-Agent":"ContentOS/0.2 (+public RSS reader)"})
 with urllib.request.urlopen(req,timeout=18) as r:
  return ET.fromstring(r.read(1500000))
def score(title,category,published):
 keywords=("财报","利润","营收","估值","融资","上市","业绩","模型","Agent","机器人","具身","AI","芯片","收购","增长","商业化")
 relevance=sum(1 for k in keywords if k.lower() in title.lower())
 age=max(0,(dt.datetime.now(dt.timezone.utc)-published).total_seconds()/3600)
 return min(95,35+min(35,relevance*8)+(25 if age<24 else 15 if age<48 else 5))
def angle(cat,title):
 if cat=="财经价值投资": return "这条消息会怎样改变公司的长期盈利能力？市场价格已经反映了多少预期？"
 return "这是技术能力突破，还是商业化进展？还有哪些尚未解决的真实世界难题？"
now=dt.datetime.now(dt.timezone.utc); items=[]; seen=set(); errors=[]
for cat,q in QUERIES:
 try:
  root=getfeed(q)
  for item in root.findall(".//item")[:15]:
   title=clean(item.findtext("title")); link=clean(item.findtext("link"))
   if not title or not link or title.casefold() in seen:continue
   try: published=parsedate_to_datetime(item.findtext("pubDate")).astimezone(dt.timezone.utc)
   except Exception:continue
   if (now-published).total_seconds()>72*3600:continue
   seen.add(title.casefold())
   source=item.find("source"); source_name=clean(source.text if source is not None else "")
   items.append({"title":title,"category":cat,"source":source_name,"url":link,"published_at":published.isoformat(),"score":score(title,cat,published),"angle":angle(cat,title),"status":"待核实：新闻聚合来源，需核对原始报道和公司公告"})
 except Exception as e:errors.append(f"{cat}: {type(e).__name__}: {str(e)[:150]}")
items.sort(key=lambda x:(-x["score"],x["published_at"]))
output={"generated_at":now.isoformat(),"method":"RSS news discovery + transparent heuristic scoring (not AI)","items":items[:60],"errors":errors}
path=Path("data/topics.json");path.parent.mkdir(exist_ok=True)
if not items and path.exists():
 old=json.loads(path.read_text(encoding="utf-8"))
 if old.get("items"): print("No new items; retaining last successful feed");raise SystemExit(0)
path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"Discovered {len(items)} topics; errors: {len(errors)}")
