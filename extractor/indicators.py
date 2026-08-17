import re

from models import Indicator

_SIGN = {"上升": 1, "上涨": 1, "增长": 1, "下降": -1, "下跌": -1, "持平": 0}

_NOISE_PREFIXES = (
    "推动",
    "带动",
    "拉动",
    "促进",
    "多措并举促进",
    "在",
    "以",
    "受",
    "叠加",
    "有效支撑",
    "企业持续加大",
    "支撑",
)


def _clean_name(name: str) -> str:
    changed = True
    while changed:
        changed = False
        for prefix in _NOISE_PREFIXES:
            if name.startswith(prefix) and len(name) > len(prefix) + 1:
                name = name[len(prefix) :]
                changed = True
    return name


_RE_LEVEL_MOM_POINTS = re.compile(
    r"([\u4e00-\u9fa5A-Za-z]{2,30}(?:指数|PMI))为?(\d+\.\d+)%[，,]"
    r"(?:比上月|较上月)?(上升|下降|持平)(?:了)?(\d+\.\d+)?个百分点"
)

_RE_CPI_PPI = re.compile(
    r"(居民消费价格|工业生产者出厂价格)(?:指数)?[（(](CPI|PPI)[）)]"
    r"环比(上涨|下降|持平)(\d+\.\d+)?%[，,]"
    r"同比(上涨|下降|持平)(\d+\.\d+)?%"
)

_CPI_PPI_LABEL = {"居民消费价格": "CPI", "工业生产者出厂价格": "PPI"}

_RE_GENERIC_YOY = re.compile(
    r"([\u4e00-\u9fa5]{2,30}(?:总额|投资|利润|增加值|营业收入|零售额))"
    r"[^。；，,]{0,30}?同比(增长|下降|持平)(\d+\.\d+)?%"
)


def extract_indicators(report_url: str, raw_text: str) -> list[Indicator]:
    indicators: list[Indicator] = []
    seen_names: set[str] = set()

    for m in _RE_LEVEL_MOM_POINTS.finditer(raw_text):
        name, value, direction, change = m.groups()
        if name in seen_names:
            continue
        seen_names.add(name)
        mom = float(change) * _SIGN[direction] if change else 0.0
        indicators.append(Indicator(report_url, name, float(value), "%", mom_change=mom))

    for m in _RE_CPI_PPI.finditer(raw_text):
        label, acronym, mom_dir, mom_val, yoy_dir, yoy_val = m.groups()
        code = _CPI_PPI_LABEL.get(label, acronym)
        for suffix, direction, value in (
            (f"{code}环比", mom_dir, mom_val),
            (f"{code}同比", yoy_dir, yoy_val),
        ):
            if suffix in seen_names or value is None:
                continue
            seen_names.add(suffix)
            indicators.append(Indicator(report_url, suffix, float(value) * _SIGN[direction], "%"))

    for m in _RE_GENERIC_YOY.finditer(raw_text):
        name, direction, value = m.groups()
        name = _clean_name(name)
        if name in seen_names or value is None:
            continue
        seen_names.add(name)
        indicators.append(Indicator(report_url, f"{name}同比", float(value) * _SIGN[direction], "%"))

    return indicators
