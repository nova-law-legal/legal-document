# -*- coding: utf-8 -*-
"""선임서류 채우기 엔진.

입력값(사건/당사자/관할/담당변호사) → 양식별 슬롯 매핑(forms.json)에 따라
hwpxskill(edit_hwpx.py)로 .hwpx 셀/문단 텍스트만 치환한다.
검증: validate.py + finalize + page_guard.py.
"""
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HWPXSKILL, TEMPLATES, FORMS_JSON, config_path  # noqa: E402


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_config():
    return _load_json(config_path())


def save_config(cfg):
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_forms():
    data = _load_json(FORMS_JSON)
    return {f["id"]: f for f in data["forms"]}


# ---------- 렌더링 헬퍼 ----------

def fmt_lawyer(lw):
    return "%s(%s)" % (lw["name"], lw["reg"])


def render_lawyer_lines(selected, n_slots, per_line=3):
    """선택된 변호사를 per_line개씩 줄로 묶어 n_slots개 슬롯 문자열 리스트로 반환.
    마지막 줄을 제외하고 줄 끝에 콤마를 붙여 원본 양식 스타일을 따른다."""
    items = [fmt_lawyer(l) for l in selected]
    # per_line개씩 줄 생성
    lines = [items[i:i + per_line] for i in range(0, len(items), per_line)]
    line_strs = []
    for i, ln in enumerate(lines):
        s = ", ".join(ln)
        if i != len(lines) - 1:
            s += ","
        line_strs.append(s)
    # 슬롯 수에 맞춰: 줄이 슬롯보다 많으면 마지막 슬롯에 합치고, 적으면 빈칸으로
    out = ["" for _ in range(n_slots)]
    if len(line_strs) <= n_slots:
        for i, s in enumerate(line_strs):
            out[i] = s
    else:
        for i in range(n_slots - 1):
            out[i] = line_strs[i]
        out[n_slots - 1] = " ".join(line_strs[n_slots - 1:])
    return out


def party_display_name(p):
    return p.get("name", "").strip()


def party_id_value(p, id_kind):
    if p.get("type") == "corp":
        return p.get("corp_reg", "").strip()
    if id_kind == "birth":
        return p.get("birth", "").strip()
    return p.get("rrn", "").strip()


def party_address_value(p):
    addr = p.get("address", "").strip()
    if p.get("type") == "corp" and p.get("ceo"):
        addr = (addr + "  (대표자 %s)" % p["ceo"]).strip()
    return addr


def join_parties(parties, valfn):
    """다수 당사자: 1개면 값 그대로, 2개 이상이면 '1. .. 2. ..' 번호 매김."""
    vals = [valfn(p) for p in parties]
    vals = [v for v in vals if v != ""]
    if len(vals) <= 1:
        return vals[0] if vals else ""
    return "  ".join("%d. %s" % (i + 1, v) for i, v in enumerate(vals))


# ---------- 슬롯값 생성 ----------

def build_slot_values(form, data, firm):
    """form(매핑) + data(입력) → {slot_key: text} dict."""
    slots = form["slots"]
    parties = data.get("parties") or []
    id_kind = form.get("id_kind", "rrn")
    values = {}

    def put(slot_def, text):
        key = slot_def["key"]
        tmpl = slot_def.get("template", "{value}")
        values[key] = tmpl.replace("{value}", text) \
            .replace("{name}", text).replace("{rrn}", text) \
            .replace("{birth}", text).replace("{address}", text) \
            .replace("{phone}", text).replace("{court}", text) \
            .replace("{detention_center}", text)

    # 사건
    if "case" in slots and "case" in data:
        values[slots["case"]["key"]] = data["case"]

    # 원고/피고 (민사)
    if "plaintiff" in slots and data.get("plaintiff"):
        values[slots["plaintiff"]["key"]] = data["plaintiff"]
    if "defendant" in slots and data.get("defendant"):
        values[slots["defendant"]["key"]] = data["defendant"]

    # 당사자 인적사항
    if "name" in slots and parties:
        put(slots["name"], join_parties(parties, party_display_name))
    if "rrn" in slots and parties:
        put(slots["rrn"], join_parties(parties, lambda p: party_id_value(p, id_kind)))
    if "birth" in slots and parties:
        put(slots["birth"], join_parties(parties, lambda p: party_id_value(p, id_kind)))
    if "address" in slots and parties:
        put(slots["address"], join_parties(parties, party_address_value))
    if "phone" in slots and parties:
        put(slots["phone"], join_parties(parties, lambda p: p.get("phone", "").strip()))

    # 특수: 구속 무인용
    if "detention_no" in slots and data.get("detention_no"):
        values[slots["detention_no"]["key"]] = data["detention_no"]
    if "detention_center" in slots and data.get("detention_center"):
        put(slots["detention_center"], data["detention_center"])

    # 관할기관
    if "court" in slots and data.get("court"):
        court = data["court"].strip()
        if court.endswith("귀중"):
            values[slots["court"]["key"]] = court
        else:
            put(slots["court"], court)

    # 담당변호사 (일반: 3줄 블록)
    selected = data.get("lawyers") or []
    if "lawyers" in slots and selected:
        keys = slots["lawyers"]["keys"]
        per_line = slots["lawyers"].get("per_line", 3)
        lines = render_lawyer_lines(selected, len(keys), per_line)
        for k, s in zip(keys, lines):
            values[k] = s

    # 담당변호사 (철회서: '변호사 {name} (인)' 줄들)
    if "lawyers_withdraw" in slots and selected:
        keys = slots["lawyers_withdraw"]["keys"]
        tmpl = slots["lawyers_withdraw"].get("template", "변호사 {name} (인)")
        for i, k in enumerate(keys):
            if i < len(selected):
                values[k] = tmpl.replace("{name}", selected[i]["name"])
            else:
                values[k] = ""

    # 담당변호사 (사임신고서: 한 문단에 '담당변호사 X' 반복)
    if "lawyers_resign" in slots and selected:
        sd = slots["lawyers_resign"]
        prefix = sd.get("prefix", "담당변호사 ")
        parts = [prefix + l["name"] for l in selected]
        values[sd["key"]] = "  ".join(parts)

    return values


# ---------- 외부 스크립트 호출 ----------

def _run(args):
    # args[0]은 스크립트명, 나머지는 인자
    from hwpx_tools import run_tool
    return run_tool(args[0], args[1:])


def fill_form(form_id, data, out_path, forms=None, config=None):
    """양식을 채워 out_path(.hwpx)로 저장. (ok, log) 반환."""
    forms = forms or load_forms()
    config = config or load_config()
    form = forms[form_id]
    template = os.path.join(TEMPLATES, form["template"])
    log = []

    values = build_slot_values(form, data, config["firm"])
    if not values:
        return False, "채울 값이 없습니다."

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as tf:
        json.dump(values, tf, ensure_ascii=False)
        vjson = tf.name

    try:
        rc, out = _run(["edit_hwpx.py", template, "-o", out_path,
                        "--slot-json", vjson, "--allow-over-budget"])
        log.append("[edit] rc=%d\n%s" % (rc, out.strip()))
        if rc != 0:
            return False, "\n".join(log)

        rc, out = _run(["finalize_hwpx.py", out_path, "--strip-linesegarray", "--layout"])
        log.append("[finalize] rc=%d %s" % (rc, out.strip().splitlines()[-1] if out.strip() else ""))

        rc, out = _run(["validate.py", out_path])
        log.append("[validate] rc=%d %s" % (rc, out.strip().splitlines()[-1] if out.strip() else ""))
        if rc != 0:
            return False, "\n".join(log)

        rc, out = _run(["page_guard.py", "--reference", template, "--output", out_path,
                        "--no-strict-paragraph-budget", "--skip-text-drift",
                        "--allow-empty-fill"])
        log.append("[page_guard] rc=%d %s" % (rc, out.strip().splitlines()[-1] if out.strip() else ""))
    finally:
        try:
            os.unlink(vjson)
        except OSError:
            pass

    return True, "\n".join(log)


if __name__ == "__main__":
    # 간단 셀프테스트
    cfg = load_config()
    forms = load_forms()
    sample = {
        "case": "2026형제12345호 사기",
        "parties": [{"type": "person", "name": "홍 길 동",
                     "rrn": "900101-1234567",
                     "address": "인천광역시 미추홀구 한나루로 436"}],
        "court": "인천지방검찰청",
        "lawyers": [cfg["lawyers"][0], cfg["lawyers"][5], cfg["lawyers"][6]],
    }
    out = os.path.join(tempfile.gettempdir(), "selftest_criminal_defense.hwpx")
    ok, log = fill_form("criminal_defense", sample, out, forms, cfg)
    print("OK" if ok else "FAIL")
    print(log)
    print("OUT:", out)
