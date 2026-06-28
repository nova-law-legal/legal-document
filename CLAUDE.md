# CLAUDE.md — 법무법인 노바 선임서류 생성기

> 이 파일은 향후 Claude 세션이 프로젝트를 빠르게 파악해 이어서 작업하도록 돕는 안내서다.
> 사용자(법무법인 노바)는 비개발자다. 변경 시 친절히 설명하고, 결과물은 실제 렌더링으로 검증할 것.

## 1. 프로젝트 개요
사건 선임서류(위임장·선임신고서 등 9종)를 **양식 선택 + 입력**만으로 자동 생성하는 윈도우 데스크톱 앱.
- 입력: 사건명, 당사자(개인/법인·다수), 관할기관, 담당변호사(다중선택), 도장 여부
- 출력: **HWPX**(한글) 기본, 한글 설치 시 **PDF**도. 의뢰인 (인) 자리에 빨강 타원 막도장 자동 날인.
- 핵심 설계: 원본이 HWP라 **HWPX를 직접 채운다**(docx 변환 안 함 → 레이아웃 안 깨짐).

## 2. 디렉터리
```
02. Document/                        ← git 루트 (origin: github.com/nova-law-legal/legal-document)
├── CLAUDE.md                        ← (이 파일)
├── Sample hwp/ , Sample pdf/ , *.docx ← 원본 양식 참조본 (변경 금지, 새 양식 매핑 시 참조)
├── 도장생성기_v2yb.exe               ← 사용자 원본 도장 프로그램(PyInstaller/PIL). .gitignore됨.
│                                       (셀프테스트: `도장생성기_v2yb.exe selftest` → selftest_out/ 에 샘플 PNG)
└── nova-docgen/                     ← ★ 실제 프로그램
    ├── app.py                       ← GUI 진입점 + `selftest` 헤드리스 모드
    ├── config.json                  ← 법인정보·변호사명단·도장 기본값 (사용자 편집 대상)
    ├── forms.json                   ← 양식 9종 슬롯 매핑 (★ 새 양식 추가 시 여기)
    ├── templates/*.hwpx             ← 양식 템플릿 9종 (한글 COM 무손실 변환본)
    ├── assets/*.ttf                 ← 도장 글꼴(충주김생체=타원, 나눔고딕Bold)
    ├── core/
    │   ├── paths.py                 ← 개발/exe(frozen) 공통 경로. config.json은 exe 옆에 영속.
    │   ├── fill_engine.py           ← 입력→슬롯값→hwpxskill 치환 (채우기 핵심)
    │   ├── hwpx_tools.py            ← hwpxskill 스크립트를 runpy로 in-process 실행 (★exe 호환 핵심)
    │   ├── stamp.py                 ← 빨강 타원 막도장 PNG 생성 (make_oval)
    │   ├── hwpx_stamp.py            ← HWPX (인) 위치에 도장 이미지 inline 삽입(BinData+hp:pic)
    │   ├── pdf_export.py            ← HWPX→PDF (한글 COM) + 검수용 PNG 렌더
    │   └── hwpxskill/               ← HWPX 편집/검증 엔진 (github.com/Canine89/hwpxskill, lxml)
    ├── build/ , dist/               ← PyInstaller 산출물 (.gitignore됨)
    ├── nova-docgen.spec             ← 빌드 스펙 (CONSOLE_FLAG를 sed로 True/False 치환해 사용)
    └── README.md                    ← 직원용 사용설명
```

## 3. 데이터 흐름
```
app.py(GUI) → fill_engine.fill_form(form_id, data, out.hwpx)
  data = {case, parties[{type,name,rrn|birth,address,phone,corp_reg,ceo}], court, lawyers[], plaintiff, defendant}
  → build_slot_values(): forms.json 매핑으로 {슬롯키:텍스트} 생성
  → hwpx_tools.run_tool("edit_hwpx.py", ... --slot-json --allow-over-budget)  ← 셀/문단 치환
  → finalize_hwpx.py(줄배치캐시 제거) → validate.py → page_guard.py(완화 플래그)
선택: 도장 ON → stamp.make_oval(name)→PNG → hwpx_stamp.stamp_hwpx(): unpack→BinData+매니페스트+section0 inline pic→pack
선택: PDF → pdf_export.hwpx_to_pdf(한글 COM)
```
슬롯키 형식: `p:N`(문단), `cell:t:r:c`(셀). `hwpx_slots.py <파일>`로 추출. 빈 셀(max=0)도 채워짐.

## 4. 반드시 알아야 할 함정 (검증으로 확인된 것)
1. **Git Bash의 `/c/...` 경로를 Python `open()`에 그대로 넘기면 `C:\c\...`로 깨진다.** 스크립트엔 Windows 절대경로(`C:\...`)를 박을 것. 임시파일은 스크래치패드 절대경로 사용.
2. **한글 COM(HWPFrame.HwpObject)**: `RegisterModule("FilePathCheckDLL","FilePathCheckerModule")`로 보안팝업 우회. SaveAs 포맷명 = `HWPX`/`PDF`/`OOXML`(=docx). 변환 전 멈추면 `Stop-Process Hwp,Hword,HShow,Hcell` 후 재시도. **ESTsoft\CreatorTemp 경로의 파일을 열면 멈출 수 있음** → 다른 폴더로 복사 후 변환.
3. **HWP→DOCX 변환은 행 고정높이(예: 6421 twips)로 2페이지 분할됨** → 그래서 docx 경로 버림. HWPX 직접 채우기 채택.
4. **edit_hwpx 예산초과**: 플레이스홀더보다 실데이터가 길면 막힘 → `--allow-over-budget` 사용. page_guard는 `--no-strict-paragraph-budget --skip-text-drift --allow-empty-fill`.
5. **PyInstaller에서 `subprocess([sys.executable,...])` 금지** (sys.executable=앱 자신). 그래서 hwpxskill을 `hwpx_tools.run_tool`(runpy in-process)로 호출. 새 외부스크립트도 이 방식으로.
6. **frozen 경로**: `paths.py`가 처리. 읽기전용=`sys._MEIPASS`(ROOT), 쓰기=exe 폴더(DATA, config.json). 새 데이터파일 추가 시 `nova-docgen.spec`의 `datas`에도 등록.
7. 출력 인코딩: 콘솔에서 한글 깨지면 `PYTHONIOENCODING=utf-8 PYTHONUTF8=1`.

## 5. 실행 / 빌드 / 검증
```bash
# 개발 실행
cd nova-docgen && python app.py
# 헤드리스 자가검증 (채우기+도장)
python app.py selftest C:\path\out.hwpx       # 종료코드 0 = 정상
# 렌더 검수 (PNG로 눈으로 확인)
python core/pdf_export.py <파일.hwpx>          # → PDF, 그리고 pdf_to_pngs로 PNG
# exe 빌드 (윈도우용, 창모드)
sed 's/CONSOLE_FLAG/False/' nova-docgen.spec > build_windowed.spec
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build/pyi build_windowed.spec
# 디버깅 빌드는 CONSOLE_FLAG를 True로 (콘솔에 traceback 표시)
```
필수 패키지: `pip install pyinstaller pywin32 lxml Pillow`. 검수용: `pymupdf`(앱엔 불필요, spec에서 제외됨).

## 6. 현재 상태 (2026-06-28)
**완료·검증**: 9종 변환, 채우기 엔진, 빨강 타원 도장 생성+삽입, GUI(양식선택/입력/개인·법인·다수/변호사 다중선택/설정), PDF, **exe 빌드 종단 검증(frozen selftest + 렌더)**.
- 완전 검증 5종: 변호인선임(피의자·피고인), 피해자 변호사선임, 고소대리위임장, 원고/피고 소송위임장.

**남은 보완 (실사용 피드백 기준)**:
- 특수 4종(담당변호사 추가지정·지정철회·사임신고서·구속무인용)은 forms.json 매핑은 했으나 실제 출력 1건씩 렌더 검수 필요. 철회/사임은 변호사 표기 방식이 달라 `lawyers_withdraw`/`lawyers_resign` 분기 사용.
- **다중 당사자**: 현재 한 줄 번호매김("1.홍길동 2.㈜가나")이고 도장은 첫 개인 1명. 당사자별 행 분리/개별 날인은 미구현(템플릿에 문단 추가 필요 → section0.xml 조작).
- 도장 크기(`hwpx_stamp.stamp_hwpx(disp_hu=2600)`)·세로 위치, 관할 입력 힌트는 실사용 조정.
- 도장 종류 grid/vertical(회사도장·증제호증)은 stamp.py에 미구현(make_oval만). 원본 상수: make_grid[2,0,26,0.99,0.5], make_vertical[1,2,0.92,0.86,0.5,0.95,0].

## 7. 작업 팁
- 양식 매핑이 헷갈리면: `python core/hwpxskill/scripts/hwpx_slots.py "templates/<양식>.hwpx" -o slots.json` 로 슬롯+미리보기 확인 후 forms.json 수정.
- 변경 후 반드시 `python app.py selftest`로 회귀 확인하고, 핵심 양식은 PNG 렌더로 눈 검수.
- 변호사 명단(이병호/박정윤 등) 최신값은 config.json 또는 메모리 `lawyer-roster` 참조.
```
