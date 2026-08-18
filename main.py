# -*- coding: utf-8 -*-
import os
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.core.window import Window
from kivy.utils import platform

ROW_H = dp(46)
BTN_H = dp(46)
HDR_H = dp(30)

INK = (0.1, 0.1, 0.1, 1)
BLUE_BTN = (0.13, 0.35, 0.87, 1)
RED_BTN = (0.85, 0.30, 0.30, 1)
CARD_BG = (0.96, 0.97, 0.99, 1)
INPUT_BG = (0.9, 0.93, 0.96, 1)
BORDER = (0.42, 0.5, 0.62, 1)


def L(text, **kw):
    kw.setdefault("color", INK)
    return Label(text=text, **kw)


def B(text, on_release=None, bg=None, fg=None, **kw):
    if bg is None:
        bg = BLUE_BTN
    if fg is None:
        fg = (1, 1, 1, 1)
    kw.setdefault("background_normal", "")
    kw.setdefault("background_down", "")
    kw.setdefault("background_color", bg)
    kw.setdefault("color", fg)
    return Button(text=text, on_release=on_release, **kw)


def TI(**kw):
    kw.setdefault("background_normal", "")
    kw.setdefault("background_active", "")
    kw.setdefault("background_color", INPUT_BG)
    kw.setdefault("foreground_color", INK)
    ti = TextInput(**kw)
    _bordered_input(ti)
    return ti


def _bordered_input(ti):
    with ti.canvas.after:
        Color(rgba=BORDER)
        ti._border = Line(width=dp(1.5))
    def _paint(*_a):
        ti._border.rounded_rectangle = (ti.x, ti.y, ti.width, ti.height, dp(4))
    ti.bind(pos=_paint, size=_paint)
    _paint()
    return ti


def fmt_time(minutes):
    minutes = int(minutes)
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def compute_timeline(parsed, breaks):
    parsed = [dict(t) for t in parsed]
    for t in parsed:
        t["ops"] = [dict(o) for o in t["ops"]]
    parsed.sort(key=lambda x: x["start"])
    for t in parsed:
        boundary = t["start"]
        for op in t["ops"]:
            op["dur"] = op["end"] - boundary
            boundary = op["end"]

    DAY = 24 * 60
    breaks_sorted = sorted(breaks, key=lambda x: x["start"])
    timeline = []
    order = 0

    done = [False] * len(parsed)
    op_i = [0] * len(parsed)
    op_worked = [0] * len(parsed)
    task_start = [None] * len(parsed)
    task_end = [None] * len(parsed)
    seg_count = {}

    i_b = 0
    open_seg = None
    open_start = None

    def close_op(t):
        nonlocal open_seg, open_start, order
        if open_seg is not None and open_start is not None:
            ti, oi = open_seg
            key = (ti, oi)
            seg_count[key] = seg_count.get(key, 0) + 1
            timeline.append({"order": order, "kind": "op",
                             "name": parsed[ti]["ops"][oi]["name"],
                             "s": open_start, "e": t, "seg": seg_count[key],
                             "tkey": key})
            order += 1
            open_seg = None
            open_start = None

    for t in range(DAY):
        while i_b < len(breaks_sorted) and t >= breaks_sorted[i_b]["start"] + breaks_sorted[i_b]["dur"]:
            i_b += 1
        in_break = (i_b < len(breaks_sorted)
                    and breaks_sorted[i_b]["start"] <= t < breaks_sorted[i_b]["start"] + breaks_sorted[i_b]["dur"])
        if in_break:
            if open_seg is not None:
                close_op(t)
            continue

        ti = None
        for idx in range(len(parsed)):
            if not done[idx] and parsed[idx]["start"] <= t:
                ti = idx
                break
        if ti is None:
            continue

        task = parsed[ti]
        oi = op_i[ti]
        op = task["ops"][oi]

        if open_seg is None:
            open_seg = (ti, oi)
            open_start = t
        if task_start[ti] is None:
            task_start[ti] = t

        op_worked[ti] += 1
        if op_worked[ti] >= op["dur"]:
            close_op(t + 1)
            op_i[ti] += 1
            op_worked[ti] = 0
            if op_i[ti] >= len(task["ops"]):
                done[ti] = True
                task_end[ti] = t + 1

    for idx in range(len(parsed)):
        timeline.append({"order": order, "kind": "task", "name": parsed[idx]["name"],
                         "s": task_start[idx], "e": task_end[idx], "ti": idx})
        order += 1
    for br in breaks_sorted:
        timeline.append({"order": order, "kind": "br", "name": br["name"],
                         "s": br["start"], "e": br["start"] + br["dur"]})
        order += 1

    timeline.sort(key=lambda r: (r["s"] is None, r["s"], 0 if r["kind"] == "task" else 1, r["order"]))
    return timeline


def auto_box(**kw):
    b = BoxLayout(orientation="vertical", size_hint_y=None, **kw)
    b.bind(minimum_height=b.setter("height"))
    return b


class TimeInput(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="horizontal", size_hint=(None, None),
                         size=(dp(96), ROW_H), spacing=dp(2), **kw)
        self.h = TI(input_filter="int", multiline=False, halign="center",
                    font_size=sp(20), size_hint=(0.45, 1),
                    hint_text="ЧЧ", hint_text_color=(0.55, 0.6, 0.7, 1))
        colon = L(text=":", font_size=sp(20), size_hint=(0.1, 1))
        self.m = TI(input_filter="int", multiline=False, halign="center",
                    font_size=sp(20), size_hint=(0.45, 1),
                    hint_text="ММ", hint_text_color=(0.55, 0.6, 0.7, 1))
        self.add_widget(self.h)
        self.add_widget(colon)
        self.add_widget(self.m)

        def _clamp(field, maxv):
            def _on_text(*_a):
                if not field.text:
                    return
                try:
                    n = int(field.text)
                except ValueError:
                    field.text = ""
                    return
                if n > maxv:
                    field.text = str(maxv)
            return _on_text

        self.h.bind(text=_clamp(self.h, 24))
        self.m.bind(text=_clamp(self.m, 59))

        def _to_minutes(*_a):
            if len(self.h.text) >= 2 and self.h.focus:
                self.m.focus = True
        self.h.bind(text=_to_minutes)


class ScheduleApp(App):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.tasks = []
        self.break_rows = []
        self._counter_task = 0
        self._counter_break = 0
        self._save_job = None
        self._loading = False
        self._last_timeline = None
        self._last_parsed = None
        self._last_alarm_times = None
        self._alarms = []
        self._popups = []

    def build(self):
        if getattr(self, "_root", None) is not None:
            return self._root
        Window.clearcolor = (1, 1, 1, 1)
        if platform != "android":
            Window.size = (480, 900)
        root = BoxLayout(orientation="vertical")
        scroll = ScrollView(size_hint=(1, 1), bar_width=dp(6))
        box = auto_box(padding=[dp(8), dp(6), dp(8), dp(12)], spacing=dp(6))
        scroll.add_widget(box)
        root.add_widget(scroll)
        self.body = box

        box.add_widget(L(text="Планировщик заданий с перерывами",
                             size_hint=(1, None), height=HDR_H,
                             font_size=sp(20), bold=True))
        box.add_widget(L(text="Задания и операции:", size_hint=(1, None),
                             height=HDR_H, font_size=sp(16), bold=True))
        self.tasks_box = auto_box(spacing=dp(6))
        box.add_widget(self.tasks_box)
        self.new_task_btn = B(text="+ Добавить новое задание",
                                   size_hint=(1, None), height=BTN_H,
                                   on_release=lambda *a: self.add_task())
        box.add_widget(self.new_task_btn)

        box.add_widget(L(text="Перерывы:", size_hint=(1, None),
                             height=HDR_H, font_size=sp(16), bold=True))
        self.breaks_box = auto_box(spacing=dp(4))
        box.add_widget(self.breaks_box)
        self.add_break_btn = B(text="+ Добавить перерыв",
                                    size_hint=(1, None), height=BTN_H,
                                    on_release=lambda *a: self.add_break())
        box.add_widget(self.add_break_btn)

        ctrl = BoxLayout(orientation="horizontal", size_hint=(1, None), height=BTN_H, spacing=dp(8))
        calc = B(text="РАССЧИТАТЬ ВРЕМЯ", size_hint_x=1, on_release=lambda *a: self.recompute())
        self.full_check = CheckBox(size_hint=(None, 1), active=True)
        full_lb = L(text="Полное время", size_hint=(None, 1), halign="left")
        ctrl.add_widget(calc)
        ctrl.add_widget(self.full_check)
        ctrl.add_widget(full_lb)
        box.add_widget(ctrl)

        reset_row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=BTN_H, spacing=dp(8))
        reset_row.add_widget(B(text="Сброс заданий", on_release=lambda *a: self.clear_tasks(), bg=RED_BTN))
        reset_row.add_widget(B(text="Сброс перерывов", on_release=lambda *a: self.clear_breaks(), bg=RED_BTN))
        box.add_widget(reset_row)

        box.add_widget(B(text="Создать будильники", size_hint=(1, None), height=BTN_H,
                         on_release=lambda *a: self.create_alarms()))

        box.add_widget(L(text="Будильники:", size_hint=(1, None), height=HDR_H,
                             font_size=sp(16), bold=True))
        self.alarms_box = auto_box(spacing=dp(2))
        box.add_widget(self.alarms_box)
        alarm_row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=BTN_H, spacing=dp(8))
        alarm_row.add_widget(B(text="Отменить все", on_release=lambda *a: self.cancel_all_alarms(), bg=RED_BTN))
        alarm_row.add_widget(B(text="Задать заново", on_release=lambda *a: self.reschedule_alarms()))
        alarm_row.add_widget(B(text="Тест (15 сек)", on_release=lambda *a: self.test_alarm()))
        box.add_widget(alarm_row)
        diag_row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=BTN_H, spacing=dp(8))
        diag_row.add_widget(B(text="Проверить", on_release=lambda *a: self.check_fire_log()))
        diag_row.add_widget(B(text="Очистить лог", on_release=lambda *a: self.clear_fire_log()))
        box.add_widget(diag_row)

        box.add_widget(L(text="Итоговое время:", size_hint=(1, None),
                             height=HDR_H, font_size=sp(16), bold=True))
        self.result_grid = GridLayout(cols=4, size_hint_y=None, spacing=(dp(4), dp(2)))
        self.result_grid.bind(minimum_height=self.result_grid.setter("height"))
        box.add_widget(self.result_grid)

        self.total_label = L(text="", size_hint=(1, None), height=HDR_H + dp(8),
                                 font_size=sp(18), bold=True)
        box.add_widget(self.total_label)

        self._root = root
        self._load_state()
        self._reschedule_from_snapshot()
        return root

    # ---------------- tasks ----------------
    def add_task(self, name=None):
        self._counter_task += 1
        n = self._counter_task
        card = auto_box(padding=[dp(8), dp(6), dp(8), dp(6)], spacing=dp(6))
        with card.canvas.before:
            Color(rgba=CARD_BG)
            card._rect = RoundedRectangle(radius=[dp(10)])
        def _paint(*_a):
            card._rect.pos = card.pos
            card._rect.size = card.size
        card.bind(pos=_paint, size=_paint)

        row0 = BoxLayout(orientation="horizontal", size_hint=(1, None), height=ROW_H, spacing=dp(4))
        row0.add_widget(L(text="Время:", size_hint=(None, None), size=(dp(56), ROW_H)))
        ti = TimeInput()
        self._watch(ti.h, ti.m)
        row0.add_widget(ti)
        row0.add_widget(L(text="Название:", size_hint=(None, None), size=(dp(84), ROW_H)))
        name_in = TI(text=name or "Задание %d" % n, multiline=False,
                            font_size=sp(16), size_hint_x=1)
        self._watch(name_in)
        row0.add_widget(name_in)
        del_btn = B(text="×", size_hint=(None, None), size=(dp(44), ROW_H),
                         on_release=lambda *a: self.remove_task(card))
        row0.add_widget(del_btn)

        ops_area = auto_box(spacing=dp(4))
        add_op_btn = B(text="+ Добавить операцию", size_hint=(1, None), height=BTN_H,
                            on_release=lambda *a: self.add_operation(card))

        card.add_widget(row0)
        card.add_widget(ops_area)
        card.add_widget(add_op_btn)

        self.tasks_box.add_widget(card)
        self.tasks.append({"card": card, "ti": ti, "name_in": name_in,
                           "ops_area": ops_area, "add_op_btn": add_op_btn,
                           "op_n": 0, "ops": []})
        self._schedule_save()
        return card

    def add_operation(self, card, name=None):
        task = self._get_task(card)
        if task is None:
            return
        task["op_n"] += 1
        n = task["op_n"]
        row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=ROW_H, spacing=dp(4))
        name_in = TI(text=name or "Операция %d" % n, multiline=False,
                            font_size=sp(16), size_hint_x=1)
        self._watch(name_in)
        row.add_widget(name_in)
        row.add_widget(L(text="до:", size_hint=(None, None), size=(dp(32), ROW_H)))
        ti = TimeInput()
        self._watch(ti.h, ti.m)
        row.add_widget(ti)
        del_btn = B(text="×", size_hint=(None, None), size=(dp(44), ROW_H),
                         on_release=lambda *a: self.remove_operation(task, row))
        row.add_widget(del_btn)
        task["ops_area"].add_widget(row)
        task["ops"].append({"row": row, "name_in": name_in, "ti": ti})
        self._schedule_save()

    def remove_task(self, card):
        for i, t in enumerate(self.tasks):
            if t["card"] is card:
                self.tasks_box.remove_widget(t["card"])
                del self.tasks[i]
                break
        self._schedule_save()

    def remove_operation(self, task, row):
        for i, op in enumerate(task["ops"]):
            if op["row"] is row:
                del task["ops"][i]
                break
        task["ops_area"].remove_widget(row)
        self._schedule_save()

    def _get_task(self, card):
        for t in self.tasks:
            if t["card"] is card:
                return t
        return None

    # ---------------- breaks ----------------
    def add_break(self, name=None):
        self._counter_break += 1
        n = self._counter_break
        row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=ROW_H, spacing=dp(4))
        name_in = TI(text=name or "Перерыв %d" % n, multiline=False,
                            font_size=sp(16), size_hint_x=1)
        self._watch(name_in)
        row.add_widget(name_in)
        row.add_widget(L(text="с:", size_hint=(None, None), size=(dp(24), ROW_H)))
        s_ti = TimeInput()
        self._watch(s_ti.h, s_ti.m)
        row.add_widget(s_ti)
        row.add_widget(L(text="до:", size_hint=(None, None), size=(dp(32), ROW_H)))
        e_ti = TimeInput()
        self._watch(e_ti.h, e_ti.m)
        row.add_widget(e_ti)
        del_btn = B(text="×", size_hint=(None, None), size=(dp(44), ROW_H),
                         on_release=lambda *a: self.remove_break(row))
        row.add_widget(del_btn)
        self.breaks_box.add_widget(row)
        self.break_rows.append({"row": row, "name_in": name_in, "s_ti": s_ti, "e_ti": e_ti})
        self._schedule_save()

    def remove_break(self, row):
        for i, b in enumerate(self.break_rows):
            if b["row"] is row:
                del self.break_rows[i]
                break
        self.breaks_box.remove_widget(row)
        self._schedule_save()

    # ---------------- reset ----------------
    def _dialog(self, title, msg, on_ok):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=[dp(16), dp(12)])
        with content.canvas.before:
            Color(rgba=(1, 1, 1, 1))
            content._rect = Rectangle()
        def _paint(*_a):
            content._rect.pos = content.pos
            content._rect.size = content.size
        content.bind(pos=_paint, size=_paint)

        content.add_widget(L(msg, size_hint=(1, None), height=dp(110),
                             text_size=(dp(300), None), halign="center", valign="middle"))
        btns = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(46), spacing=dp(10))
        def _ok(*_a):
            popup.dismiss()
            on_ok()
        btns.add_widget(B(text="Да", on_release=_ok))
        btns.add_widget(B(text="Отмена", on_release=lambda *a: popup.dismiss()))
        content.add_widget(btns)
        popup = Popup(title=title, content=content, size_hint=(None, None),
                      size=(dp(360), dp(220)), auto_dismiss=False)
        popup.open()

    def clear_tasks(self):
        if not self.tasks:
            return
        self._dialog("Сброс", "Удалить все задания с операциями?", self._do_clear_tasks)

    def _do_clear_tasks(self):
        for t in list(self.tasks):
            self.tasks_box.remove_widget(t["card"])
        self.tasks = []
        self._counter_task = 0
        self._schedule_save()

    def clear_breaks(self):
        if not self.break_rows:
            return
        self._dialog("Сброс", "Удалить все перерывы?", self._do_clear_breaks)

    def _do_clear_breaks(self):
        for b in list(self.break_rows):
            self.breaks_box.remove_widget(b["row"])
        self.break_rows = []
        self._counter_break = 0
        self._schedule_save()

    # ---------------- persistence ----------------
    def _state_path(self):
        p = os.environ.get("SCHEDULE_STATE")
        if p:
            return p
        return os.path.join(self.user_data_dir, "data.json")

    def _watch(self, *inputs):
        for w in inputs:
            w.bind(text=self._on_change)

    def _on_change(self, *_a):
        if self._loading:
            return
        self._schedule_save()

    def _schedule_save(self):
        if self._save_job is not None:
            Clock.unschedule(self._save_job)
        self._save_job = Clock.schedule_once(lambda dt: self._save_state(), 0.5)

    def _collect_state(self):
        return {
            "tasks": [
                {
                    "name": t["name_in"].text,
                    "h": t["ti"].h.text,
                    "m": t["ti"].m.text,
                    "ops": [
                        {"name": o["name_in"].text,
                         "h": o["ti"].h.text,
                         "m": o["ti"].m.text}
                        for o in t["ops"]
                    ],
                }
                for t in self.tasks
            ],
            "breaks": [
                {
                    "name": b["name_in"].text,
                    "sh": b["s_ti"].h.text,
                    "sm": b["s_ti"].m.text,
                    "eh": b["e_ti"].h.text,
                    "em": b["e_ti"].m.text,
                }
                for b in self.break_rows
            ],
            "alarms": list(self._alarms),
        }

    def _save_state(self):
        self._save_job = None
        path = self._state_path()
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    old = f.read()
                if old.strip():
                    with open(path + ".bak", "w", encoding="utf-8") as f:
                        f.write(old)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._collect_state(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _apply_state(self, st):
        for t in st.get("tasks", []):
            self.add_task(name=t.get("name", ""))
            task = self.tasks[-1]
            task["ti"].h.text = t.get("h", "")
            task["ti"].m.text = t.get("m", "")
            for o in t.get("ops", []):
                self.add_operation(task["card"], name=o.get("name", ""))
                op = task["ops"][-1]
                op["ti"].h.text = o.get("h", "")
                op["ti"].m.text = o.get("m", "")
        for b in st.get("breaks", []):
            self.add_break(name=b.get("name", ""))
            rec = self.break_rows[-1]
            rec["s_ti"].h.text = b.get("sh", "")
            rec["s_ti"].m.text = b.get("sm", "")
            rec["e_ti"].h.text = b.get("eh", "")
            rec["e_ti"].m.text = b.get("em", "")
        for a in st.get("alarms", []):
            self._alarms.append({"time": a.get("time", 0),
                                 "msg": a.get("msg", ""),
                                 "on": bool(a.get("on", True))})

    def _load_state(self):
        path = self._state_path()
        st = None
        try:
            with open(path, "r", encoding="utf-8") as f:
                st = json.load(f)
        except Exception:
            try:
                with open(path + ".bak", "r", encoding="utf-8") as f:
                    st = json.load(f)
            except Exception:
                return
        if not isinstance(st, dict):
            return
        self._loading = True
        try:
            self._apply_state(st)
        finally:
            self._loading = False
        self._rebuild_alarms_box()

    def on_stop(self):
        self._save_state()

    # ---------------- alarms ----------------
    def create_alarms(self):
        self.recompute()
        if self._last_timeline is None:
            return
        parsed = self._last_parsed or []
        alarms = set()
        msgs = {}
        for r in self._last_timeline:
            if r["kind"] == "task" and r["s"] is not None:
                alarms.add(r["s"])
        op_end = {}
        op_bracket = {}
        for r in self._last_timeline:
            if r["kind"] == "op" and r["s"] is not None and r["e"] is not None:
                k = r.get("tkey")
                if k is not None:
                    if op_end.get(k, -1) < r["e"]:
                        op_end[k] = r["e"]
                        ti, oi = k
                        op_bracket[k] = parsed[ti]["ops"][oi]["end"]
        for k, e in op_end.items():
            alarms.add(e)
            msgs[e] = "(%s)" % fmt_time(op_bracket[k])
        for r in self._last_timeline:
            if r["kind"] == "br" and r["s"] is not None and r["e"] is not None:
                alarms.add(r["s"])
                alarms.add(r["e"])
                msgs[r["s"]] = r["name"]
                if "обед" in r["name"].lower():
                    msgs[r["e"]] = "Конец обеда"
                else:
                    msgs[r["e"]] = "Конец перерыва"
        if not alarms:
            self._show_error("Нет заданий для создания будильников.")
            return
        self._show_alarms(sorted(alarms), msgs)

    def _show_alarms(self, times, msgs):
        self._last_alarm_times = list(times)
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=[dp(16), dp(12)])
        with content.canvas.before:
            Color(rgba=(1, 1, 1, 1))
            content._rect = Rectangle()
        def _paint(*_a):
            content._rect.pos = content.pos
            content._rect.size = content.size
        content.bind(pos=_paint, size=_paint)

        content.add_widget(L("Будильники будут созданы в приложении:",
                             size_hint=(1, None), height=dp(36),
                             font_size=sp(16), bold=True))
        scroll = ScrollView(size_hint=(1, 1), bar_width=dp(6))
        lst = auto_box(spacing=dp(2))
        for t in times:
            text = fmt_time(t)
            m = msgs.get(t, "")
            if m:
                text = "%s %s" % (text, m)
            lst.add_widget(L(text, size_hint=(1, None), height=ROW_H,
                             font_size=sp(14), halign="center"))
        scroll.add_widget(lst)
        content.add_widget(scroll)
        content.add_widget(L("Приложение напомнит в заданное время уведомлением. "
                             "Управлять будильниками можно в разделе «Будильники».",
                             size_hint=(1, None), height=dp(44),
                             text_size=(dp(300), None), halign="center",
                             font_size=sp(13)))

        btns = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(46), spacing=dp(10))
        btns.add_widget(B(text="Подтвердить", on_release=lambda *a: self._confirm_alarms(times, msgs)))
        btns.add_widget(B(text="Отмена", on_release=lambda *a: popup.dismiss()))
        content.add_widget(btns)

        popup = Popup(title="Будильники", content=content,
                      size_hint=(None, None), size=(dp(360), dp(480)), auto_dismiss=False)
        self._popups.append(popup)
        popup.bind(on_dismiss=lambda *a: self._forget_popup(popup))
        popup.open()

    def _forget_popup(self, popup):
        try:
            self._popups.remove(popup)
        except ValueError:
            pass

    def _confirm_alarms(self, times, msgs):
        self._active_popup_dismiss()
        new_alarms = [{"time": t, "msg": msgs.get(t, ""), "on": True} for t in times]
        if platform != "android":
            self._alarms = new_alarms
            self._rebuild_alarms_box()
            return
        self._grant_alarm_permissions()
        for a in self._alarms:
            self._cancel_android_alarm(a)
        self._alarms = new_alarms
        self._schedule_android_alarms(self._alarms)
        self._write_alarm_snapshot()
        self._rebuild_alarms_box()
        self._show_info("Готово", "Установлено %d будильник(ов).\n\n"
                         "Включённые будут звонить уведомлением в нужное время.\n"
                         "Список — в разделе «Будильники»." % len(self._alarms))

    def _active_popup_dismiss(self):
        for w in self._popups:
            w.dismiss()

    def _rebuild_alarms_box(self):
        if not hasattr(self, "alarms_box"):
            return
        self.alarms_box.clear_widgets()
        if not self._alarms:
            self.alarms_box.add_widget(L(text="Будильники не созданы.",
                                         size_hint=(1, None), height=ROW_H,
                                         font_size=sp(14), color=(0.4, 0.45, 0.5, 1)))
            return
        for i, a in enumerate(self._alarms):
            row = BoxLayout(orientation="horizontal", size_hint=(1, None),
                            height=ROW_H, spacing=dp(4))
            cb = CheckBox(size_hint=(None, 1), active=a.get("on", True))
            cb.bind(active=lambda w, val, idx=i: self._toggle_alarm(idx, val))
            row.add_widget(cb)
            text = fmt_time(a["time"])
            if a.get("msg"):
                text = "%s %s" % (text, a["msg"])
            row.add_widget(L(text, size_hint_x=1, font_size=sp(14), halign="left"))
            self.alarms_box.add_widget(row)

    def _toggle_alarm(self, idx, active):
        if idx < 0 or idx >= len(self._alarms):
            return
        self._alarms[idx]["on"] = bool(active)
        if platform == "android":
            if active:
                self._schedule_android_alarms([self._alarms[idx]])
            else:
                self._cancel_android_alarm(self._alarms[idx])
            self._write_alarm_snapshot()
        self._rebuild_alarms_box()

    def cancel_all_alarms(self):
        if not self._alarms:
            return
        for a in self._alarms:
            a["on"] = False
        if platform == "android":
            for a in self._alarms:
                self._cancel_android_alarm(a)
            self._write_alarm_snapshot()
        self._rebuild_alarms_box()
        self._show_error("Все будильники отключены.")

    def reschedule_alarms(self):
        if not self._alarms:
            self._show_error("Будильники не созданы.")
            return
        if platform != "android":
            self._show_error("На десктопе установка недоступна.")
            return
        self._grant_alarm_permissions()
        self._schedule_android_alarms(self._alarms)
        self._write_alarm_snapshot()
        self._show_info("Готово", "Будильники обновлены.")

    def test_alarm(self):
        try:
            from jnius import autoclass
            AlarmReceiver = autoclass("org.example.toratime.AlarmReceiver")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            act = PythonActivity.mActivity
            AlarmReceiver.testAlarm(act)
        except Exception as e:
            self._show_error("Тест не удался:\n%s" % e)

    def check_fire_log(self):
        try:
            from jnius import autoclass
            AlarmReceiver = autoclass("org.example.toratime.AlarmReceiver")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            act = PythonActivity.mActivity
            txt = AlarmReceiver.readFireLog(act)
            self._show_info("Лог срабатываний", txt)
        except Exception as e:
            self._show_error("Не удалось прочитать лог:\n%s" % e)

    def clear_fire_log(self):
        try:
            from jnius import autoclass
            AlarmReceiver = autoclass("org.example.toratime.AlarmReceiver")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            act = PythonActivity.mActivity
            AlarmReceiver.clearFireLog(act)
            self._show_info("Готово", "Лог очищен.")
        except Exception as e:
            self._show_error("Не удалось очистить лог:\n%s" % e)

    def _write_alarm_snapshot(self):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            act = PythonActivity.mActivity
            prefs = act.getSharedPreferences("toratime", Context.MODE_PRIVATE)
            data = [[a["time"], a.get("msg", "")] for a in self._alarms if a.get("on", True)]
            prefs.edit().putString("alarm_snapshot", json.dumps(data)).commit()
        except Exception:
            pass

    def _reschedule_from_snapshot(self):
        try:
            from jnius import autoclass
            AlarmReceiver = autoclass("org.example.toratime.AlarmReceiver")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            act = PythonActivity.mActivity
            AlarmReceiver.rescheduleAllFromSnapshot(act)
        except Exception:
            pass

    def _grant_alarm_permissions(self):
        try:
            from jnius import autoclass
            AlarmReceiver = autoclass("org.example.toratime.AlarmReceiver")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            act = PythonActivity.mActivity
            AlarmReceiver.requestPermissions(act)
        except Exception as e:
            self._show_error("Не удалось запросить разрешения:\n%s" % e)

    def _schedule_android_alarms(self, alarms):
        try:
            from jnius import autoclass
            AlarmReceiver = autoclass("org.example.toratime.AlarmReceiver")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            act = PythonActivity.mActivity
            for a in alarms:
                if not a.get("on", True):
                    continue
                minutes = a["time"]
                msg = a.get("msg", "") or fmt_time(minutes)
                AlarmReceiver.scheduleNext(act, minutes, msg)
        except Exception as e:
            self._show_error("Не удалось запланировать будильники:\n%s" % e)

    def _cancel_android_alarm(self, a):
        try:
            from jnius import autoclass
            AlarmReceiver = autoclass("org.example.toratime.AlarmReceiver")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            act = PythonActivity.mActivity
            AlarmReceiver.cancel(act, a.get("time", 0))
        except Exception as e:
            self._show_error("Не удалось отменить будильник:\n%s" % e)

    # ---------------- recompute ----------------
    def _show_error(self, msg):
        content = L(text=msg, text_size=(dp(340), None), halign="center")
        popup = Popup(title="Ошибка", content=content,
                      size_hint=(None, None), size=(dp(360), dp(200)))
        popup.open()

    def _show_info(self, title, msg):
        content = L(text=msg, text_size=(dp(340), None), halign="center")
        popup = Popup(title=title, content=content,
                      size_hint=(None, None), size=(dp(360), dp(200)))
        popup.open()

    def _read_time(self, ti):
        h_txt = ti.h.text.strip()
        m_txt = ti.m.text.strip()
        if not h_txt or not m_txt:
            raise ValueError("время")
        try:
            h = int(h_txt)
            m = int(m_txt)
        except ValueError:
            raise ValueError("время")
        if not (0 <= h <= 24) or not (0 <= m <= 59):
            raise ValueError("время")
        return h * 60 + m

    def _result_cell(self, text, halign="left"):
        lb = L(text=text, halign=halign, valign="middle",
                   size_hint_y=None, height=ROW_H, font_size=sp(14))
        if halign == "left":
            lb.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
        return lb

    def recompute(self):
        self._last_timeline = None
        if not self.tasks:
            self._show_error("Добавьте хотя бы одно задание.")
            return
        self._save_state()

        breaks = []
        for b in self.break_rows:
            try:
                s = self._read_time(b["s_ti"])
                e = self._read_time(b["e_ti"])
            except ValueError:
                self._show_error("Неверное время перерыва «%s»." % b["name_in"].text)
                return
            if e <= s:
                self._show_error("Конец перерыва «%s» должен быть позже начала." % b["name_in"].text)
                return
            breaks.append({"name": b["name_in"].text, "start": s, "dur": e - s})

        parsed = []
        for t in self.tasks:
            try:
                start = self._read_time(t["ti"])
            except ValueError:
                self._show_error("Неверное время задания «%s»." % t["name_in"].text)
                return
            ops = []
            boundary = start
            for op in t["ops"]:
                name = op["name_in"].text
                try:
                    end = self._read_time(op["ti"])
                except ValueError:
                    self._show_error("Неверное время окончания операции «%s»." % name)
                    return
                if end <= boundary:
                    self._show_error("Окончание операции «%s» должно быть позже предыдущего времени." % name)
                    return
                ops.append({"name": name, "end": end})
                boundary = end
            parsed.append({"name": t["name_in"].text, "start": start, "ops": ops})

        timeline = compute_timeline(parsed, breaks)
        self._last_timeline = timeline
        self._last_parsed = parsed

        self.result_grid.clear_widgets()
        for col in ("Элемент", "Начало", "Конец", "Продолжительность"):
            self.result_grid.add_widget(L(text=col, bold=True,
                                              size_hint_y=None, height=HDR_H,
                                              font_size=sp(14)))
        full = self.full_check.active
        prev_end = None
        op_work = {}
        op_max_end = {}
        for r in timeline:
            if r["kind"] == "op" and r["s"] is not None and r["e"] is not None:
                k = r["tkey"]
                op_work[k] = op_work.get(k, 0) + r["e"] - r["s"]
                op_max_end[k] = max(op_max_end.get(k, r["s"]), r["e"])

        for i, r in enumerate(timeline):
            if r["s"] is None or r["e"] is None:
                continue
            bracket = None
            if r["kind"] == "task":
                ti = r["ti"]
                text = r["name"]
                dur = "%d мин" % (r["e"] - r["s"]) if full else ""
            elif r["kind"] == "op":
                ti, oi = r["tkey"]
                seg = " (продолжение)" if r.get("seg", 0) > 1 else ""
                is_last_seg = r["e"] == op_max_end[r["tkey"]]
                is_last_op = oi == len(parsed[ti]["ops"]) - 1
                closing = is_last_seg and is_last_op
                text = r["name"] + seg
                if closing:
                    text += " (Закрытие)"
                if is_last_seg:
                    bracket = parsed[ti]["ops"][oi]["end"]
                dur = "%d мин" % op_work[r["tkey"]]
            else:
                text = r["name"]
                dur = "%d мин" % (r["e"] - r["s"])

            if r["kind"] in ("br", "task"):
                s_disp = fmt_time(r["s"])
            elif full or i == 0:
                s_disp = fmt_time(r["s"])
            elif prev_end is not None and r["s"] > prev_end:
                s_disp = fmt_time(r["s"])
            else:
                s_disp = ""
            if not full and r["kind"] == "task":
                e_disp = ""
            else:
                e_disp = fmt_time(r["e"])
            if bracket is not None and e_disp:
                e_disp = "%s (%s)" % (e_disp, fmt_time(bracket))
            prev_end = r["e"]

            self.result_grid.add_widget(self._result_cell(text))
            self.result_grid.add_widget(self._result_cell(s_disp, "center"))
            self.result_grid.add_widget(self._result_cell(e_disp, "center"))
            self.result_grid.add_widget(self._result_cell(dur, "center"))

        total_min = sum(r["e"] - r["s"] for r in timeline
                        if r["kind"] == "op" and r["s"] is not None and r["e"] is not None)
        h, m = divmod(total_min, 60)
        if h and m:
            total_text = "%d ч %d мин" % (h, m)
        elif h:
            total_text = "%d ч" % h
        else:
            total_text = "%d мин" % m
        self.total_label.text = "Общее рабочее время: %s" % total_text


if __name__ == "__main__":
    ScheduleApp().run()
