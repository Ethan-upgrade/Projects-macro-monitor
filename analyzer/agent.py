import asyncio
import json

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from analyzer.prompts import (
    CROSS_SCHEMA,
    CROSS_SYSTEM_PROMPT,
    SINGLE_SCHEMA,
    SINGLE_SYSTEM_PROMPT,
    build_cross_prompt,
    build_single_prompt,
)


async def _run_structured(prompt: str, system_prompt: str, schema: dict) -> dict:
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        tools=[],
        max_turns=1,
        output_format=schema,
    )
    result = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message

    if result is None:
        raise RuntimeError("no ResultMessage received from claude-agent-sdk query")
    if result.is_error:
        raise RuntimeError(f"claude-agent-sdk query failed: {result.subtype} {result.errors}")
    if result.structured_output is None:
        raise RuntimeError(f"no structured_output in result: {result.result!r}")
    return result.structured_output


def analyze_single(title: str, pub_date: str, category: str, raw_text: str) -> dict:
    prompt = build_single_prompt(title, pub_date, category, raw_text)
    return asyncio.run(_run_structured(prompt, SINGLE_SYSTEM_PROMPT, SINGLE_SCHEMA))


def analyze_cross(month: str, reports: list[dict], recent_indicators: list[dict]) -> dict:
    prompt = build_cross_prompt(month, reports, recent_indicators)
    return asyncio.run(_run_structured(prompt, CROSS_SYSTEM_PROMPT, CROSS_SCHEMA))


if __name__ == "__main__":
    import sys

    from storage.db import get_connection

    conn = get_connection()
    row = conn.execute("SELECT * FROM reports ORDER BY pub_date DESC LIMIT 1").fetchone()
    conn.close()
    if row is None:
        print("no reports in db")
        sys.exit(1)

    print(f"analyzing: {row['title']} ({row['pub_date']})")
    output = analyze_single(row["title"], row["pub_date"], row["category"], row["raw_text"])
    print(json.dumps(output, ensure_ascii=False, indent=2))
