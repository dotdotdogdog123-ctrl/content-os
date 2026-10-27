"""Offline quality checks for Content OS topic classification."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from finance_rules import classify

class FinanceRulesTest(unittest.TestCase):
    def test_investing_methods(self):
        self.assertEqual(classify("巴菲特价值投资的三条经验"), "投资方法论")

    def test_personal_finance(self):
        self.assertEqual(classify("如何做好家庭资产配置和ETF定投？"), "个人理财与资产配置")

    def test_company_research(self):
        self.assertEqual(classify("泡泡玛特财报解读：营收和盈利如何变化"), "股票与公司分析")

    def test_market_events(self):
        self.assertEqual(classify("美联储降息会怎样影响股市"), "市场与经济热点")

    def test_exclude_fund_nav_spam(self):
        self.assertIsNone(classify("某混合基金A净值增长率2.5%，最新净值公布"))

    def test_exclude_celebrity_market_word(self):
        self.assertIsNone(classify("明星被封杀，没有中国市场会失去什么"))

    def test_exclude_tech_with_publisher_name(self):
        self.assertIsNone(classify("腾讯云走进端侧具身智能 - 21财经"))

    def test_exclude_fund_admin_notice(self):
        self.assertIsNone(classify("华宝基金旗下基金开通基金转换业务公告"))

    def test_exclude_tech_news(self):
        self.assertIsNone(classify("OpenAI发布全新Agent世界模型"))

if __name__ == "__main__":
    unittest.main()
