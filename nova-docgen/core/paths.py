# -*- coding: utf-8 -*-
"""리소스 경로 (개발 실행 / PyInstaller .exe 공통).

ROOT: 읽기전용 번들 데이터(템플릿·폰트·hwpxskill·forms.json).
DATA: 쓰기 가능 위치(config.json) — exe 옆 또는 프로젝트 루트.
"""
import os
import sys
import shutil

_THIS = os.path.dirname(os.path.abspath(__file__))


def is_frozen():
    return getattr(sys, "frozen", False)


def root_dir():
    """번들된 읽기전용 데이터 루트."""
    if is_frozen():
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(_THIS)  # nova-docgen/


def data_dir():
    """쓰기 가능한 사용자 데이터 위치(설정 저장)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(_THIS)


ROOT = root_dir()
DATA = data_dir()

HWPXSKILL = os.path.join(ROOT, "core", "hwpxskill", "scripts")
TEMPLATES = os.path.join(ROOT, "templates")
ASSETS = os.path.join(ROOT, "assets")
FORMS_JSON = os.path.join(ROOT, "forms.json")


def config_path():
    """config.json 경로. exe 옆에 없으면 번들 기본본을 복사."""
    p = os.path.join(DATA, "config.json")
    if not os.path.exists(p):
        default = os.path.join(ROOT, "config.json")
        if os.path.exists(default) and os.path.abspath(default) != os.path.abspath(p):
            shutil.copyfile(default, p)
    return p
