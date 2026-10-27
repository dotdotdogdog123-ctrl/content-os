#!/usr/bin/env python3
"""Discover public finance videos from official feeds. No login, scraping bypass or fabricated metrics."""
import datetime as dt
import html
import json
import os
import re
import statistics
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from finance_rules import CATEGORY, classify

NOW = dt.datetime.now(dt.timezone.utc)
MAX_AGE_DAYS = 180
BILIBILI_SOURCES = (
    ("B站财经分区近期投稿", "https://api.bilibili.com/x/web-interface/newlist?rid=207&ps=50&pn=1"),
    ("B站全站热门（财经过滤）", "https://api.bilibili.com/x/web-interface/popular?pn=1&ps=50"),
)
# Stable channel IDs sourced from publicly indexed channel listings. This is a curated
# creator watchlist, NOT an exhaustive search or a platform-wide trending chart.
YOUTUBE_CHANNELS = (
    ("小Lin说", "UCilwQlk62k1z7aUEZPOB6yw"),
    ("美投讲美股", "UCBUH38E0ngqvmTqdchWunwQ"),
    ("一口新飯 MoneyXYZ", "UCh4QrR5V6reIojGpRqkTbYw"),
    ("財經M平方", "UC6LU7FUBvbFCh_cQasrHZ_Q"),
    ("游庭皓的財經皓角", "UC0lbAQVpenvfA2QqzsRtL_g"),
    ("懶錢包 Lazy Wallet", "UChYg2EINv5URVkebzlTGbFQ"),
    ("老王愛說笑", "UCvnLmiWt_zIVIh0zUm_j4Hw"),
    ("投資好朋友 BOS價值投資", "UCT-EAA2q6A02iankuVsdL1w"),
)
MATCH_TERMS = ("投资", "投資", "理财", "理財", "财经", "財經", "股票", "股價",
               "基金", "估值", "经济", "經濟", "金融", "股市", "财报", "財報",
               "收益", "资产配置", "資產配置", "美股", "ETF", "降息")
METRIC_KEYS = ("views", "likes", "comments", "favorites", "shares")
# Reject generic entertainment/business headlines where a weak keyword like
# "收购" or "暴涨" alone created a false investment recommendation.
STRONG_FINANCE = re.compile(
    r"投资|投資|理财|理財|股票|股市|股价|股價|台股|臺股|港股|美股|"
    r"ETF|基金|财报|財報|估值|市值|股息|分红|分紅|回购|回購|"
    r"债券|債券|美债|美債|国债|國債|黄金|黃金|利率|降息|升息|加息|"
    r"美联储|聯準會|关税|關稅|金融危机|金融危機|貨幣|通膨|通胀|"
    r"GDP|经济|經濟|资产|資產|證券|证券|央行|银行|銀行|"
    r"公司分析|商业模式|商業模式|盈利|營收|营收|净利润|淨利", re.I
)
WEAK_ONLY = re.compile(r"收购|收購|并购|併購|暴涨|暴漲|暴跌|赚钱|賺錢|亏钱|虧錢|消费|消費")


def video_track(title):
    track = classify(title)
    if track and WEAK_ONLY.search(title) and not STRONG_FINANCE.search(title):
        return None
    return track


def request_bytes(url, accept="application/xml"):
    request = urllib.request.Request(url, headers={
        "User-Agent": "ContentOS/0.6 (+public feed reader; no credentials)",
        "Accept": accept,
    })
    with urllib.request.urlopen(request, timeout=18) as response:
        return response.read(1800000)


def count(value):
    try:
        return max(0, int(value)) if value is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def format_guess(title):
    """All format labels are *title-only* guesses, not viewed/verified facts."""
    if re.search(r"访谈|訪談|专访|專訪|对话|對話|对谈|對談|播客|Podcast|圆桌|圓桌|訪問|專題訪問", title, re.I):
        return "访谈/对话"
    if re.search(r"科普|解读|解讀|分析|讲解|講解|为什么|為什麼|看懂|复盘|復盤|一文|教程|懶人包|知识|知識|入门|入門", title, re.I):
        return "讲解/科普"
    if re.search(r"争议|爭議|反驳|反駁|骗局|騙局|真相|暴跌|暴漲|泡沫|错了|錯了|辩论|辯論", title, re.I):
        return "热点争议"
    if re.search(r"观点|觀點|看法|我认为|我認為|聊聊|说说|說說|分享|投資筆記", title, re.I):
        return "口播/观点"
    return "形式待核验"


def base_item(title, track, platform, source, author, url, published):
    age = max(0, (NOW - published).total_seconds() / 86400)
    if age > MAX_AGE_DAYS or published > NOW + dt.timedelta(days=2):
        return None
    kind = format_guess(title)
    relevance = sum(word.casefold() in title.casefold() for word in MATCH_TERMS)
    # Editorial priority only; do not mistake this for a platform popularity score.
    score = min(90, round(30 + min(22, relevance * 5) +
                          max(0, 23 - age / 7) + (12 if kind != "形式待核验" else 0)))
    return {
        "title": title, "category": CATEGORY, "topic_track": track,
        "content_type": "社交视频", "platform": platform, "source": source,
        "author": author, "url": url, "published_at": published.isoformat(),
        "score": score, "score_basis": "标题相关性、发布时间、形式关键词；非平台热度",
        "metrics": {key: None for key in METRIC_KEYS},
        "engagement_rate": None, "engagement_basis": None,
        "platform_heat_ratio": None, "platform_heat_sample": 0,
        "format": kind, "format_evidence": "标题推断" if kind != "形式待核验" else "待人工核验",
        "manually_verified": False,
        "angle": "原视频的核心论点、证据、适用边界和反方观点分别是什么？",
        "status": "已获取公开视频链接和标题；未观看核验内容。缺失指标保留空值。",
    }


def bilibili_feed(url):
    obj = json.loads(request_bytes(url, "application/json"))
    if obj.get("code") != 0:
        raise ValueError("B站公开接口返回状态 " + str(obj.get("code")))
    data = obj.get("data") or {}
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("archives", "list", "result"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def bilibili_item(video, source):
    if not isinstance(video, dict):
        return None
    title = html.unescape(re.sub(r"<[^>]+>", "", str(video.get("title") or ""))).strip()
    track = video_track(title)
    bvid = str(video.get("bvid") or "")
    if not track or not re.fullmatch(r"BV[0-9A-Za-z]{10}", bvid):
        return None
    stamp = count(video.get("pubdate") or video.get("ctime"))
    if not stamp:
        return None  # Missing publication time is not today's upload.
    try:
        published = dt.datetime.fromtimestamp(stamp, dt.timezone.utc)
    except (OverflowError, ValueError, OSError):
        return None
    author = video.get("owner") if isinstance(video.get("owner"), dict) else {}
    item = base_item(title, track, "B站", source, str(author.get("name") or ""),
                     "https://www.bilibili.com/video/" + bvid, published)
    if item is None:
        return None
    stats = video.get("stat") if isinstance(video.get("stat"), dict) else {}
    item["metrics"] = {key: count(stats.get(raw)) for key, raw in (
        ("views", "view"), ("likes", "like"), ("comments", "reply"),
        ("favorites", "favorite"), ("shares", "share")
    )}
    return item


def youtube_recent(name, channel_id):
    """YouTube's public channel Atom feed provides real video IDs, not engagement data."""
    if not re.fullmatch(r"UC[0-9A-Za-z_-]{22}", channel_id):
        raise ValueError("invalid configured channel ID")
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_id
    root = ET.fromstring(request_bytes(url))
    ns = {"atom": "http://www.w3.org/2005/Atom",
          "yt": "http://www.youtube.com/xml/schemas/2015",
          "media": "http://search.yahoo.com/mrss/"}
    actual_channel = root.findtext("yt:channelId", "", ns).strip()
    # Some feed variants return a prefixed identifier. The stable 22-char
    # channel payload must still agree with the configured public channel ID.
    if actual_channel and not actual_channel.endswith(channel_id[2:]):
        raise ValueError("feed channel ID mismatch")
    entries = root.findall("atom:entry", ns)
    items = []
    for entry in entries:
        title = html.unescape(entry.findtext("atom:title", "", ns)).strip()
        track = video_track(title)
        identifier = entry.findtext("yt:videoId", "", ns)
        if not track or not re.fullmatch(r"[0-9A-Za-z_-]{11}", identifier):
            continue
        try:
            published = dt.datetime.fromisoformat(
                entry.findtext("atom:published", "", ns).replace("Z", "+00:00"))
            if published.tzinfo is None:
                continue
        except (ValueError, TypeError):
            continue
        item = base_item(title, track, "YouTube", "YouTube 频道官方 Atom RSS",
                         name, "https://www.youtube.com/watch?v=" + identifier, published)
        if item is not None:
            # Some official Atom feeds expose view counts in Media RSS.
            # Never interpret starRating count as likes or infer comments.
            stats = entry.find("media:group/media:community/media:statistics", ns)
            if stats is not None:
                item["metrics"]["views"] = count(stats.get("views"))
                if item["metrics"]["views"] is not None:
                    item["view_metric_source"] = "YouTube 官方 Atom media:statistics"
            items.append(item)
    return len(entries), items


def youtube_public_statistics(items, api_key):
    """Optional official YouTube Data API v3; do not log URLs or credentials."""
    if not api_key or not items:
        return 0
    videos = [item for item in items if item["platform"] == "YouTube"]
    updated = 0
    for start in range(0, len(videos), 50):
        batch = videos[start:start + 50]
        ids = [item["url"].split("v=")[-1] for item in batch]
        query = urllib.parse.urlencode({"part": "statistics", "id": ",".join(ids), "key": api_key})
        obj = json.loads(request_bytes("https://www.googleapis.com/youtube/v3/videos?" + query,
                                       "application/json"))
        indexed = {v.get("id"): v.get("statistics", {}) for v in obj.get("items", [])}
        for item, identifier in zip(batch, ids):
            if identifier not in indexed:
                continue
            stats = indexed[identifier]
            item["metrics"]["views"] = count(stats.get("viewCount"))
            item["metrics"]["likes"] = count(stats.get("likeCount"))
            item["metrics"]["comments"] = count(stats.get("commentCount"))
            # YouTube's public API does not expose per-video shares/favorites.
            updated += 1
    return updated


def finalize_metrics(items):
    for item in items:
        m = item["metrics"]
        views = m.get("views")
        keys = ("likes", "comments", "favorites", "shares") if item["platform"] == "B站" else ("likes", "comments")
        if views is not None and views > 0 and all(m.get(key) is not None for key in keys):
            item["engagement_rate"] = round(100 * sum(m[key] for key in keys) / views, 2)
            item["engagement_basis"] = "+".join(keys) + "/views"
    # Same-platform AND same-age-bucket median. No cross-platform comparisons.
    buckets = {}
    for item in items:
        views = item["metrics"]["views"]
        if views is None:
            continue
        age = max(0, (NOW - dt.datetime.fromisoformat(item["published_at"])).total_seconds() / 86400)
        age_bucket = "0-7天" if age <= 7 else "8-30天" if age <= 30 else "31-180天"
        item["platform_heat_group"] = item["platform"] + " / " + age_bucket
        buckets.setdefault(item["platform_heat_group"], []).append(views)
    for item in items:
        views = item["metrics"]["views"]
        group = item.get("platform_heat_group")
        sample = buckets.get(group, [])
        item["platform_heat_sample"] = len(sample)
        if views is not None and len(sample) >= 3:
            median = statistics.median(sample)
            if median > 0:
                item["platform_heat_ratio"] = round(views / median, 2)


def quality_report(items, stats):
    platforms = sorted({item["platform"] for item in items})
    return {
        "total": len(items),
        "by_platform": {p: sum(x["platform"] == p for x in items) for p in platforms},
        "with_views": sum(x["metrics"]["views"] is not None for x in items),
        "with_engagement_rate": sum(x["engagement_rate"] is not None for x in items),
        "with_relative_heat": sum(x["platform_heat_ratio"] is not None for x in items),
        "format_title_inferred": sum(x["format_evidence"] == "标题推断" for x in items),
        "manually_verified": sum(x["manually_verified"] for x in items),
        "sources_ok": sum(s["status"] == "ok" for s in stats),
        "sources_failed": sum(s["status"] == "failed" for s in stats),
    }


def main():
    path = Path("data/videos.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    results, errors, source_stats, seen = [], [], [], set()
    for label, url in BILIBILI_SOURCES:
        try:
            candidates = bilibili_feed(url)
            added = 0
            for candidate in candidates:
                item = bilibili_item(candidate, label)
                if item and item["url"] not in seen:
                    seen.add(item["url"])
                    results.append(item)
                    added += 1
            source_stats.append({"source": label, "fetched": len(candidates),
                                 "matched_new": added, "status": "ok"})
        except Exception as exc:
            errors.append(label + ": " + type(exc).__name__ + ": " + str(exc)[:90])
            source_stats.append({"source": label, "status": "failed"})
    for name, channel_id in YOUTUBE_CHANNELS:
        label = "YouTube：" + name
        try:
            fetched, candidates = youtube_recent(name, channel_id)
            added = 0
            for item in candidates:
                if item["url"] not in seen:
                    seen.add(item["url"])
                    results.append(item)
                    added += 1
            source_stats.append({"source": label, "fetched": fetched,
                                 "matched_new": added, "status": "ok"})
        except Exception as exc:
            errors.append(label + ": " + type(exc).__name__ + ": " + str(exc)[:90])
            source_stats.append({"source": label, "status": "failed"})
    key = os.environ.get("YOUTUBE_API_KEY", "")
    if key and results:
        try:
            enriched = youtube_public_statistics(results, key)
            source_stats.append({"source": "YouTube Data API（可选公开统计）",
                                 "enriched": enriched, "status": "ok"})
        except Exception as exc:
            # Never print a URL, exception body, or API key from an authenticated request.
            errors.append("YouTube Data API: " + type(exc).__name__ + "（细节已隐藏）")
            source_stats.append({"source": "YouTube Data API（可选公开统计）", "status": "failed"})
    if not results and path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            if previous.get("items"):
                previous["last_attempt_at"] = NOW.isoformat()
                previous["errors"] = errors
                previous["source_stats"] = source_stats
                previous["data_stale"] = True
                previous["stale_reason"] = "本轮无匹配视频；保留历史快照，未伪装为最新数据"
                path.write_text(json.dumps(previous, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print("No fresh matching videos; retained old snapshot")
                return
        except (OSError, ValueError):
            pass
    finalize_metrics(results)
    results.sort(key=lambda x: (-x["score"], -(x["metrics"]["views"] or 0)))
    results = results[:120]
    output = {
        "generated_at": NOW.isoformat(),
        "method": "Official YouTube channel Atom feeds + public Bilibili feeds; optional official YouTube Data API",
        "items": results, "errors": errors, "source_stats": source_stats,
        "quality": quality_report(results, source_stats), "data_stale": False,
        "coverage": "创作者观察名单，不是全网视频搜索或热榜；视频形式仅由标题推断；未人工核验。",
        "metric_note": "YouTube RSS 可能提供播放量（media:statistics），但不提供可直接计算互动率的完整赞/评论；可选官方 Data API 获取公开统计。B站可得点赞/评论/收藏/分享。不同口径不可跨平台比较。",
        "heat_note": "同平台、同发布时间分组(0-7/8-30/31-180天)至少3条有播放量视频时，播放量/组内中位数；仅为样本内相对值，不是平台全站热度。",
    }
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Public finance videos:", len(results), "quality:", output["quality"],
          "source failures:", len(errors))


if __name__ == "__main__":
    main()
