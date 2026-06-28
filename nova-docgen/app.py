# -*- coding: utf-8 -*-
"""법무법인 노바 — 선임서류 생성기 (데스크톱 GUI)."""
import os
import sys
import tempfile
import datetime
import traceback

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

from fill_engine import fill_form, load_forms, load_config, save_config  # noqa: E402
from stamp import save_stamp  # noqa: E402
from hwpx_stamp import stamp_hwpx  # noqa: E402
from pdf_export import hwpx_to_pdf  # noqa: E402

ID_LABEL = {"rrn": "주민등록번호", "birth": "생년월일", "none": ""}


class PartyRow(ttk.Frame):
    """당사자 1명 입력 행 (개인/법인 전환)."""

    def __init__(self, master, form, on_delete):
        super().__init__(master, padding=(6, 4))
        self.form = form
        self.on_delete = on_delete
        self.type_var = tk.StringVar(value="개인")
        self.vars = {k: tk.StringVar() for k in
                     ("name", "id", "address", "phone", "ceo")}
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        fields = self.form.get("party_fields", [])
        id_kind = self.form.get("id_kind", "rrn")
        is_corp = self.type_var.get() == "법인"
        col = 0

        if self.form.get("supports_corporation", False):
            ttk.Label(self, text="구분").grid(row=0, column=col, padx=2)
            cb = ttk.Combobox(self, width=5, state="readonly",
                              values=["개인", "법인"], textvariable=self.type_var)
            cb.grid(row=0, column=col + 1, padx=2)
            cb.bind("<<ComboboxSelected>>", lambda e: self._build())
            col += 2

        name_label = "법인명" if is_corp else "성명"
        ttk.Label(self, text=name_label).grid(row=0, column=col, padx=2)
        ttk.Entry(self, width=12, textvariable=self.vars["name"]).grid(
            row=0, column=col + 1, padx=2)
        col += 2

        if "rrn" in fields or "birth" in fields:
            id_label = "법인등록번호" if is_corp else ID_LABEL.get(id_kind, "번호")
            ttk.Label(self, text=id_label).grid(row=0, column=col, padx=2)
            ttk.Entry(self, width=16, textvariable=self.vars["id"]).grid(
                row=0, column=col + 1, padx=2)
            col += 2

        if "address" in fields:
            ttk.Label(self, text="주소").grid(row=0, column=col, padx=2)
            ttk.Entry(self, width=30, textvariable=self.vars["address"]).grid(
                row=0, column=col + 1, padx=2)
            col += 2

        if "phone" in fields:
            ttk.Label(self, text="연락처").grid(row=0, column=col, padx=2)
            ttk.Entry(self, width=14, textvariable=self.vars["phone"]).grid(
                row=0, column=col + 1, padx=2)
            col += 2

        if is_corp:
            ttk.Label(self, text="대표자").grid(row=0, column=col, padx=2)
            ttk.Entry(self, width=8, textvariable=self.vars["ceo"]).grid(
                row=0, column=col + 1, padx=2)
            col += 2

        ttk.Button(self, text="삭제", width=4,
                   command=lambda: self.on_delete(self)).grid(
            row=0, column=col, padx=6)

    def get(self):
        is_corp = self.type_var.get() == "법인"
        d = {"type": "corp" if is_corp else "person",
             "name": self.vars["name"].get().strip(),
             "address": self.vars["address"].get().strip(),
             "phone": self.vars["phone"].get().strip()}
        idv = self.vars["id"].get().strip()
        if is_corp:
            d["corp_reg"] = idv
            d["ceo"] = self.vars["ceo"].get().strip()
        elif self.form.get("id_kind") == "birth":
            d["birth"] = idv
        else:
            d["rrn"] = idv
        return d


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("법무법인 노바 — 선임서류 생성기")
        self.geometry("1024x720")
        self.cfg = load_config()
        self.forms = load_forms()
        self.form_list = list(self.forms.values())
        self.party_rows = []
        self.lawyer_vars = []
        self._build()
        self._on_form_change()

    # ---------- UI ----------
    def _build(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="① 양식 선택", font=("맑은 고딕", 11, "bold")).pack(side="left")
        self.form_var = tk.StringVar()
        self.form_cb = ttk.Combobox(top, width=40, state="readonly",
                                    textvariable=self.form_var,
                                    values=[f["title"] for f in self.form_list])
        self.form_cb.current(0)
        self.form_cb.pack(side="left", padx=10)
        self.form_cb.bind("<<ComboboxSelected>>", lambda e: self._on_form_change())
        ttk.Button(top, text="⚙ 설정(변호사 명단)",
                   command=self._open_settings).pack(side="right")

        body = ttk.Frame(self, padding=(10, 0))
        body.pack(fill="both", expand=True)

        # 왼쪽: 입력
        left = ttk.LabelFrame(body, text="② 사건 · 당사자 입력", padding=10)
        left.pack(side="left", fill="both", expand=True)

        self.case_var = tk.StringVar()
        self.plaintiff_var = tk.StringVar()
        self.defendant_var = tk.StringVar()
        self.court_var = tk.StringVar()
        self.stamp_var = tk.BooleanVar(value=self.cfg.get("stamp", {}).get("enabled_default", True))

        self.dyn = ttk.Frame(left)
        self.dyn.pack(fill="both", expand=True)

        # 오른쪽: 담당변호사
        right = ttk.LabelFrame(body, text="③ 담당변호사 (다중선택)", padding=10)
        right.pack(side="right", fill="y")
        self.lawyer_frame = ttk.Frame(right)
        self.lawyer_frame.pack(fill="both", expand=True)
        self._build_lawyers()

        # 하단 버튼
        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")
        self.status = tk.StringVar(value="준비됨")
        ttk.Label(bottom, textvariable=self.status, foreground="#0a0").pack(side="left")
        ttk.Button(bottom, text="HWPX 생성", command=lambda: self._generate("hwpx")).pack(side="right", padx=4)
        ttk.Button(bottom, text="PDF 생성", command=lambda: self._generate("pdf")).pack(side="right", padx=4)

    def _build_lawyers(self):
        for w in self.lawyer_frame.winfo_children():
            w.destroy()
        self.lawyer_vars = []
        for lw in self.cfg["lawyers"]:
            v = tk.BooleanVar(value=False)
            ttk.Checkbutton(self.lawyer_frame,
                            text="%s (%s)" % (lw["name"], lw["reg"]),
                            variable=v).pack(anchor="w")
            self.lawyer_vars.append((v, lw))

    def _cur_form(self):
        return self.form_list[self.form_cb.current()]

    def _on_form_change(self):
        form = self._cur_form()
        for w in self.dyn.winfo_children():
            w.destroy()
        self.party_rows = []
        r = 0
        # 사건
        ttk.Label(self.dyn, text="사건명").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(self.dyn, width=50, textvariable=self.case_var).grid(
            row=r, column=1, sticky="w"); r += 1
        # 원고/피고 (민사)
        if "plaintiff" in form["slots"]:
            ttk.Label(self.dyn, text="원고").grid(row=r, column=0, sticky="w", pady=3)
            ttk.Entry(self.dyn, width=50, textvariable=self.plaintiff_var).grid(
                row=r, column=1, sticky="w"); r += 1
            ttk.Label(self.dyn, text="피고").grid(row=r, column=0, sticky="w", pady=3)
            ttk.Entry(self.dyn, width=50, textvariable=self.defendant_var).grid(
                row=r, column=1, sticky="w"); r += 1
        # 당사자 영역
        pl = ttk.Label(self.dyn, text="%s" % form.get("party_term", "당사자"),
                       font=("맑은 고딕", 10, "bold"))
        pl.grid(row=r, column=0, sticky="nw", pady=(10, 3))
        self.party_area = ttk.Frame(self.dyn)
        self.party_area.grid(row=r, column=1, sticky="w"); r += 1
        ttk.Button(self.dyn, text="+ 당사자 추가",
                   command=self._add_party).grid(row=r, column=1, sticky="w", pady=4); r += 1
        # 관할
        hint = form.get("court_hint", "")
        ttk.Label(self.dyn, text="관할기관").grid(row=r, column=0, sticky="w", pady=3)
        fr = ttk.Frame(self.dyn); fr.grid(row=r, column=1, sticky="w")
        ttk.Entry(fr, width=30, textvariable=self.court_var).pack(side="left")
        ttk.Label(fr, text="  + '귀중' 자동 (예: 인천%s)" % hint,
                  foreground="#888").pack(side="left"); r += 1
        # 도장
        ttk.Checkbutton(self.dyn, text="의뢰인 도장 자동 날인 (타원·빨강)",
                        variable=self.stamp_var).grid(row=r, column=1, sticky="w", pady=6); r += 1

        self._add_party()

    def _add_party(self):
        row = PartyRow(self.party_area, self._cur_form(), self._del_party)
        row.pack(fill="x", pady=2)
        self.party_rows.append(row)

    def _del_party(self, row):
        if len(self.party_rows) <= 1:
            return
        self.party_rows.remove(row)
        row.destroy()

    # ---------- 생성 ----------
    def _collect(self):
        form = self._cur_form()
        parties = [r.get() for r in self.party_rows]
        parties = [p for p in parties if p["name"]]
        data = {
            "case": self.case_var.get().strip(),
            "court": self.court_var.get().strip(),
            "parties": parties,
            "lawyers": [lw for v, lw in self.lawyer_vars if v.get()],
        }
        if "plaintiff" in form["slots"]:
            data["plaintiff"] = self.plaintiff_var.get().strip()
            data["defendant"] = self.defendant_var.get().strip()
        return form, data

    def _generate(self, kind):
        form, data = self._collect()
        if not data["parties"]:
            messagebox.showwarning("입력 필요", "당사자 이름을 1명 이상 입력하세요.")
            return
        if not data["lawyers"]:
            if not messagebox.askyesno("확인", "담당변호사를 선택하지 않았습니다. 그대로 진행할까요?"):
                return
        # 저장 위치
        default_name = self._default_filename(form, data)
        ext = "pdf" if kind == "pdf" else "hwpx"
        path = filedialog.asksaveasfilename(
            defaultextension="." + ext,
            initialfile=default_name + "." + ext,
            filetypes=[(ext.upper(), "*." + ext)])
        if not path:
            return
        try:
            self.status.set("생성 중...")
            self.update_idletasks()
            hwpx_out = path if ext == "hwpx" else os.path.splitext(path)[0] + ".hwpx"
            ok, log = fill_form(form["id"], data, hwpx_out, self.forms, self.cfg)
            if not ok:
                raise RuntimeError(log)
            # 도장
            if self.stamp_var.get():
                self._apply_stamp(form, data, hwpx_out)
            # PDF
            if ext == "pdf":
                hwpx_to_pdf(hwpx_out, path)
                if hwpx_out != path and os.path.exists(hwpx_out):
                    try: os.remove(hwpx_out)
                    except OSError: pass
            self.status.set("완료: " + os.path.basename(path))
            if messagebox.askyesno("완료", "생성되었습니다.\n%s\n\n폴더를 열까요?" % path):
                os.startfile(os.path.dirname(path))
        except Exception as e:
            self.status.set("오류")
            messagebox.showerror("오류", "생성 실패:\n%s" % e + "\n\n" + traceback.format_exc()[-800:])

    def _apply_stamp(self, form, data, hwpx_out):
        # 도장 슬롯이 있는 양식만, 첫 개인 당사자 기준
        person = next((p for p in data["parties"] if p.get("type") != "corp"), None)
        if person is None:
            person = data["parties"][0]
        name = person["name"]
        seal_png = os.path.join(tempfile.gettempdir(), "seal_tmp.png")
        save_stamp(name.replace(" ", ""), seal_png)
        tmp = hwpx_out + ".stamp.hwpx"
        ok, msg = stamp_hwpx(hwpx_out, tmp, name, seal_png)
        if ok:
            os.replace(tmp, hwpx_out)

    def _default_filename(self, form, data):
        today = datetime.date.today().strftime("%y%m%d")
        nm = data["parties"][0]["name"].replace(" ", "") if data["parties"] else ""
        return "%s_%s_%s" % (today, form["title"].split("(")[0].strip(), nm)

    # ---------- 설정 ----------
    def _open_settings(self):
        SettingsDialog(self)


class SettingsDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("변호사 명단 관리")
        self.geometry("420x440")
        self.transient(app)
        self.grab_set()
        self.lawyers = [dict(l) for l in app.cfg["lawyers"]]
        self._build()

    def _build(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=("name", "reg"), show="headings", height=12)
        self.tree.heading("name", text="이름")
        self.tree.heading("reg", text="등록번호")
        self.tree.column("name", width=160)
        self.tree.column("reg", width=160)
        self.tree.pack(fill="both", expand=True)
        self._refresh()

        ed = ttk.Frame(frame); ed.pack(fill="x", pady=8)
        self.name_v = tk.StringVar(); self.reg_v = tk.StringVar()
        ttk.Label(ed, text="이름").grid(row=0, column=0)
        ttk.Entry(ed, width=12, textvariable=self.name_v).grid(row=0, column=1, padx=4)
        ttk.Label(ed, text="등록번호").grid(row=0, column=2)
        ttk.Entry(ed, width=12, textvariable=self.reg_v).grid(row=0, column=3, padx=4)
        ttk.Button(ed, text="추가/수정", command=self._add).grid(row=0, column=4, padx=4)

        btns = ttk.Frame(frame); btns.pack(fill="x")
        ttk.Button(btns, text="선택 삭제", command=self._del).pack(side="left")
        ttk.Button(btns, text="저장", command=self._save).pack(side="right")
        self.tree.bind("<<TreeviewSelect>>", self._on_sel)

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        for l in self.lawyers:
            self.tree.insert("", "end", values=(l["name"], l["reg"]))

    def _on_sel(self, e):
        sel = self.tree.selection()
        if sel:
            n, r = self.tree.item(sel[0])["values"]
            self.name_v.set(n); self.reg_v.set(r)

    def _add(self):
        name = self.name_v.get().strip(); reg = self.reg_v.get().strip()
        if not name or not reg:
            return
        for l in self.lawyers:
            if l["name"] == name:
                l["reg"] = reg
                self._refresh(); return
        self.lawyers.append({"name": name, "reg": reg})
        self._refresh()

    def _del(self):
        sel = self.tree.selection()
        if not sel:
            return
        n = self.tree.item(sel[0])["values"][0]
        self.lawyers = [l for l in self.lawyers if l["name"] != n]
        self._refresh()

    def _save(self):
        self.app.cfg["lawyers"] = self.lawyers
        save_config(self.app.cfg)
        self.app._build_lawyers()
        messagebox.showinfo("저장", "변호사 명단을 저장했습니다.")
        self.destroy()


def _selftest(out_path):
    """헤드리스 종단 검증 (frozen exe 패키징 확인용)."""
    cfg = load_config()
    forms = load_forms()
    data = {
        "case": "셀프테스트 사건",
        "parties": [{"type": "person", "name": "홍 길 동",
                     "rrn": "900101-1234567", "address": "인천 미추홀구 한나루로 436"}],
        "court": "인천지방검찰청",
        "lawyers": cfg["lawyers"][:3],
    }
    ok, log = fill_form("criminal_defense", data, out_path, forms, cfg)
    if ok:
        person = data["parties"][0]
        seal = os.path.join(tempfile.gettempdir(), "seal_selftest.png")
        save_stamp(person["name"].replace(" ", ""), seal)
        tmp = out_path + ".s.hwpx"
        sok, _ = stamp_hwpx(out_path, tmp, person["name"], seal)
        if sok:
            os.replace(tmp, out_path)
    print("SELFTEST", "OK" if ok else "FAIL")
    print(log)
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
            tempfile.gettempdir(), "novadoc_selftest.hwpx")
        sys.exit(_selftest(out))
    App().mainloop()
