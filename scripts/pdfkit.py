#!/usr/bin/env python3
"""
작성자: Git 이력 참조
작성목적: pdf-kit 스킬 CLI. 템플릿 복사, 디자인 축(스타일·색조·폰트·밀도·모서리·포인트색) 설정,
         HTML → PDF 렌더링, 여러 디자인 안을 한 번에 비교하는 갤러리 생성을 담당한다.
작성일: 2026-09-17

주요 입력: HTML 문서(<html data-style=... data-palette=...>), 선택적으로 같은 폴더의 pdf-kit.json
주요 출력: pdf-kit.css(번들, 자동 생성), PDF, 페이지별 PNG 미리보기, <문서>_gallery/ 비교표
외부 의존성: Google Chrome/Chromium/Edge(필수), Poppler pdftoppm·pdfinfo(미리보기·갤러리), Python 3.9+ 표준 라이브러리
주의사항:
  - pdf-kit.css 는 assets/css 를 합쳐 만든 생성 파일이다. 직접 고치지 말고 문서의 <style>에서 덮어쓴다.
  - 디자인 축의 값 목록(DESIGN_AXES)은 assets/css 의 선택자와 일치해야 한다(tests 가 검사).
  - macOS Chrome은 PDF를 다 쓴 뒤에도 종료되지 않을 수 있어, 산출물 완성 여부로 완료를 판단한다.

사용법:
  python3 pdfkit.py options
  python3 pdfkit.py init <report|onepager|deck> <dest.html> [--style S] [--palette P] [--font F] [--density D] [--radius R] [--accent #hex]
  python3 pdfkit.py set <doc.html> [위 옵션 중 바꿀 것만] [--save]
  python3 pdfkit.py render <doc.html> [out.pdf] [--preview] [--expect-pages N]
  python3 pdfkit.py gallery <doc.html> [--styles all|a,b] [--palettes all|a,b] [--fonts ...] [--densities ...] [--radii ...] [--pages 2]

변경사항 내역:
- 2026-09-17 | 최초 작성 | init/render, 미리보기, 페이지 수 검증
- 2026-09-17 | 디자인 축 분리 | options/set/gallery 추가, CSS 번들링, pdf-kit.json 기본값
"""

from __future__ import annotations

import argparse
import contextlib
import html
import itertools
import json
import os
import re
import shutil
import signal
import string
import struct
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_ROOT / "templates"
CSS_DIR = SKILL_ROOT / "assets" / "css"
BUNDLE_NAME = "pdf-kit.css"
PREFS_NAME = "pdf-kit.json"

RENDER_TIMEOUT_SEC = 120
POLL_INTERVAL_SEC = 0.5
PREVIEW_DPI = 70
GALLERY_DPI = 60
SHEET_DPI = 110
GALLERY_MAX_VARIANTS = 36
GALLERY_WORKERS = 4
ACCENT_STYLE_ID = "pdfkit-accent"
TEMPLATES = ("report", "onepager", "deck")

# 축 이름 → {값: 설명}. 첫 번째 값이 기본값이며, 순서가 번들·도움말·갤러리 순서가 된다.
DESIGN_AXES = {
    "style": {
        "swiss": "그리드·굵은 룰·산세리프. 보고서·기술 문서 기본값",
        "editorial": "세리프 제목·가운데 정렬 표지·가는 이중 룰. 잡지·에세이",
        "bold": "어두운 표지·큰 숫자·꽉 찬 블록. 발표·경영 보고",
        "minimal": "넓은 여백·테두리 최소·가벼운 굵기. 제안서·포트폴리오",
        "tech": "모노 라벨·점선·도트 그리드 표지. 개발·엔지니어링 문서",
    },
    "palette": {
        "indigo": "중성 회색 + 인디고",
        "navy": "네이비. 공공·기업",
        "terracotta": "종이색 + 테라코타. 따뜻한 톤",
        "forest": "딥 그린. 지속가능성·헬스",
        "plum": "플럼 퍼플. 브랜딩·크리에이티브",
        "mono": "흑백. 흑백 인쇄·이력서",
    },
    "font": {
        "auto": "스타일 기본 조합",
        "sans": "제목·라벨 모두 산세리프",
        "serif": "제목 세리프 + 본문 산세리프",
        "mono": "라벨·수치 모노스페이스",
    },
    "density": {
        "normal": "본문 10pt, 기본 간격",
        "compact": "본문 9.25pt, 좁은 간격. 정보량 많은 문서",
        "airy": "본문 10.5pt, 넓은 간격. 읽기 위주 문서",
    },
    "radius": {
        "auto": "스타일 기본 모서리",
        "sharp": "직각",
        "soft": "6pt",
        "round": "14pt",
    },
}
AXIS_PLURALS = {"styles": "style", "palettes": "palette", "fonts": "font", "densities": "density", "radii": "radius"}
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
HTML_TAG_PATTERN = re.compile(r"<html\b[^>]*>", re.IGNORECASE)
ACCENT_BLOCK_PATTERN = re.compile(rf'\s*<style id="{ACCENT_STYLE_ID}">.*?</style>', re.DOTALL)

CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "msedge",
)


class PdfKitError(Exception):
    """사용자에게 그대로 보여줄 오류. main()에서 종료 코드 1로 변환한다."""


def log(message: str) -> None:
    print(f"[pdf-kit] {message}", flush=True)


# ---------------------------------------------------------------- CSS 번들

def css_sources() -> list[Path]:
    style_files = [CSS_DIR / "styles" / f"{name}.css" for name in DESIGN_AXES["style"]]
    return [CSS_DIR / "core.css", CSS_DIR / "palettes.css", *style_files, CSS_DIR / "options.css"]


def build_css_bundle() -> str:
    parts = ["/* pdf-kit.css — pdf-kit 스킬이 생성한 파일. 직접 수정하지 말고 문서의 <style>에서 덮어쓴다. */\n"]
    for source in css_sources():
        parts.append(f"\n/* ===== {source.relative_to(CSS_DIR).as_posix()} ===== */\n")
        parts.append(source.read_text(encoding="utf-8"))
    return "".join(parts)


def write_bundle(target_dir: Path) -> Path:
    bundle_path = target_dir / BUNDLE_NAME
    bundle_path.write_text(build_css_bundle(), encoding="utf-8")
    return bundle_path


# ---------------------------------------------------------------- 디자인 설정

def read_design(html_text: str) -> dict[str, str]:
    tag_match = HTML_TAG_PATTERN.search(html_text)
    tag = tag_match.group(0) if tag_match else ""
    design = {}
    for axis, choices in DESIGN_AXES.items():
        attr_match = re.search(rf'\bdata-{axis}="([^"]*)"', tag)
        design[axis] = attr_match.group(1) if attr_match else next(iter(choices))
    accent_match = re.search(
        rf'<style id="{ACCENT_STYLE_ID}">[^<]*?--accent:\s*(#[0-9a-fA-F]{{6}})', html_text
    )
    design["accent"] = accent_match.group(1) if accent_match else "none"
    return design


def validate_design(changes: dict[str, str]) -> None:
    for axis, chosen in changes.items():
        if axis == "accent":
            if chosen != "none" and not HEX_COLOR_PATTERN.match(chosen):
                raise PdfKitError(f"--accent 는 #RRGGBB 형식이거나 none 이어야 합니다: {chosen}")
            continue
        if axis not in DESIGN_AXES:
            raise PdfKitError(f"알 수 없는 디자인 축입니다: {axis}")
        if chosen not in DESIGN_AXES[axis]:
            raise PdfKitError(f"{axis} 값 '{chosen}' 은 지원하지 않습니다. 가능: {', '.join(DESIGN_AXES[axis])}")


def accent_block(accent: str) -> str:
    # 팔레트 선택자(html[data-palette])와 명시도가 같고 문서 뒤쪽에 있으므로 팔레트의 accent 를 덮는다.
    return (
        f'\n<style id="{ACCENT_STYLE_ID}">html[data-palette] {{ --accent: {accent}; '
        f"--accent-soft: color-mix(in srgb, {accent} 12%, var(--surface)); "
        f"--accent-on-inverse: color-mix(in srgb, {accent} 55%, #ffffff); }}</style>"
    )


def apply_design(html_text: str, changes: dict[str, str]) -> str:
    validate_design(changes)
    tag_match = HTML_TAG_PATTERN.search(html_text)
    if not tag_match:
        raise PdfKitError("<html> 태그를 찾지 못했습니다.")
    tag = tag_match.group(0)
    for axis in DESIGN_AXES:
        if axis not in changes:
            continue
        attribute = f'data-{axis}="{changes[axis]}"'
        if re.search(rf'\bdata-{axis}="[^"]*"', tag):
            tag = re.sub(rf'\bdata-{axis}="[^"]*"', attribute, tag)
        else:
            tag = tag[:-1].rstrip() + f" {attribute}>"
    html_text = html_text[: tag_match.start()] + tag + html_text[tag_match.end():]

    if "accent" in changes:
        html_text = ACCENT_BLOCK_PATTERN.sub("", html_text)
        if changes["accent"] != "none":
            head_end = html_text.lower().find("</head>")
            if head_end < 0:
                raise PdfKitError("</head> 를 찾지 못해 포인트색을 넣을 수 없습니다.")
            html_text = html_text[:head_end].rstrip() + accent_block(changes["accent"]) + "\n" + html_text[head_end:]
    return html_text


def load_prefs(folder: Path) -> dict[str, str]:
    prefs_path = folder / PREFS_NAME
    if not prefs_path.exists():
        return {}
    try:
        prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PdfKitError(f"{prefs_path} 를 읽을 수 없습니다: {error}") from error
    allowed_keys = set(DESIGN_AXES) | {"accent"}
    return {key: str(value) for key, value in prefs.items() if key in allowed_keys}


def save_prefs(folder: Path, design: dict[str, str]) -> Path:
    prefs_path = folder / PREFS_NAME
    prefs_path.write_text(json.dumps(design, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return prefs_path


def changes_from_args(args: argparse.Namespace) -> dict[str, str]:
    return {key: getattr(args, key) for key in [*DESIGN_AXES, "accent"] if getattr(args, key, None) is not None}


def describe(design: dict[str, str]) -> str:
    return " · ".join(f"{key}={design[key]}" for key in [*DESIGN_AXES, "accent"] if key in design)


# ---------------------------------------------------------------- 렌더링

def find_chrome() -> str:
    env_path = os.environ.get("CHROME_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    for candidate in CHROME_CANDIDATES:
        resolved = candidate if Path(candidate).exists() else shutil.which(candidate)
        if resolved:
            return resolved
    raise PdfKitError("Chrome/Chromium을 찾지 못했습니다. CHROME_PATH 환경변수로 경로를 지정하세요.")


def is_pdf_complete(pdf_path: Path, last_size: int) -> tuple[bool, int]:
    if not pdf_path.exists():
        return False, -1
    size = pdf_path.stat().st_size
    with pdf_path.open("rb") as pdf_file:
        pdf_file.seek(max(0, size - 64))
        has_eof = b"%%EOF" in pdf_file.read()
    return has_eof and size == last_size, size


def run_chrome_until_pdf(command: list[str], pdf_path: Path) -> bool:
    """
    macOS Chrome은 PDF를 다 쓴 뒤에도 업데이터·crashpad 때문에 종료되지 않는 경우가 있다.
    프로세스 종료 대신 PDF가 %%EOF로 끝나고 크기가 안정되면 완료로 보고 프로세스 그룹을 직접 종료한다.
    """
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.monotonic() + RENDER_TIMEOUT_SEC
    last_size = -1
    is_done = False
    try:
        while time.monotonic() < deadline:
            is_done, last_size = is_pdf_complete(pdf_path, last_size)
            if is_done:
                break
            if process.poll() is not None:
                current_size = pdf_path.stat().st_size if pdf_path.exists() else -1
                is_done, _ = is_pdf_complete(pdf_path, current_size)
                break
            time.sleep(POLL_INTERVAL_SEC)
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
    return is_done


def render_pdf(html_path: Path, pdf_path: Path, wait_ms: int) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    with tempfile.TemporaryDirectory(prefix="pdf-kit-") as profile_dir:
        command = [
            find_chrome(),
            "--headless",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile_dir}",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            f"--virtual-time-budget={wait_ms}",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ]
        if sys.platform.startswith("linux"):
            command.insert(1, "--no-sandbox")
        if not run_chrome_until_pdf(command, pdf_path):
            raise PdfKitError(f"렌더링 실패: {RENDER_TIMEOUT_SEC}초 안에 PDF가 완성되지 않았습니다 ({html_path}).")


def count_pages(pdf_path: Path) -> int | None:
    if shutil.which("pdfinfo"):
        info = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True)
        match = re.search(r"^Pages:\s+(\d+)", info.stdout, re.MULTILINE)
        if match:
            return int(match.group(1))
    # pdfinfo가 없을 때의 근사치. 압축된 객체 스트림이면 틀릴 수 있다.
    approx = len(re.findall(rb"/Type\s*/Page(?!s)", pdf_path.read_bytes()))
    return approx or None


def make_preview(pdf_path: Path, preview_dir: Path, dpi: int, last_page: int | None = None) -> list[Path]:
    if not shutil.which("pdftoppm"):
        log("pdftoppm 없음 → 미리보기 생략 (macOS: brew install poppler)")
        return []
    if preview_dir.exists():
        shutil.rmtree(preview_dir)
    preview_dir.mkdir(parents=True)
    command = ["pdftoppm", "-png", "-r", str(dpi)]
    if last_page:
        command += ["-f", "1", "-l", str(last_page)]
    subprocess.run([*command, str(pdf_path), str(preview_dir / "page")], check=True)
    return sorted(preview_dir.glob("page-*.png"), key=lambda path: int(path.stem.rsplit("-", 1)[-1]))


def png_size(png_path: Path) -> tuple[int, int]:
    with png_path.open("rb") as png_file:
        header = png_file.read(24)
    return struct.unpack(">II", header[16:24])


def require_file(raw_path: str) -> Path:
    path = Path(raw_path).resolve()
    if not path.exists():
        raise PdfKitError(f"파일이 없습니다: {path}")
    return path


# ---------------------------------------------------------------- 명령

def cmd_options(_: argparse.Namespace) -> None:
    for axis, choices in DESIGN_AXES.items():
        print(f"\n--{axis}  (기본값: {next(iter(choices))})")
        for name, summary in choices.items():
            print(f"  {name:<11} {summary}")
    print("\n--accent  #RRGGBB: 팔레트는 유지하고 포인트색만 교체 / none: 해제")
    print(f"\n템플릿: {', '.join(TEMPLATES)}")


def cmd_init(args: argparse.Namespace) -> None:
    dest_path = Path(args.dest).resolve()
    if dest_path.exists() and not args.force:
        raise PdfKitError(f"이미 존재합니다: {dest_path} (덮어쓰려면 --force)")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # 우선순위: CLI 옵션 > 폴더의 pdf-kit.json > 템플릿 기본값
    design = {**load_prefs(dest_path.parent), **changes_from_args(args)}
    html_text = (TEMPLATE_DIR / f"{args.template}.html").read_text(encoding="utf-8")
    html_text = apply_design(html_text, design)
    dest_path.write_text(html_text, encoding="utf-8")
    write_bundle(dest_path.parent)
    log(f"생성: {dest_path}")
    log(f"디자인: {describe(read_design(html_text))}")


def cmd_set(args: argparse.Namespace) -> None:
    html_path = require_file(args.input)
    changes = changes_from_args(args)
    html_text = html_path.read_text(encoding="utf-8")
    before = read_design(html_text)
    if changes:
        html_text = apply_design(html_text, changes)
        html_path.write_text(html_text, encoding="utf-8")
    write_bundle(html_path.parent)
    after = read_design(html_text)
    changed = [f"{key} {before[key]}→{after[key]}" for key in after if before[key] != after[key]]
    log(f"디자인: {describe(after)}")
    log(f"변경: {', '.join(changed) or '없음'}")
    if args.save:
        log(f"기본값 저장: {save_prefs(html_path.parent, after)}")


def cmd_render(args: argparse.Namespace) -> None:
    html_path = require_file(args.input)
    pdf_path = Path(args.output).resolve() if args.output else html_path.with_suffix(".pdf")
    # 스킬 CSS가 갱신됐을 수 있으므로 렌더링마다 번들을 새로 쓴다(문서별 수정은 <style>에 있으므로 안전).
    write_bundle(html_path.parent)
    render_pdf(html_path, pdf_path, args.wait_ms)

    pages = count_pages(pdf_path)
    log(f"PDF: {pdf_path} ({pages}쪽, {pdf_path.stat().st_size // 1024}KB)")
    log(f"디자인: {describe(read_design(html_path.read_text(encoding='utf-8')))}")
    if args.preview:
        previews = make_preview(pdf_path, pdf_path.with_name(pdf_path.stem + "_preview"), PREVIEW_DPI)
        if previews:
            log(f"미리보기: {previews[0].parent} ({len(previews)}장)")
    if args.expect_pages is not None and pages != args.expect_pages:
        raise PdfKitError(f"페이지 수 불일치: 기대 {args.expect_pages}쪽, 실제 {pages}쪽 → 넘친 내용이나 빈 페이지를 확인하세요.")


def parse_axis_values(axis: str, raw_value: str | None, current: str) -> list[str]:
    if raw_value in (None, "", "keep"):
        return [current]
    if raw_value == "all":
        return list(DESIGN_AXES[axis])
    values = []
    for value in (item.strip() for item in raw_value.split(",")):
        if not value:
            continue
        resolved = current if value == "keep" else value
        validate_design({axis: resolved})
        if resolved not in values:
            values.append(resolved)
    return values


def variant_label(index: int) -> str:
    letters = string.ascii_uppercase
    if index < len(letters):
        return letters[index]
    return letters[index // len(letters) - 1] + letters[index % len(letters)]


def build_gallery_sheet(source_name: str, current: dict[str, str], variants: list[dict]) -> str:
    first_thumbs = next((variant["thumbs"] for variant in variants if variant["thumbs"]), [])
    is_landscape = bool(first_thumbs) and png_size(first_thumbs[0])[0] > png_size(first_thumbs[0])[1]
    columns = 2 if is_landscape else 3
    cards = []
    for variant in variants:
        diff = [f"{axis}={variant['design'][axis]}" for axis in DESIGN_AXES if variant["design"][axis] != current[axis]]
        chips = "".join(f"<span>{html.escape(item)}</span>" for item in diff) or "<span>현재 설정</span>"
        thumbs = "".join(
            f'<img src="{html.escape(path.relative_to(variant["dir"].parent).as_posix())}">' for path in variant["thumbs"]
        )
        cards.append(f'<figure><div class="thumbs">{thumbs}</div><figcaption><b>{variant["label"]}</b>{chips}</figcaption></figure>')
    current_summary = ", ".join(f"{axis}={current[axis]}" for axis in DESIGN_AXES)
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>pdf-kit gallery</title>
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
@page {{ size: A4 landscape; margin: 12mm; }}
html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ margin: 0; font-family: "Pretendard", -apple-system, sans-serif; color: #16181d; }}
header {{ display: flex; justify-content: space-between; align-items: baseline; gap: 8mm; margin-bottom: 6mm; }}
h1 {{ font-size: 16pt; margin: 0; letter-spacing: -0.02em; white-space: nowrap; }}
header p {{ margin: 0; font-size: 8pt; color: #6b7280; text-align: right; }}
main {{ display: grid; grid-template-columns: repeat({columns}, 1fr); gap: 7mm 6mm; }}
figure {{ margin: 0; break-inside: avoid; }}
.thumbs {{ display: flex; gap: 2mm; background: #eef0f3; padding: 2mm; border-radius: 3pt; }}
.thumbs img {{ flex: 1; min-width: 0; width: 100%; box-shadow: 0 0 0 0.5pt #d5d8de; }}
figcaption {{ display: flex; flex-wrap: wrap; align-items: center; gap: 3pt; margin-top: 2mm; font-size: 8pt; }}
figcaption b {{ font-size: 13pt; margin-right: 4pt; }}
figcaption span {{ background: #f1f2f4; border-radius: 99px; padding: 1.5pt 6pt; color: #3d434f; }}
</style></head><body>
<header><h1>디자인 후보 · {html.escape(source_name)}</h1><p>현재: {html.escape(current_summary)}<br>칩은 현재와 달라지는 값만 표시</p></header>
<main>{''.join(cards)}</main>
</body></html>"""


def cmd_gallery(args: argparse.Namespace) -> None:
    html_path = require_file(args.input)
    source_text = html_path.read_text(encoding="utf-8")
    current = read_design(source_text)

    axis_values = {axis: parse_axis_values(axis, getattr(args, plural), current[axis]) for plural, axis in AXIS_PLURALS.items()}
    combos = list(itertools.product(*(axis_values[axis] for axis in DESIGN_AXES)))
    if len(combos) == 1:
        raise PdfKitError("비교할 후보가 1개뿐입니다. --styles all 처럼 바꿔 볼 축을 지정하세요.")
    if len(combos) > GALLERY_MAX_VARIANTS:
        raise PdfKitError(f"후보가 {len(combos)}개로 너무 많습니다(최대 {GALLERY_MAX_VARIANTS}). 축 값을 줄이세요.")

    out_dir = Path(args.out).resolve() if args.out else html_path.parent / f"{html_path.stem}_gallery"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    write_bundle(html_path.parent)

    # 후보 HTML은 out_dir에 두고 <base>로 원본 폴더를 가리켜 CSS·이미지 상대경로를 그대로 쓴다.
    base_tag = f'<base href="{html_path.parent.as_uri()}/">'
    variants = []
    for index, combo in enumerate(combos):
        design = dict(zip(DESIGN_AXES, combo))
        label = variant_label(index)
        variant_dir = out_dir / label
        variant_dir.mkdir()
        variant_text = apply_design(source_text, design)
        variant_text = re.sub(r"<head([^>]*)>", lambda match: f"<head{match.group(1)}>\n{base_tag}", variant_text, count=1)
        variant_html = variant_dir / "doc.html"
        variant_html.write_text(variant_text, encoding="utf-8")
        variants.append({"label": label, "design": design, "dir": variant_dir, "html": variant_html, "thumbs": []})

    def render_variant(variant: dict) -> None:
        pdf_path = variant["dir"] / "doc.pdf"
        render_pdf(variant["html"], pdf_path, args.wait_ms)
        variant["thumbs"] = make_preview(pdf_path, variant["dir"] / "thumbs", GALLERY_DPI, args.pages)

    log(f"후보 {len(variants)}개 렌더링 중…")
    with ThreadPoolExecutor(max_workers=GALLERY_WORKERS) as executor:
        list(executor.map(render_variant, variants))

    sheet_path = out_dir / "gallery.html"
    sheet_path.write_text(build_gallery_sheet(html_path.name, current, variants), encoding="utf-8")
    sheet_pdf = out_dir / "gallery.pdf"
    render_pdf(sheet_path, sheet_pdf, args.wait_ms)
    sheet_pngs = make_preview(sheet_pdf, out_dir / "sheet", SHEET_DPI)

    log(f"비교표 PDF: {sheet_pdf}")
    for png_path in sheet_pngs:
        log(f"비교표 이미지: {png_path}")
    print("\n후보 → 적용 명령 (현재 문서에서 달라지는 축만 바뀌고 나머지는 유지됩니다)")
    for variant in variants:
        flags = " ".join(f"--{axis} {variant['design'][axis]}" for axis in DESIGN_AXES if variant["design"][axis] != current[axis])
        print(f"  {variant['label']:>2}  set {html_path.name} {flags or '(현재 설정 그대로)'}")


# ---------------------------------------------------------------- CLI

def add_design_arguments(parser: argparse.ArgumentParser) -> None:
    for axis, choices in DESIGN_AXES.items():
        parser.add_argument(f"--{axis}", choices=list(choices))
    parser.add_argument("--accent", help="#RRGGBB 또는 none")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pdfkit", description="pdf-kit: 디자인을 골라 쓰는 HTML/CSS → PDF")
    sub = parser.add_subparsers(dest="command", required=True)

    options_parser = sub.add_parser("options", help="선택 가능한 디자인 축과 값 목록")
    options_parser.set_defaults(func=cmd_options)

    init_parser = sub.add_parser("init", help="템플릿을 작업 폴더로 복사")
    init_parser.add_argument("template", choices=TEMPLATES)
    init_parser.add_argument("dest")
    add_design_arguments(init_parser)
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(func=cmd_init)

    set_parser = sub.add_parser("set", help="지정한 디자인 축만 변경하고 나머지는 유지")
    set_parser.add_argument("input")
    add_design_arguments(set_parser)
    set_parser.add_argument("--save", action="store_true", help=f"결과를 같은 폴더의 {PREFS_NAME}에 기본값으로 저장")
    set_parser.set_defaults(func=cmd_set)

    render_parser = sub.add_parser("render", help="HTML을 PDF로 렌더링")
    render_parser.add_argument("input")
    render_parser.add_argument("output", nargs="?")
    render_parser.add_argument("--preview", action="store_true", help="페이지별 PNG 생성")
    render_parser.add_argument("--expect-pages", type=int, help="페이지 수가 다르면 실패 처리")
    render_parser.add_argument("--wait-ms", type=int, default=8000, help="폰트·이미지 로딩 대기")
    render_parser.set_defaults(func=cmd_render)

    gallery_parser = sub.add_parser("gallery", help="같은 문서를 여러 디자인 안으로 렌더링해 비교표 생성")
    gallery_parser.add_argument("input")
    for plural in AXIS_PLURALS:
        gallery_parser.add_argument(f"--{plural}", help="all | keep | 쉼표 구분 값 (기본: keep)")
    gallery_parser.add_argument("--pages", type=int, default=2, help="후보마다 보여줄 앞쪽 페이지 수")
    gallery_parser.add_argument("--out", help="출력 폴더 (기본: <문서명>_gallery)")
    gallery_parser.add_argument("--wait-ms", type=int, default=8000)
    gallery_parser.set_defaults(func=cmd_gallery)
    return parser


def main(argv: list[str] | None = None) -> int:
    parsed = build_parser().parse_args(argv)
    try:
        parsed.func(parsed)
    except PdfKitError as error:
        print(f"[pdf-kit] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
