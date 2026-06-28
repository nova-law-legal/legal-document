# -*- coding: utf-8 -*-
"""HWPX에 의뢰인 도장(인라인 이미지) 삽입.

채워진 .hwpx를 unpack → BinData에 도장 PNG 추가 → content.hpf 매니페스트 등록 →
section0.xml의 의뢰인 이름 문단 '(인)' 자리에 인라인 hp:pic 삽입 → pack.
"""
import os
import re
import shutil
import sys

from lxml import etree

NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "opf": "http://www.idpf.org/2007/opf/",
}
HP = NS["hp"]
HC = NS["hc"]

# 96dpi 기준 1px = 75 HWPUNIT
PX_TO_HU = 75


class _Res:
    def __init__(self, rc, out):
        self.returncode = rc
        self.stdout = out
        self.stderr = out


def _run(args):
    from hwpx_tools import run_tool
    rc, out = run_tool(args[0], args[1:])
    return _Res(rc, out)


def _next_image_index(bindata_dir):
    n = 0
    if os.path.isdir(bindata_dir):
        for f in os.listdir(bindata_dir):
            m = re.match(r"image(\d+)\.", f, re.I)
            if m:
                n = max(n, int(m.group(1)))
    return n + 1


def _inline_pic_xml(img_id, px_w, px_h, disp_hu):
    """인라인(treatAsChar=1) 도장 hp:pic Element 생성."""
    org_w = px_w * PX_TO_HU
    org_h = px_h * PX_TO_HU
    # 표시 크기: 높이를 disp_hu로, 폭은 비율 유지
    disp_h = disp_hu
    disp_w = int(disp_hu * px_w / px_h)
    sx = disp_w / org_w
    sy = disp_h / org_h
    xml = (
        '<hp:pic xmlns:hp="%(hp)s" xmlns:hc="%(hc)s" '
        'id="0" zOrder="100" numberingType="PICTURE" textWrap="IN_FRONT_OF_TEXT" '
        'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" href="" groupLevel="0" '
        'instid="0" reverse="0">'
        '<hp:offset x="0" y="0"/>'
        '<hp:orgSz width="%(ow)d" height="%(oh)d"/>'
        '<hp:curSz width="%(dw)d" height="%(dh)d"/>'
        '<hp:flip horizontal="0" vertical="0"/>'
        '<hp:rotationInfo angle="0" centerX="%(cx)d" centerY="%(cy)d" rotateimage="1"/>'
        '<hp:renderingInfo>'
        '<hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        '<hc:scaMatrix e1="%(sx)f" e2="0" e3="0" e4="0" e5="%(sy)f" e6="0"/>'
        '<hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        '</hp:renderingInfo>'
        '<hc:img binaryItemIDRef="%(id)s" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>'
        '<hp:imgRect>'
        '<hc:pt0 x="0" y="0"/><hc:pt1 x="%(ow)d" y="0"/>'
        '<hc:pt2 x="%(ow)d" y="%(oh)d"/><hc:pt3 x="0" y="%(oh)d"/>'
        '</hp:imgRect>'
        '<hp:imgClip left="0" right="%(ow)d" top="0" bottom="%(oh)d"/>'
        '<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        '<hp:imgDim dimwidth="%(ow)d" dimheight="%(oh)d"/>'
        '<hp:effects/>'
        '<hp:sz width="%(dw)d" widthRelTo="ABSOLUTE" height="%(dh)d" heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="1" '
        'holdAnchorAndSO="0" vertRelTo="LINE" horzRelTo="PARA" vertAlign="TOP" '
        'horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        '</hp:pic>'
    ) % {
        "hp": HP, "hc": HC, "id": img_id,
        "ow": org_w, "oh": org_h, "dw": disp_w, "dh": disp_h,
        "cx": disp_w // 2, "cy": disp_h // 2, "sx": sx, "sy": sy,
    }
    return etree.fromstring(xml.encode("utf-8"))


def _add_manifest_item(hpf_path, img_id, href):
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(hpf_path, parser)
    root = tree.getroot()
    manifest = root.find("opf:manifest", NS)
    item = etree.SubElement(manifest, "{%s}item" % NS["opf"])
    item.set("id", img_id)
    item.set("href", href)
    item.set("media-type", "image/png")
    item.set("isEmbeded", "1")
    tree.write(hpf_path, xml_declaration=True, encoding="UTF-8", standalone=True)


def _insert_seal_in_section(section_path, name_text, img_id, px_w, px_h, disp_hu,
                            anchor="(인)"):
    """이름 문단의 anchor('(인)')를 도장 인라인 이미지로 치환. 성공 여부 반환."""
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(section_path, parser)
    root = tree.getroot()

    key = "".join(name_text.split())  # 공백 무시 비교용
    target_para = None
    for p in root.iter("{%s}p" % HP):
        txt = "".join(t.text or "" for t in p.iter("{%s}t" % HP))
        if anchor in txt and key and key in "".join(txt.split()):
            target_para = p
            break
    if target_para is None:
        return False

    # anchor를 포함한 hp:t 찾기
    for t in target_para.iter("{%s}t" % HP):
        if t.text and anchor in t.text:
            run = t.getparent()  # hp:run
            before, _, after = t.text.partition(anchor)
            t.text = before
            pic = _inline_pic_xml(img_id, px_w, px_h, disp_hu)
            new_run = etree.SubElement(target_para, "{%s}run" % HP)
            cpr = run.get("charPrIDRef")
            if cpr is not None:
                new_run.set("charPrIDRef", cpr)
            new_run.append(pic)
            # run 위치: 원 run 바로 뒤로 이동
            run.addnext(new_run)
            if after:
                tail_run = etree.Element("{%s}run" % HP)
                if cpr is not None:
                    tail_run.set("charPrIDRef", cpr)
                tt = etree.SubElement(tail_run, "{%s}t" % HP)
                tt.text = after
                new_run.addnext(tail_run)
            tree.write(section_path, xml_declaration=True, encoding="UTF-8",
                       standalone=True)
            return True
    return False


def stamp_hwpx(in_hwpx, out_hwpx, name_text, png_path, disp_hu=2600,
               anchor="(인)", workdir=None):
    """채워진 hwpx에 도장 삽입 → out_hwpx. (ok, msg) 반환."""
    from PIL import Image
    tmp = workdir or (out_hwpx + "_unpack")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    r = _run(["office/unpack.py", in_hwpx, tmp])
    if r.returncode != 0:
        return False, "unpack 실패: " + r.stderr

    bindata = os.path.join(tmp, "BinData")
    os.makedirs(bindata, exist_ok=True)
    idx = _next_image_index(bindata)
    img_id = "image%d" % idx
    fname = "%s.png" % img_id
    shutil.copyfile(png_path, os.path.join(bindata, fname))
    px_w, px_h = Image.open(png_path).size

    _add_manifest_item(os.path.join(tmp, "Contents", "content.hpf"),
                       img_id, "BinData/" + fname)

    ok = _insert_seal_in_section(
        os.path.join(tmp, "Contents", "section0.xml"),
        name_text, img_id, px_w, px_h, disp_hu, anchor)
    if not ok:
        return False, "이름 문단의 '%s' 위치를 찾지 못했습니다." % anchor

    r = _run(["office/pack.py", tmp, out_hwpx])
    if r.returncode != 0:
        return False, "pack 실패: " + r.stderr
    return True, "도장 삽입 완료 (%s)" % img_id
