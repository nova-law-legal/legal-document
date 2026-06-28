# 법무법인 노바 — 선임서류 생성기

사건 선임서류(위임장·선임신고서 등)를 양식 선택 → 입력만으로 자동 생성하는 윈도우 프로그램.
결과물은 **HWPX(한글)** 로 나오며, 한글이 설치돼 있으면 **PDF**로도 바로 출력됩니다.

## 빠른 시작 (직원용)
1. `dist\노바선임서류생성기.exe` 를 더블클릭해 실행합니다.
2. **① 양식 선택** — 만들 서류 종류를 고릅니다(변호인선임신고서, 소송위임장 등 9종).
3. **② 사건·당사자 입력**
   - 사건명, (민사면) 원고/피고, 관할기관을 입력합니다. ("귀중"은 자동으로 붙습니다.)
   - 당사자는 `+ 당사자 추가`로 여러 명 입력 가능하며, **개인/법인**을 전환할 수 있습니다.
   - `의뢰인 도장 자동 날인` 체크 시 의뢰인 이름의 빨강 타원 도장이 (인) 자리에 찍힙니다.
4. **③ 담당변호사** — 들어갈 변호사를 체크(다중선택)합니다.
5. **HWPX 생성** 또는 **PDF 생성** 버튼 → 저장 위치를 정하면 완성됩니다.

## 변호사 명단 관리
- 상단 `⚙ 설정(변호사 명단)` 에서 변호사 추가/수정/삭제 후 **저장**.
- 명단은 exe 옆 `config.json` 에 저장되어, 입·퇴사 시 코드 수정 없이 관리됩니다.

## 필요 환경
- 윈도우 + (PDF 출력 시) 한글 오피스 설치. HWPX 생성만이면 한글 없이도 동작.

## 폴더 구조 (개발용)
```
nova-docgen/
├── app.py                 # GUI 진입점 (python app.py 로도 실행)
├── config.json            # 법인정보·변호사 명단·도장 기본값 (사용자 편집)
├── forms.json             # 양식별 슬롯 매핑 (9종)
├── templates/             # 양식 .hwpx 템플릿 9종 (한글 무손실 변환본)
├── assets/                # 도장 글꼴 (충주김생체, 나눔고딕Bold)
├── core/
│   ├── fill_engine.py     # 입력→슬롯 치환 채우기 엔진
│   ├── stamp.py           # 도장(빨강 타원 막도장) 생성
│   ├── hwpx_stamp.py      # HWPX (인) 위치에 도장 이미지 삽입
│   ├── pdf_export.py      # HWPX→PDF (한글 COM)
│   ├── paths.py           # 개발/exe 공통 리소스 경로
│   ├── hwpx_tools.py      # hwpxskill in-process 실행
│   └── hwpxskill/         # HWPX 편집·검증 엔진 (github.com/Canine89/hwpxskill)
├── build/                 # 빌드 산출물/로그
└── dist/노바선임서류생성기.exe   # 배포용 실행파일
```

## 새 양식 추가 / 빌드
- 새 양식: 한글에서 .hwpx로 저장 → `templates/`에 넣고 → `build/convert_templates.py`로 변환 →
  `python core/hwpxskill/scripts/hwpx_slots.py <파일>` 로 슬롯 확인 → `forms.json`에 매핑 추가.
- 재빌드: `python -m PyInstaller --noconfirm --clean build_windowed.spec`

## 검증
- 헤드리스 자가점검: `노바선임서류생성기.exe selftest <출력경로.hwpx>` (종료코드 0 = 정상)
