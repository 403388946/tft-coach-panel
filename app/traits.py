"""羁绊断点确定性查表。

不靠模型口算：给定羁绊名与当前计数，返回达到的最高档、距下一档缺口、是否溢出。
断点表随赛季数据包更新；未配置断点的羁绊只显示当前层数，不猜达标。
"""
from __future__ import annotations

from typing import Optional

# 羁绊名 -> 激活档位（升序）。P0 内置已知样本，后续从 data 赛季词表补齐。
BREAKPOINTS: dict[str, list[int]] = {
    "街头恶魔": [3, 5, 7, 10],
    "斗士": [2, 4, 6],
    "高级工程师": [2, 4, 6, 8],
    "强袭射手": [1, 2],
    "战略分析师": [1, 2],
    "杀手": [1, 2],
    "福牛守护者": [1, 2],
    "源计划": [1, 3],
}


def analyze(name: str, count: int) -> dict:
    """返回单个羁绊的断点分析结果。

    active: 已达到的最高档位；None 表示尚未激活任何档位。
    short_by: 距下一档缺口；None 表示已是最后一档或未配置。
    overflow: 是否超过最后一档。
    """
    breakpoints = BREAKPOINTS.get(name)
    result: dict = {
        "name": name,
        "count": count,
        "configured": breakpoints is not None,
        "active": None,
        "short_by": None,
        "overflow": False,
    }
    if not breakpoints:
        return result

    active: Optional[int] = None
    for b in breakpoints:
        if count >= b:
            active = b
    result["active"] = active

    next_b = next((b for b in breakpoints if b > count), None)
    if next_b is None:
        result["overflow"] = count > breakpoints[-1]
    else:
        result["short_by"] = next_b - count
    return result


def format_line(result: dict) -> str:
    """面板展示用单行文本。"""
    name, count = result["name"], result["count"]
    if not result["configured"]:
        return f"? {name} {count}（断点待补）"
    if result["active"] is not None and result["short_by"] is None:
        tag = "溢出" if result["overflow"] else "达标"
        return f"☑ {name} {count}（{tag}）"
    if result["active"] is None:
        target = result["short_by"]
        return f"☐ {name} {count}（距下一档差 {target}）"
    return f"☐ {name} {count}（已达 {result['active']}，再差 {result['short_by']} 到下一档）"


def analyze_traits(traits: list[dict]) -> list[dict]:
    """批量分析 [{"name": str, "count": int}, ...]。"""
    return [analyze(t["name"], int(t.get("count", 0))) for t in traits]
