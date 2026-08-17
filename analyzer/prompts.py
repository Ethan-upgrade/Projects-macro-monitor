SINGLE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "core_conclusions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "本篇报告的核心结论，每条一句话",
            },
            "risk_flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "报告中提示或隐含的风险点；没有则为空数组",
            },
            "industry_highlights": {
                "type": "array",
                "items": {"type": "string"},
                "description": "报告中提到的行业或领域亮点；没有则为空数组",
            },
            "sentiment": {
                "type": "string",
                "enum": ["改善", "走弱", "平稳", "分化"],
                "description": "本篇报告反映的整体景气方向",
            },
        },
        "required": ["core_conclusions", "risk_flags", "industry_highlights", "sentiment"],
    },
}

CROSS_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "overall_assessment": {
                "type": "string",
                "description": "本月整体经济景气综合研判，2-3句话",
            },
            "divergences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "indicators_involved": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["description", "indicators_involved"],
                },
                "description": "本月各报告和指标之间的信号背离，例如 PMI 回暖但社零走弱；没有则为空数组",
            },
            "convergences": {
                "type": "array",
                "items": {"type": "string"},
                "description": "本月各报告和指标共同印证的信号；没有则为空数组",
            },
            "inflection_points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "indicator": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["indicator", "description"],
                },
                "description": "相较近 3 个月趋势出现的拐点；没有则为空数组",
            },
            "trend_vs_recent_3m": {
                "type": "string",
                "description": "与近 3 个月趋势相比的整体判断",
            },
        },
        "required": [
            "overall_assessment",
            "divergences",
            "convergences",
            "inflection_points",
            "trend_vs_recent_3m",
        ],
    },
}

SINGLE_SYSTEM_PROMPT = (
    "你是一名宏观经济分析师，负责阅读国家统计局发布的数据解读报告，"
    "提炼其中的核心结论、风险提示与行业亮点。只依据报告原文作判断，不要编造数字。"
)

CROSS_SYSTEM_PROMPT = (
    "你是一名宏观经济分析师，负责对同一个月内多篇官方数据解读报告"
    "（PMI、CPI/PPI、投资、社零等）做综合研判。重点识别不同指标和报告之间的"
    "信号背离与共振，并结合提供的近 3 个月指标序列判断是否出现拐点。"
    "只依据提供的原文和指标数据作判断，不要编造数字。"
)


def build_single_prompt(title: str, pub_date: str, category: str, raw_text: str) -> str:
    return (
        f"报告标题：{title}\n"
        f"发布日期：{pub_date}\n"
        f"类别：{category}\n\n"
        f"报告正文：\n{raw_text}\n\n"
        "请按输出格式要求提炼这篇报告。"
    )


def build_cross_prompt(month: str, reports: list[dict], recent_indicators: list[dict]) -> str:
    reports_block = "\n\n".join(
        f"【{r['category']}】{r['title']}（{r['pub_date']}）\n{r['raw_text']}" for r in reports
    )
    indicators_block = "\n".join(
        f"- {i['name']}: {i['value']}{i['unit']} (report_date={i['pub_date']})"
        for i in recent_indicators
    )
    return (
        f"月份：{month}\n\n"
        f"本月各报告原文：\n{reports_block}\n\n"
        f"近 3 个月相关指标序列（供对比拐点用）：\n{indicators_block}\n\n"
        "请按输出格式要求给出本月综合研判。"
    )
