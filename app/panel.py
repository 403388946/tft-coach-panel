"""Tkinter 轻量侧边栏面板（P0）。

布局 440×760，分区：局面状态 / 羁绊 / 商店 / 场上备注 / 建议区 / 备注。
面板只读取画面与手动录入、给本地梳理建议；所有游戏操作由玩家本人完成。
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from . import capture, decide
from .state import BoardState, ShopItem

APP_TITLE = "TFT 参谋面板（P0）"
PANEL_W, PANEL_H = 440, 760


def _parse_int(text: str) -> int | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _split_tags(text: str) -> list[str]:
    """按逗号 / 顿号拆分标签，去空白与空项。"""
    parts = text.replace("，", ",").replace("、", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


def _parse_traits(text: str) -> list[dict]:
    """解析羁绊录入，每行 `名称:数量` 或 `名称 数量`；缺省数量记 1。"""
    traits: list[dict] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if ":" in line:
            name, cnt = line.split(":", 1)
        elif " " in line:
            name, cnt = line.rsplit(" ", 1)
        else:
            name, cnt = line, "1"
        count = _parse_int(cnt) or 1
        traits.append({"name": name.strip(), "count": count})
    return traits


class CoachPanel(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(f"{PANEL_W}x{PANEL_H}")
        self.resizable(False, True)
        self.frame_path: str | None = None
        self.last_capture_ms: int | None = None
        self.shop_entries: list[tuple[tk.Entry, tk.Entry]] = []
        self.lock_vars: dict[str, tk.BooleanVar] = {}
        self._build_ui()

    # ---------- UI 构建 ----------

    def _build_ui(self) -> None:
        self._build_top()
        self._build_state()
        self._build_traits()
        self._build_shop()
        self._build_board_note()
        self._build_advice()
        self._build_note()

    def _build_top(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Button(bar, text="重抓帧", command=self.on_capture).pack(side="left")
        ttk.Button(bar, text="生成建议", command=self.on_decide).pack(side="left", padx=4)
        ttk.Button(bar, text="复制局面文本", command=self.on_copy_prompt).pack(side="left")
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(bar, textvariable=self.status_var, foreground="#666").pack(
            side="left", padx=6
        )

    def _build_state(self) -> None:
        box = ttk.LabelFrame(self, text="局面状态")
        box.pack(fill="x", padx=8, pady=4)

        self.var_stage = tk.StringVar()
        self.var_level = tk.StringVar()
        self.var_xp = tk.StringVar()
        self.var_gold = tk.StringVar()
        self.var_hp = tk.StringVar()
        self.var_streak = tk.StringVar()
        self.var_augments = tk.StringVar()
        self.var_pending = tk.StringVar()

        fields = [
            ("stage", "阶段", self.var_stage, "如 4-2"),
            ("level", "等级", self.var_level, "如 8"),
            ("xp", "经验", self.var_xp, "如 0/76"),
            ("gold", "金币", self.var_gold, "如 29"),
            ("hp", "血量", self.var_hp, "如 80"),
            ("streak", "连胜/连败", self.var_streak, "如 W3 / L2"),
        ]
        for i, (key, label, var, hint) in enumerate(fields):
            row, col = divmod(i, 3)
            cell = ttk.Frame(box)
            cell.grid(row=row, column=col, padx=6, pady=4, sticky="w")
            ttk.Label(cell, text=label, width=6).pack(side="left")
            entry = ttk.Entry(cell, textvariable=var, width=8)
            entry.pack(side="left")
            entry.bind("<FocusIn>", lambda _e, h=hint: self.status_var.set(h))
            self.lock_vars[key] = tk.BooleanVar(value=False)
            ttk.Checkbutton(cell, text="锁", variable=self.lock_vars[key],
                            width=3).pack(side="left", padx=(2, 0))

        hex_row = ttk.Frame(box)
        hex_row.grid(row=2, column=0, columnspan=3, padx=6, pady=4, sticky="w")
        ttk.Label(hex_row, text="已选海克斯", width=9).pack(side="left")
        ttk.Entry(hex_row, textvariable=self.var_augments, width=14).pack(side="left")
        ttk.Label(hex_row, text="待选", width=5).pack(side="left", padx=(8, 0))
        ttk.Entry(hex_row, textvariable=self.var_pending, width=14).pack(side="left")

    def _build_traits(self) -> None:
        box = ttk.LabelFrame(self, text="羁绊（每行：名称:数量）")
        box.pack(fill="x", padx=8, pady=4)
        self.trait_text = tk.Text(box, height=4, width=52)
        self.trait_text.pack(padx=6, pady=4, fill="x")

    def _build_shop(self) -> None:
        box = ttk.LabelFrame(self, text="商店（5 张）")
        box.pack(fill="x", padx=8, pady=4)
        head = ttk.Frame(box)
        head.pack(fill="x", padx=6, pady=(4, 0))
        ttk.Label(head, text="#", width=3).pack(side="left")
        ttk.Label(head, text="牌名", width=22).pack(side="left")
        ttk.Label(head, text="费用", width=8).pack(side="left")
        for i in range(5):
            row = ttk.Frame(box)
            row.pack(fill="x", padx=6, pady=2)
            ttk.Label(row, text=str(i + 1), width=3).pack(side="left")
            name_e = ttk.Entry(row, width=22)
            name_e.pack(side="left", padx=(0, 6))
            cost_e = ttk.Entry(row, width=8)
            cost_e.pack(side="left")
            self.shop_entries.append((name_e, cost_e))

    def _build_board_note(self) -> None:
        box = ttk.LabelFrame(self, text="场上 / 备战席（P1）")
        box.pack(fill="x", padx=8, pady=4)
        ttk.Label(box, text="星级 / 装备 / 站位待确认，见备注栏",
                  foreground="#888").pack(padx=6, pady=4, anchor="w")

    def _build_advice(self) -> None:
        box = ttk.LabelFrame(self, text="建议")
        box.pack(fill="both", expand=True, padx=8, pady=4)
        self.advice = tk.Text(box, height=10, wrap="word")
        self.advice.pack(padx=6, pady=4, fill="both", expand=True)
        self.conf_var = tk.StringVar(value="可信度：—")
        ttk.Label(box, textvariable=self.conf_var, foreground="#666").pack(
            anchor="w", padx=6, pady=(0, 2)
        )
        self.unresolved_var = tk.StringVar(value="存疑：—")
        ttk.Label(box, textvariable=self.unresolved_var, foreground="#a33").pack(
            anchor="w", padx=6, pady=(0, 4)
        )

    def _build_note(self) -> None:
        box = ttk.LabelFrame(self, text="备注")
        box.pack(fill="x", padx=8, pady=4)
        self.note_entry = ttk.Entry(box)
        self.note_entry.pack(padx=6, pady=4, fill="x")

    # ---------- 状态读取 ----------

    def _read_state(self) -> BoardState:
        state = BoardState()
        state.stage = self.var_stage.get().strip()
        state.level = _parse_int(self.var_level.get())
        state.xp = self.var_xp.get().strip()
        state.gold = _parse_int(self.var_gold.get())
        state.hp = _parse_int(self.var_hp.get())
        state.streak = self.var_streak.get().strip()
        state.augments = _split_tags(self.var_augments.get())
        state.pending_augments = _split_tags(self.var_pending.get())
        state.traits = _parse_traits(self.trait_text.get("1.0", "end"))

        for name_e, cost_e in self.shop_entries:
            name = name_e.get().strip()
            cost = _parse_int(cost_e.get())
            if name or cost is not None:
                state.shop.append(ShopItem(name=name, cost=cost))

        state.note = self.note_entry.get().strip()

        # 勾选锁定的字段记入 state（回填时跳过，避免覆盖手动值）
        for key, var in self.lock_vars.items():
            if var.get():
                state.lock(key)

        # 关键数字字段未填 → 存疑（保守标注，不猜值）
        if state.level is None:
            state.mark_unresolved("等级")
        if state.gold is None:
            state.mark_unresolved("金币")
        if state.hp is None:
            state.mark_unresolved("血量")
        if not state.shop:
            state.mark_unresolved("商店")
        return state

    # ---------- 事件 ----------

    def on_capture(self) -> None:
        self.status_var.set("抓帧中…")

        def worker() -> None:
            res = capture.capture_frame(width=1600)
            self.after(0, lambda: self._after_capture(res))

        threading.Thread(target=worker, daemon=True).start()

    def _after_capture(self, res: dict) -> None:
        if res["ok"]:
            self.frame_path = res["frame_path"]
            self.last_capture_ms = res["elapsed_ms"]
            self.status_var.set(
                f"已抓帧 {res['mode']} {res['elapsed_ms']}ms"
            )
        else:
            self.status_var.set("抓帧失败")
            messagebox.showwarning("抓帧失败", res["error"] or "未找到游戏窗口")

    def on_decide(self) -> None:
        state = self._read_state()
        self.status_var.set("思考中…")
        t0 = time.perf_counter()
        try:
            result = decide.decide(state, frame_path=self.frame_path)
        except Exception as exc:  # 决策失败：保留上一条建议，不覆盖
            self.status_var.set("决策失败，保留上一条建议")
            messagebox.showwarning("决策失败", str(exc))
            return
        elapsed_ms = (time.perf_counter() - t0) * 1000

        self.advice.delete("1.0", "end")
        self.advice.insert("1.0", result["advice"])
        capture_note = f"｜抓帧 {self.last_capture_ms}ms" if self.last_capture_ms else ""
        self.conf_var.set(
            f"可信度：{result['confidence']}｜决策 {elapsed_ms:.0f}ms{capture_note}"
        )
        unresolved = result.get("unresolved") or []
        self.unresolved_var.set(
            "存疑：" + ("、".join(unresolved) if unresolved else "无")
        )
        self.status_var.set("建议已生成")

    def on_copy_prompt(self) -> None:
        state = self._read_state()
        self.clipboard_clear()
        self.clipboard_append(state.to_prompt_text())
        self.status_var.set("局面文本已复制，可贴给云端对话")


def main() -> None:
    app = CoachPanel()
    app.mainloop()


if __name__ == "__main__":
    main()
