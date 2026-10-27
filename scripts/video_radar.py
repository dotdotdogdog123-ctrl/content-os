#!/usr/bin/env python3
"""Find real public finance videos. No account, login, signature bypass or fake metrics."""
import datetime as dt
import html
import json
import re
import urllib.request
from pathlib import Path
from finance_rules import CATEGORY, classify

NOW = dt.datetime.now(dt.timezone.utc)
SOURCES = (
    ("B站财经分区近期投稿", "https://api.bilibili.com/x/web-interface/newlist?rid=207&ps=50&pn=1"),
    ("B站财经分区动态", "https://api.bilibili.com/x/web-interface/dynamic/region?rid=207&ps=50&pn=1"),
    ("B站知识区排行榜", "https://api.bilibili.com/x/web-interface/ranking/v2?rid=36&type=all"),
    ("B站全站热门补充", "https://api.bilibili.com/x/web-interface/popular?pn=1&ps=50"),
)
FINANCE_CHANNEL_NAMES = ("财经", "金融", "商业", "经济", "投资", "理财")
MATCH_TERMS = ("投资", "理财", "财经", "股票", "基金", "估值", "经济", "金融", "股市", "财报", "收益", "资产配置")

def fetch(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/",
        "Accept": "application/json"
    })
    with urllib.request.urlopen(request, timeout=18) as response:
        obj = json.load(response)
    if obj.get("code") != 0:
        raise ValueError("public feed response code " + str(obj.get("code")))
    data = obj.get("data") or {}
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for field in ("archives", "list", "result"):
        if isinstance(data.get(field), list):
            return data[field]
    return []

def count(value):
    try:
        return max(0, int(value)) if value is not None else None
    except (TypeError, ValueError):
        return None

def video_format(title):
    if any(x in title for x in ("访谈", "专访", "对话", "对谈", "播客", "圆桌")):
        return "标题推断：访谈/对话"
    if any(x in title for x in ("科普", "解读", "分析", "讲解", "为什么", "看懂", "复盘")):
        return "标题推断：讲解/科普"
    return "视频形式待观看核实"

def convert(video, source):
    if not isinstance(video, dict):
        return None
    title = html.unescape(re.sub(r"<[^>]+>", "", str(video.get("title") or ""))).strip()
    track = classify(title)
    if track is None:
        return None
    bvid = str(video.get("bvid") or "")
    if not re.fullmatch(r"BV[0-9A-Za-z]{10}", bvid):
        return None
    stats = video.get("stat") or {}
    metrics = {key: count(stats.get(raw)) for key, raw in (
        ("views", "view"), ("likes", "like"), ("comments", "reply"),
        ("favorites", "favorite"), ("shares", "share")
    )}
    views = metrics["views"]
    interaction_keys = ("likes", "comments", "favorites", "shares")
    complete = bool(views and all(metrics[key] is not None for key in interaction_keys))
    rate = round(100 * sum(metrics[key] for key in interaction_keys) / views, 2) if complete else None
    try:
        stamp = count(video.get("pubdate") or video.get("ctime"))
        published = dt.datetime.fromtimestamp(stamp, dt.timezone.utc) if stamp else NOW
    except (OverflowError, ValueError):
        published = NOW
    age_days = max(0, (NOW - published).total_seconds() / 86400)
    relevance = sum(term.lower() in title.lower() for term in MATCH_TERMS)
    score = min(100, round(25 + min(25, relevance * 8) + max(0, 20 - age_days) + min(30, (rate or 0) * 2.5)))
    author = video.get("owner") or {}
    return {
        "title": title, "category": CATEGORY, "topic_track": track,
        "content_type": "社交视频", "platform": "B站", "source": source,
        "author": str(author.get("name") or ""), "url": "https://www.bilibili.com/video/" + bvid,
        "published_at": published.isoformat(), "score": score,
        "metrics": metrics, "engagement_rate": rate,
        "format": video_format(title),
        "angle": "这条视频最值得追问的投资观点是什么？有哪些事实、风险和反方论据？",
        "status": "视频链接来自公开数据；内容尚未观看核实，互动数据为采集时快照",
    }

def main():
    path = Path("data/videos.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    results, errors, source_stats, seen = [], [], [], set()
    successful = 0
    for label, url in SOURCES:
        try:
            candidates = fetch(url)
            successful += 1
            added = 0
            for candidate in candidates:
                item = convert(candidate, label)
                if not item or item["url"] in seen:
                    continue
                seen.add(item["url"])
                results.append(item)
                added += 1
            source_stats.append({"source": label, "fetched": len(candidates), "matched_new": added, "status": "ok"})
        except Exception as exc:
            error = label + ": " + type(exc).__name__ + ": " + str(exc)[:120]
            errors.append(error)
            source_stats.append({"source": label, "status": "failed"})
    if successful == 0 and path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            if previous.get("items"):
                previous["last_attempt_at"] = NOW.isoformat()
                previous["errors"] = errors
                previous["source_stats"] = source_stats
                previous["data_stale"] = True
                path.write_text(json.dumps(previous, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print("All sources unavailable; kept last successful videos")
                return
        except (OSError, ValueError):
            pass
    results.sort(key=lambda item: (-item["score"], -(item["metrics"]["views"] or 0)))
    output = {
        "generated_at": NOW.isoformat(),
        "method": "Public Bilibili finance-area video discovery; no login, AI or keyword-search bypass",
        "items": results[:120], "errors": errors, "source_stats": source_stats,
        "data_stale": False,
        "coverage": "B站财经分区与公开榜单的可得部分；不是全平台财经热榜，视频形式按标题初判",
    }
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Verified video links:", len(output["items"]), "success sources:", successful, "errors:", len(errors))

if __name__ == "__main__":
    main()
