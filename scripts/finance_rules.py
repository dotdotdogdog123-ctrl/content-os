"""Shared, explainable finance topic rules used by both public feeds.

A title match proposes a topic; it does not certify the video's contents.
"""
import re

CATEGORY = "理财投资/财经"
LOW_VALUE = re.compile(
    r"单位净值|累计净值|净值增长率|基金净值|最新净值|净值播报|"
    r"基金份额净值|份额净值|基金产品档案|"
    r"股票股价[_\s]|股价行情[_\s]|行情_讨论_资讯|"
    r"每日行情|实时行情|行情中心|申购赎回清单|"
    r"基金经理变更公告|基金销售公告|基金资产净值公告|"
    r"行情报价_交易|行情数据中心"
)
TOPICS = (
    ("投资方法论", r"价值投资|巴菲特|段永平|芒格|护城河|安全边际|投资误区|投资心理|投资哲学|长期持有|长期投资|投资策略|投资方法|投资逻辑|资产定价|估值方法"),
    ("个人理财与资产配置", r"理财|个人财务|资产配置|基金定投|定投|ETF|指数基金|存款|存钱|储蓄|国债|债券|黄金|保险|养老金|养老规划|房贷|财务自由|家庭资产|现金流管理|收益率|买基金"),
    ("股票与公司分析", r"股票|股价|A股|港股|美股|个股|上市公司|股息|分红|回购|财报|盈利|营收|净利润|市盈率|估值|商业模式|公司研究|公司分析|茅台|泸州老窖|泡泡玛特|腾讯|阿里巴巴|美团|比亚迪|宁德时代|苹果公司|特斯拉|英伟达|伯克希尔|拼多多"),
    ("市场与经济热点", r"财经|金融|股市|牛市|熊市|炒股|基金|投资|降息|加息|央行|美联储|通胀|通缩|经济|消费|汇率|房价|楼市|房地产|大盘|指数|板块|股市行情|市场行情|利率|经济政策|GDP|暴涨|暴跌|抄底|加仓|减仓|亏钱|赚钱|银行|证券|债市|黄金价格"),
)
FINANCE_CONTEXT = re.compile(
    r"投资|金融|财经|股票|股价|股市|财报|营收|利润|市值|估值|"
    r"上市|资本市场|基金|银行|经济|货币|降息|美联储|消费股|"
    r"商业模式|证券|融资|资产|英伟达股价|AI概念股"
)

def classify(title):
    """Return a finance subtopic or None; reject generic noise."""
    title = str(title or "").strip()
    if not title or LOW_VALUE.search(title):
        return None
    if re.search(r"人工智能|机器人|世界模型|\bAI\b|Agent|大模型", title, re.I) and not FINANCE_CONTEXT.search(title):
        return None
    for subtopic, pattern in TOPICS:
        if re.search(pattern, title, re.I):
            return subtopic
    return None
