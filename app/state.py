"""结构化棋盘状态（board state）。

字段对齐 docs/panel-design-lightweight.md 第 5 节；P0 只覆盖 MVP 子集，
缺失字段留空，不猜值。识别存疑字段记入 unresolved，面板置灰标注。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class ShopItem:
    """商店一张牌。"""

    name: str = ""
    cost: Optional[int] = None
    traits: list[str] = field(default_factory=list)


@dataclass
class BoardState:
    # 状态行（MVP 必做）
    stage: str = ""
    level: Optional[int] = None
    xp: str = ""
    gold: Optional[int] = None
    hp: Optional[int] = None
    streak: str = ""
    augments: list[str] = field(default_factory=list)
    pending_augments: list[str] = field(default_factory=list)

    # 羁绊 / 商店
    traits: list[dict] = field(default_factory=list)  # [{"name": str, "count": int}]
    shop: list[ShopItem] = field(default_factory=list)

    # P1 预留：场上 / 备战席 / 装备 / 对手
    board: list[dict] = field(default_factory=list)
    bench: list[dict] = field(default_factory=list)
    items: dict = field(default_factory=dict)
    opponent: dict = field(default_factory=dict)

    # 备注与存疑
    note: str = ""
    unresolved: list[str] = field(default_factory=list)
    locked: set[str] = field(default_factory=set)

    # ---- 序列化 ----

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["locked"] = sorted(self.locked)
        return data

    # ---- 存疑 / 锁定 ----

    def mark_unresolved(self, field_name: str) -> None:
        if field_name and field_name not in self.unresolved:
            self.unresolved.append(field_name)

    def lock(self, field_name: str) -> None:
        self.locked.add(field_name)

    def unlock(self, field_name: str) -> None:
        self.locked.discard(field_name)

    # ---- 喂给决策层的结构化文本 ----

    def _line(self, label: str, value: Any) -> str:
        if value is None or value == "" or value == []:
            return f"{label}: 未填"
        return f"{label}: {value}"

    def to_prompt_text(self) -> str:
        lines: list[str] = []
        lines.append(self._line("阶段", self.stage))
        level_part = f"{self.level}" if self.level is not None else "未填"
        if self.xp:
            level_part = f"{level_part} (经验 {self.xp})"
        lines.append(f"等级: {level_part}")
        lines.append(self._line("血量", self.hp))
        lines.append(self._line("金币", self.gold))
        lines.append(self._line("连胜/连败", self.streak))
        lines.append(self._line("已选海克斯", "、".join(self.augments) if self.augments else ""))
        lines.append(self._line("待选海克斯", "、".join(self.pending_augments) if self.pending_augments else ""))

        if self.traits:
            trait_txt = ", ".join(f"{t['name']}{t['count']}" for t in self.traits)
            lines.append(f"已激活羁绊: {trait_txt}")
        else:
            lines.append("已激活羁绊: 未填")

        if self.shop:
            lines.append("商店:")
            for i, item in enumerate(self.shop, start=1):
                cost = f"{item.cost}费" if item.cost is not None else "费用?"
                traits = f"[{'、'.join(item.traits)}]" if item.traits else "[]"
                lines.append(f"  {i}. {item.name} {cost} {traits}")
        else:
            lines.append("商店: 未填")

        if self.note:
            lines.append(f"备注: {self.note}")

        if self.unresolved:
            lines.append(f"视觉待确认: {', '.join(self.unresolved)}")

        return "\n".join(lines)
