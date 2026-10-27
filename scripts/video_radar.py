#!/usr/bin/env python3
"""Discover actual public finance videos without credentials or anti-bot bypass."""
import json,re,datetime as dt,urllib.request
from pathlib import Path
now=dt.datetime.now(dt.timezone.utc)
words=("价值投资","巴菲特","段永平","投资","股票","财经","估值","商业模式","财报","茅台","泡泡玛特","腾讯","基金","股市","投资心理","公司分析","港股","A股","美股","消费股")
def main():
 path=Path("data/videos.json");path.parent.mkdir(exist_ok=True)
 errors=[];items=[]
 try:
  req=urllib.request.Request("https://api.bilibili.com/x/web-interface/popular?pn=1&ps=50",headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.bilibili.com/"})
  with urllib.request.urlopen(req,timeout=18) as res:data=json.load(res)
  if data.get("code")!=0:raise ValueError("B站接口未返回成功")
  for v in (data.get("data") or {}).get("list",[]):
   title=re.sub("<[^>]+>","",str(v.get("title") or "")).strip()
   if not any(w.lower() in title.lower() for w in words):continue
   bvid=str(v.get("bvid") or "")
   if not re.fullmatch("BV[0-9A-Za-z]{10}",bvid):continue
   stat=v.get("stat") or {}
   def metric(k):
    try:return max(0,int(stat[k]))
    except (KeyError,ValueError,TypeError):return None
   metrics={"views":metric("view"),"likes":metric("like"),"comments":metric("reply"),"favorites":metric("favorite"),"shares":metric("share")}
   views=metrics["views"];eng=sum(metrics[k] or 0 for k in ("likes","comments","favorites","shares"))
   rate=round(eng/views*100,2) if views else None
   stamp=int(v.get("pubdate") or v.get("ctime") or now.timestamp())
   published=dt.datetime.fromtimestamp(stamp,dt.timezone.utc)
   age=max(0,(now-published).total_seconds()/86400)
   score=min(100,round(25+max(0,20-age*0.67)+min(30,(rate or 0)*3)+min(25,sum(w in title for w in words)*7)))
   fmt="访谈对话" if any(w in title for w in ("访谈","对话","对谈","专访","播客","圆桌")) else "科普讲解" if any(w in title for w in ("科普","讲解","看懂","为什么","分析","解读")) else "观点视频（形式待核实）"
   track="价值投资方法论" if any(w in title for w in ("巴菲特","段永平","投资心理","价值投资","投资方法")) else "个股研究与热点争议"
   items.append({"title":title,"category":"财经价值投资","content_type":"社交视频","platform":"B站","source":"B站公开热门列表","author":str((v.get("owner") or {}).get("name") or ""),"url":"https://www.bilibili.com/video/"+bvid,"published_at":published.isoformat(),"score":score,"metrics":metrics,"engagement_rate":rate,"format":fmt,"topic_track":track,"angle":"核心论点是什么？证据充分吗？有哪些反方观点？","status":"真实视频与公开指标快照；观点和形式尚待观看核实"})
  items.sort(key=lambda x:(-x["score"],-(x["metrics"]["views"] or 0)))
 except Exception as e:errors.append(type(e).__name__+": "+str(e)[:180])
 if errors and path.exists():
  try:
   old=json.loads(path.read_text(encoding="utf-8"))
   if old.get("items"):
    old["errors"]=errors;old["last_attempt_at"]=now.isoformat()
    path.write_text(json.dumps(old,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Retained last successful data");return
  except (ValueError,OSError):pass
 output={"generated_at":now.isoformat(),"method":"Public Bilibili popular feed; no AI or login","items":items,"errors":errors,"coverage":"仅公开泛热门榜单中符合财经关键词的视频，非全站财经热榜"}
 path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Videos:",len(items),"Errors:",len(errors))
if __name__=="__main__":main()
