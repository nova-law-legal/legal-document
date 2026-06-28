# -*- coding: utf-8 -*-
"""hwpxskill 스크립트를 in-process(runpy)로 실행. PyInstaller .exe에서도 동작."""
import os
import io
import sys
import runpy
import contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HWPXSKILL  # noqa: E402


def run_tool(script, args):
    """script(예: 'edit_hwpx.py' 또는 'office/unpack.py')를 args로 실행.
    (returncode, output) 반환."""
    script_path = os.path.join(HWPXSKILL, *script.split("/"))
    old_argv = sys.argv
    old_path = list(sys.path)
    # 형제 모듈 import(page_guard 등) + office 패키지 경로 보장
    for p in (HWPXSKILL, os.path.dirname(script_path)):
        if p not in sys.path:
            sys.path.insert(0, p)
    sys.argv = [script_path] + [str(a) for a in args]
    buf = io.StringIO()
    rc = 0
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            runpy.run_path(script_path, run_name="__main__")
    except SystemExit as e:
        code = e.code
        rc = 0 if code is None else (code if isinstance(code, int) else 1)
    except Exception as e:  # noqa: BLE001
        buf.write("EXC: %r\n" % e)
        rc = 1
    finally:
        sys.argv = old_argv
        sys.path = old_path
    return rc, buf.getvalue()
