"""决策接口。

``decide(state, frame_path) -> {advice, target_comp, trait_check, confidence, unresolved, prompt}``

P0：本地只做确定性梳理（羁绊断点、经济 / 血量风险提示），最终 meta 建议由云端大模型给出；
后期把 ``call_cloud`` 接到 OpenAI 兼容接口即可，面板与 state 协议不变。
"""
from __future__ import annotations

from . import traits
from .state import BoardState

# 影响建议可信度的关键字段（任一缺失则标注存疑）：key -> 中文标签。
KEY_FIELDS: dict[str, str] = {
    "level": "等级",
    "gold": "金币",
    "hp": "血量",
    "shop": "商店",
}


def _missing_fields(state: BoardState) -> list[str]:
    return [k for k in KEY_FIELDS if getattr(state, k) in (None, "", [])]


def _confidence(state: BoardState) -> str:
    missing = _missing_fields(state)
    if missing:
        labels = "、".join(KEY_FIELDS[k] for k in missing)
        return "存疑（关键字段未填：" + labels + "）"
    return "初步（本地梳理，最终以云端 meta 判断为准）"


def _local_hints(state: BoardState, trait_check: list[dict]) -> list[str]:
    hints: list[str] = []

    if state.gold is not None:
        if state.gold >= 50:
            hints.append(f"金币 {state.gold}：可吃满利息，优先存钱升人口")
        elif state.gold >= 30:
            hints.append(f"金币 {state.gold}：接近满利息，谨慎 D 牌")
        else:
            hints.append(f"金币 {state.gold}：偏低，注意别断利息")

    if state.hp is not None:
        if state.hp <= 30:
            hints.append(f"血量 {state.hp}：偏低，建议提前 D 牌稳血")
        elif state.hp <= 50:
            hints.append(f"血量 {state.hp}：中等，留意连败节奏")

    gaps = [t for t in trait_check if t["configured"] and t["active"] is None]
    if gaps:
        lines = [f"{t['name']} 差 {t['short_by']}" for t in gaps]
        hints.append("待补羁绊：" + "、".join(lines))

    return hints


def call_cloud(prompt: str, frame_path: str | None = None) -> dict:
    """预留：后期接云端大模型。

    接入方式（P1/P2）：把 prompt（+ 可选 frame_path 截图）发给 OpenAI 兼容接口，
    返回 JSON：``{advice, target_comp}``。当前 P0 不联网、不加载本地模型。
    """
    raise NotImplementedError("云端决策接口在后续阶段接入；P0 仅本地梳理。")


def decide(state: BoardState, frame_path: str | None = None) -> dict:
    trait_check = traits.analyze_traits(state.traits)
    hints = _local_hints(state, trait_check)
    trait_lines = [traits.format_line(t) for t in trait_check]

    sections = ["【本地梳理】"]
    sections += [f"- {h}" for h in hints] or ["- 暂无可确定的本地提示"]
    sections.append("【羁绊断点】")
    sections += [f"- {ln}" for ln in trait_lines] or ["- 未录入羁绊"]
    sections.append("【待云端判断】阵容方向、买牌取舍、装备分配、站位对位（P0 未接云端模型）")

    unresolved = list(state.unresolved)
    for k in _missing_fields(state):
        label = KEY_FIELDS[k]
        if label not in unresolved:
            unresolved.append(label)

    return {
        "advice": "\n".join(sections),
        "target_comp": None,
        "trait_check": trait_check,
        "confidence": _confidence(state),
        "unresolved": unresolved,
        "prompt": state.to_prompt_text(),
        "frame_path": frame_path,
    }
