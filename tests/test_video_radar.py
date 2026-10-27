"""Offline tests: public-feed parsing, missing metrics and honest same-platform comparisons."""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import video_radar as radar
from finance_rules import classify


class FinanceVideoRadarTest(unittest.TestCase):
    def test_traditional_chinese_titles(self):
        self.assertEqual(classify("ETF定期定額理財有哪些風險"), "个人理财与资产配置")
        self.assertEqual(classify("聯準會降息如何影響台股"), "股票与公司分析")

    def test_format_is_only_title_inference(self):
        self.assertEqual(radar.format_guess("財經訪談：如何選股"), "访谈/对话")
        self.assertEqual(radar.format_guess("財報解讀：估值方法"), "讲解/科普")
        self.assertEqual(radar.format_guess("某公司股票觀察"), "形式待核验")

    def test_youtube_feed_has_real_id_but_missing_metrics(self):
        published = (radar.NOW - dt.timedelta(days=1)).isoformat()
        xml = ('<feed xmlns="http://www.w3.org/2005/Atom" '
               'xmlns:yt="http://www.youtube.com/xml/schemas/2015" ' 
               'xmlns:media="http://search.yahoo.com/mrss/">'
               '<yt:channelId>UCilwQlk62k1z7aUEZPOB6yw</yt:channelId>'
               '<entry><title>價值投資如何判斷估值？</title>'
               '<yt:videoId>abcdefghijk</yt:videoId>'
               '<published>' + published + '</published>'
               '<media:group><media:community><media:statistics views="12345"/>'
               '</media:community></media:group></entry></feed>')
        with patch.object(radar, "request_bytes", return_value=xml.encode()):
            fetched, items = radar.youtube_recent("test", "UCilwQlk62k1z7aUEZPOB6yw")
        self.assertEqual(fetched, 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], "https://www.youtube.com/watch?v=abcdefghijk")
        self.assertEqual(items[0]["metrics"]["views"], 12345)
        self.assertFalse(items[0]["manually_verified"])

    def test_bilibili_requires_real_id_and_publish_time(self):
        item = {"title": "泡泡玛特财报解读", "bvid": "BV1234567890",
                "pubdate": int((radar.NOW - dt.timedelta(days=1)).timestamp()),
                "stat": {"view": 100, "like": 8, "reply": 2, "favorite": 1, "share": 1}}
        video = radar.bilibili_item(item, "test")
        self.assertIsNotNone(video)
        self.assertEqual(video["metrics"]["views"], 100)
        self.assertIsNone(radar.bilibili_item({**item, "bvid": "not-real"}, "test"))
        self.assertIsNone(radar.bilibili_item({**item, "pubdate": None}, "test"))

    def test_platform_heat_requires_three_comparable_samples(self):
        published = radar.NOW - dt.timedelta(days=1)
        items = [radar.base_item("股票估值分析", "股票与公司分析",
                                 "B站", "test", "", "https://example.test/" + str(i), published)
                 for i in range(3)]
        for item, views in zip(items, (100, 200, 400)):
            item["metrics"] = {"views": views, "likes": 10, "comments": 5,
                               "favorites": 3, "shares": 2}
        yt = radar.base_item("股票估值分析", "股票与公司分析",
                             "YouTube", "test", "", "https://example.test/yt", published)
        yt["metrics"]["views"] = 10000
        items.append(yt)
        radar.finalize_metrics(items)
        self.assertEqual(items[0]["engagement_rate"], 20.0)
        self.assertEqual(items[0]["platform_heat_ratio"], 0.5)
        self.assertEqual(items[2]["platform_heat_ratio"], 2.0)
        self.assertIsNone(yt["platform_heat_ratio"])
        self.assertIsNone(yt["engagement_rate"])


if __name__ == "__main__":
    unittest.main()
