# -*- coding: utf-8 -*-
"""HWPX → PDF 변환 (한글 COM 사용). 검수용 PNG 렌더 헬퍼 포함."""
import os
import win32com.client as win32


def _new_hwp():
    hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
    try:
        hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
    except Exception:
        pass
    return hwp


def hwpx_to_pdf(src_hwpx, out_pdf, hwp=None):
    """src_hwpx를 out_pdf로 저장. 페이지 수 반환."""
    own = hwp is None
    if own:
        hwp = _new_hwp()
    try:
        hwp.Open(src_hwpx, "HWPX", "forceopen:true")
        pages = hwp.PageCount
        hwp.SaveAs(out_pdf, "PDF", "")
        hwp.Clear(1)
        return pages
    finally:
        if own:
            try:
                hwp.Quit()
            except Exception:
                pass


def pdf_to_pngs(pdf_path, out_dir, prefix="page", dpi=140):
    """검수용: PDF의 각 페이지를 PNG로 저장. 파일 경로 리스트 반환."""
    import fitz
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    paths = []
    for i, pg in enumerate(doc):
        p = os.path.join(out_dir, "%s_p%d.png" % (prefix, i + 1))
        pg.get_pixmap(dpi=dpi).save(p)
        paths.append(p)
    return paths


if __name__ == "__main__":
    import sys
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".pdf"
    print("pages:", hwpx_to_pdf(src, out))
    print("pdf:", out)
