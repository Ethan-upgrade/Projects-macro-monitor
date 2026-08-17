from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from models import Report

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) macro-monitor-bot/0.1"}

# Ordered most-specific-first; first match wins.
CATEGORY_KEYWORDS = [
    ("采购经理指数", "PMI"),
    ("商品住宅销售价格", "房价"),
    ("CPI和PPI", "CPI/PPI"),
    ("居民消费价格", "CPI"),
    ("工业生产者出厂价格", "PPI"),
    ("CPI", "CPI/PPI"),
    ("PPI", "CPI/PPI"),
    ("投资数据", "投资"),
    ("固定资产投资", "投资"),
    ("社会消费品零售总额", "社零"),
    ("消费市场", "社零"),
    ("工业生产数据", "工业"),
    ("工业企业利润", "工业"),
    ("规模以上工业", "工业"),
    ("工业生产增长", "工业"),
    ("平均工资", "就业"),
    ("就业形势", "就业"),
    ("进出口", "外贸"),
    ("对外贸易", "外贸"),
    ("居民收入", "民生"),
    ("十四五", "专题"),
    ("经济运行", "综合"),
    ("国民经济", "综合"),
    ("农业生产", "农业"),
    ("能源供给", "能源"),
    ("服务业经济", "服务业"),
    ("文化及相关产业", "文化产业"),
]


def _guess_category(title: str) -> str:
    for keyword, category in CATEGORY_KEYWORDS:
        if keyword in title:
            return category
    return "其他"


def fetch_detail(url: str, client: httpx.Client) -> Report | None:
    resp = client.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    title_meta = soup.find("meta", attrs={"name": "ArticleTitle"})
    date_meta = soup.find("meta", attrs={"name": "PubDate"})
    body = soup.find("div", class_="trs_editor_view")

    if not title_meta or not date_meta or not body:
        return None

    title = title_meta["content"].strip()
    pub_date = datetime.strptime(date_meta["content"].strip(), "%Y/%m/%d %H:%M")
    paragraphs = [p.get_text(separator="", strip=True) for p in body.find_all("p")]
    raw_text = "\n".join(p for p in paragraphs if p)

    return Report(
        url=url,
        title=title,
        pub_date=pub_date,
        category=_guess_category(title),
        raw_text=raw_text,
    )
