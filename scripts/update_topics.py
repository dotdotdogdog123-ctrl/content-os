#!/usr/bin/env python3
"""Finance-only news/background research feed, kept separate from verified videos."""
import datetime as dt
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from finance_rules import CATEGORY, classify

# Each query is a discovery lead, not proof that an item is relevant.
QUERIES = [
    "个人理财 资产配置 投资 观点",
    "指数基金 ETF 定投 争议",
    "A股 港股 美股 投资 市场 热点",
    "茅台 泡泡玛特 腾讯 公司 分析 估值",
    "美联储 利率 黄金 汇率 理财 影响",
    "巴菲特 段永平 投资 策略 观点",
    "股票 商业模式 盈利 长期 投资",
    "基金投资 风险 收益 投资者",
]
NOW = dt.datetime.now(dt.timezone.utc)

def clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", str(value or "")))).strip()

def feed(query):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query + " when:3d", "hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans"
    })
    request = urllib.request.Request(url, headers={
        "User-Agent": "ContentOS/0.4 (+public RSS research reader)"
    })
    with urllib.request.urlopen(request, timeout=18) as response:
        return ET.fromstring(response.read(1500000))

def research_question(subtopic):
    return {
        "个人理财与资产配置": "这对普通人的资产配置有什么实际影响？适用条件和主要风险是什么？",
        "股票与公司分析": "公司的盈利与竞争力受到什么影响？市场预期和估值是否匹配？",
        "投资方法论": "这套观点的前提和反例是什么？哪些投资者可能不适用？",
        "市场与经济热点": "事件背后的驱动因素是什么？哪些数据能验证市场判断？",
    }.get(subtopic, "有哪些可靠证据与相反观点？")

def main():
    items, seen, errors = [], set(), []
    for query in QUERIES:
        try:
            root = feed(query)
            for node in root.findall(".//item")[:20]:
                title = clean(node.findtext("title"))
                link = clean(node.findtext("link"))
                if not title or not link:
                    continue
                subtopic = classify(title)
                if subtopic is None:
                    continue
                key = re.sub(r"\s*[-—|]\s*[^-—|]+$", "", title).strip().casefold()
                if key in seen:
                    continue
                try:
                    published = parsedate_to_datetime(node.findtext("pubDate")).astimezone(dt.timezone.utc)
                except (TypeError, ValueError, AttributeError):
                    continue
                age = (NOW - published).total_seconds() / 3600
                if age < -2 or age > 72:
                    continue
                seen.add(key)
                source = node.find("source")
                relevance = sum(term.lower() in title.lower() for term in (
                    "理财", "投资", "基金", "股票", "市场", "财经", "财报",
                    "估值", "收益", "黄金", "债券", "美联储", "公司"
                ))
                score = min(90, 30 + min(30, relevance * 7) + (25 if age < 24 else 15 if age < 48 else 5))
                items.append({
                    "title": title, "category": CATEGORY, "topic_track": subtopic,
                    "content_type": "新闻背景参考",
                    "source": clean(source.text if source is not None else ""),
                    "url": link, "published_at": published.isoformat(),
                    "score": score, "angle": research_question(subtopic),
                    "status": "财经背景线索；未验证原始报道，不是视频或已证实的投资建议",
                })
        except Exception as exc:
            errors.append(type(exc).__name__ + ": " + str(exc)[:130])
    if not items and errors:
        old_path = Path("data/topics.json")
        if old_path.exists():
            try:
                old = json.loads(old_path.read_text(encoding="utf-8"))
                if old.get("items"):
                    old["last_attempt_at"] = NOW.isoformat()
                    old["errors"] = errors
                    old["data_stale"] = True
                    old_path.write_text(json.dumps(old, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    print("RSS unavailable; retained old background items:", len(old["items"]))
                    return
            except (OSError, ValueError):
                pass
    items.sort(key=lambda item: (-item["score"], item["published_at"]))
    path = Path("data/topics.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "generated_at": NOW.isoformat(),
        "method": "Financial-topic RSS background leads; heuristic relevance (not video or AI fact checking)",
        "items": items[:90], "errors": errors, "data_stale": bool(errors and not items),
        "coverage": "理财投资与财经背景线索，需核对来源；不以搜索词直接决定分类",
    }
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Finance background items:", len(result["items"]), "feed errors:", len(errors))

if __name__ == "__main__":
    main()
