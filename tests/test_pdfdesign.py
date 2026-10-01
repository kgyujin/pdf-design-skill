"""
작성자: Git 이력 참조
작성목적: pdfdesign.py 의 디자인 설정 로직과 CSS 축 정합성을 검증한다.
작성일: 2026-09-17
주의사항:
  - 표준 라이브러리 unittest 만 사용한다. 실행: python3 -m unittest discover -s tests
  - 렌더링 테스트는 Chrome과 pdfinfo가 있을 때만 실행하고, 없으면 skip 한다.
변경사항 내역:
- 2026-09-17 | 최초 작성 | set 부분 변경, accent, prefs, CSS 축 정합성, 렌더 스모크
- 2026-09-17 | 바탕체 규칙 | 바탕체는 font 옵션에서만, 폰트는 고운바탕
- 2026-09-17 | AI 티 검사 | audit_design 탐지·오탐 방지, 기본 CSS·템플릿에 AI 패턴이 없는지 검사
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import deck_tools  # noqa: E402
import pdfdesign  # noqa: E402

HAS_RENDERER = bool(shutil.which("pdfinfo") and shutil.which("pdftoppm")) and any(
    Path(path).exists() or shutil.which(path) for path in pdfdesign.CHROME_CANDIDATES
)


def run_cli(*argv: str) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = pdfdesign.main(list(argv))
    return exit_code, stdout.getvalue(), stderr.getvalue()


class DesignSettingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(tempfile.mkdtemp(prefix="pdf-design-test-"))
        self.doc = self.work_dir / "doc.html"
        exit_code, _, stderr = run_cli("init", "report", str(self.doc), "--style", "bold", "--palette", "forest")
        self.assertEqual(exit_code, 0, stderr)

    def tearDown(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def design(self) -> dict[str, str]:
        return pdfdesign.read_design(self.doc.read_text(encoding="utf-8"))

    def test_init_applies_options_and_writes_bundle(self) -> None:
        self.assertEqual(self.design()["style"], "bold")
        self.assertEqual(self.design()["palette"], "forest")
        self.assertTrue((self.work_dir / pdfdesign.BUNDLE_NAME).exists())

    def test_set_changes_only_requested_axis(self) -> None:
        run_cli("set", str(self.doc), "--style", "editorial")
        design = self.design()
        self.assertEqual(design["style"], "editorial")
        self.assertEqual(design["palette"], "forest", "색조는 유지돼야 한다")
        self.assertEqual(design["density"], "normal")

    def test_set_keeps_document_content(self) -> None:
        before_body = self.doc.read_text(encoding="utf-8").split("</head>", 1)[1]
        run_cli("set", str(self.doc), "--palette", "plum", "--density", "compact")
        after_body = self.doc.read_text(encoding="utf-8").split("</head>", 1)[1]
        self.assertEqual(before_body, after_body)

    def test_accent_is_added_replaced_and_removed(self) -> None:
        run_cli("set", str(self.doc), "--accent", "#FF6600")
        self.assertEqual(self.design()["accent"], "#FF6600")
        run_cli("set", str(self.doc), "--accent", "#123456")
        text = self.doc.read_text(encoding="utf-8")
        self.assertEqual(text.count(pdfdesign.ACCENT_STYLE_ID), 1, "포인트색 블록은 하나만 있어야 한다")
        self.assertEqual(self.design()["accent"], "#123456")
        self.assertEqual(self.design()["palette"], "forest")
        run_cli("set", str(self.doc), "--accent", "none")
        self.assertNotIn(pdfdesign.ACCENT_STYLE_ID, self.doc.read_text(encoding="utf-8"))

    def test_invalid_accent_is_rejected_without_writing(self) -> None:
        original = self.doc.read_text(encoding="utf-8")
        exit_code, _, stderr = run_cli("set", str(self.doc), "--accent", "orange")
        self.assertEqual(exit_code, 1)
        self.assertIn("#RRGGBB", stderr)
        self.assertEqual(self.doc.read_text(encoding="utf-8"), original)

    def test_saved_prefs_become_defaults_for_next_init(self) -> None:
        run_cli("set", str(self.doc), "--radius", "round", "--save")
        prefs = json.loads((self.work_dir / pdfdesign.PREFS_NAME).read_text(encoding="utf-8"))
        self.assertEqual(prefs["radius"], "round")

        next_doc = self.work_dir / "deck.html"
        run_cli("init", "deck", str(next_doc), "--palette", "navy")
        next_design = pdfdesign.read_design(next_doc.read_text(encoding="utf-8"))
        self.assertEqual(next_design["style"], "bold", "저장된 기본값을 따라야 한다")
        self.assertEqual(next_design["radius"], "round")
        self.assertEqual(next_design["palette"], "navy", "CLI 옵션이 저장된 기본값보다 우선한다")

    def test_init_refuses_to_overwrite(self) -> None:
        exit_code, _, stderr = run_cli("init", "report", str(self.doc))
        self.assertEqual(exit_code, 1)
        self.assertIn("--force", stderr)


class GalleryOptionTest(unittest.TestCase):
    def test_parse_axis_values(self) -> None:
        self.assertEqual(pdfdesign.parse_axis_values("style", None, "tech"), ["tech"])
        self.assertEqual(pdfdesign.parse_axis_values("style", "all", "tech"), list(pdfdesign.DESIGN_AXES["style"]))
        self.assertEqual(pdfdesign.parse_axis_values("palette", "keep,navy,navy", "plum"), ["plum", "navy"])
        with self.assertRaises(pdfdesign.PdfDesignError):
            pdfdesign.parse_axis_values("palette", "rainbow", "plum")

    def test_variant_labels_are_unique(self) -> None:
        labels = [pdfdesign.variant_label(index) for index in range(pdfdesign.GALLERY_MAX_VARIANTS)]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(labels[26], "AA")


class CssAxisConsistencyTest(unittest.TestCase):
    """DESIGN_AXES 에 있는 값마다 CSS 규칙이 있어야 선택해도 모양이 바뀐다."""

    PALETTE_TOKENS = (
        "--ink", "--ink-2", "--muted", "--line", "--surface", "--surface-2", "--accent", "--accent-soft",
        "--on-accent", "--inverse", "--on-inverse", "--on-inverse-muted", "--accent-on-inverse",
    )
    NEUTRAL_VALUES = {"font": {"auto"}, "density": {"normal"}, "radius": {"auto"}}

    def setUp(self) -> None:
        self.bundle = pdfdesign.build_css_bundle()

    def test_every_axis_value_has_selector(self) -> None:
        for axis, choices in pdfdesign.DESIGN_AXES.items():
            for value in choices:
                if value in self.NEUTRAL_VALUES.get(axis, set()):
                    continue
                self.assertIn(f'data-{axis}="{value}"', self.bundle, f"{axis}={value} 규칙 없음")

    def test_every_style_file_exists(self) -> None:
        for source in pdfdesign.css_sources():
            self.assertTrue(source.exists(), source)

    def test_every_palette_defines_all_tokens(self) -> None:
        palettes_css = (pdfdesign.CSS_DIR / "palettes.css").read_text(encoding="utf-8")
        for name in pdfdesign.DESIGN_AXES["palette"]:
            block = re.search(rf'html\[data-palette="{name}"\]\s*\{{(.*?)\}}', palettes_css, re.DOTALL)
            self.assertIsNotNone(block, name)
            defined = set(re.findall(r"(--[a-z0-9-]+):", block.group(1)))
            self.assertEqual(defined, set(self.PALETTE_TOKENS) | {"--secondary"}, f"{name} 팔레트 토큰 불일치")

    def test_serif_is_opt_in_and_uses_gowun_batang(self) -> None:
        # 바탕(명조)체는 사용자가 요청할 때만 font 옵션으로 켠다. 스타일·템플릿·예제가 직접 쓰면 안 된다.
        self.assertIn('--font-serif: "Gowun Batang"', self.bundle)
        self.assertIn("family=Gowun+Batang", self.bundle)
        self.assertNotIn("Noto Serif", self.bundle)
        # 기본 폰트는 Pretendard. 스타일 파일은 세리프·모노 폰트를 직접 지정하지 않는다(옵션 축이 담당).
        allowed = {pdfdesign.CSS_DIR / "core.css", pdfdesign.CSS_DIR / "options.css"}
        for source in pdfdesign.css_sources():
            if source not in allowed:
                style_css = source.read_text(encoding="utf-8")
                self.assertNotIn("--font-serif", style_css, source.name)
                self.assertNotIn("--font-mono", style_css, source.name)
        self.assertIn('--font-sans: "Pretendard"', self.bundle)
        for html_path in [*pdfdesign.TEMPLATE_DIR.glob("*.html"), *(REPO_ROOT / "examples").glob("*.html")]:
            text = html_path.read_text(encoding="utf-8")
            self.assertNotIn("--font-serif", text, html_path.name)
            self.assertNotRegex(text, r'data-font="serif', html_path.name)
        options_css = (pdfdesign.CSS_DIR / "options.css").read_text(encoding="utf-8")
        for value in ("serif", "serif-all"):
            rule = re.search(rf'html\[data-font="{value}"\] \{{([^}}]*)\}}', options_css).group(1)
            self.assertIn("--head-weight: 700", rule, "고운바탕은 700까지만 있어 제목 굵기를 고정해야 한다")

    def test_import_rules_stay_at_top_of_bundle(self) -> None:
        # @import 는 주석 외 다른 규칙보다 앞에 있어야 브라우저가 무시하지 않는다.
        without_comments = re.sub(r"/\*.*?\*/", "", self.bundle, flags=re.DOTALL).lstrip()
        self.assertTrue(without_comments.startswith("@import"))


SAMPLE_DECK = """
<html><head><title>Deck</title></head><body class="deck">
<section class="slide hero">
  <div class="slide-title">Opening</div>
  <footer class="slide-foot"><span class="source"></span><span class="page"></span></footer>
</section>
<section class="slide">
  <header class="slide-head"><div class="eyebrow">Result</div><div class="slide-title">Latency <br>dropped 42%</div>
  <p class="slide-msg">Key message here.</p></header>
  <div class="slide-body l-points"><ol class="points"><li><strong>A</strong> text</li></ol></div>
  <footer class="slide-foot"><span class="source">Source: Report, Fig. 1</span><span class="page"></span></footer>
</section>
<section class="slide">
  <header class="slide-head"><div class="slide-title">No notes here</div></header>
  <footer class="slide-foot"><span class="source"></span><span class="page"></span></footer>
</section>
</body></html>
"""


class DeckToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.slides = deck_tools.parse_slides(SAMPLE_DECK)

    def test_parses_slide_fields(self) -> None:
        self.assertEqual(len(self.slides), 3)
        second = self.slides[1]
        self.assertEqual(second.title, "Latency dropped 42%")
        self.assertEqual(second.message, "Key message here.")
        self.assertEqual(second.source, "Source: Report, Fig. 1")
        self.assertEqual(self.slides[0].kinds, ["hero"])


    def test_sources_are_optional_and_titles_remain_required(self) -> None:
        self.assertEqual(deck_tools.audit_slides(self.slides), [])
        issues = deck_tools.audit_slides(deck_tools.parse_slides('<section class="slide"></section>'))
        self.assertEqual(len(issues), 1)
        self.assertIn("제목", issues[0]["message"])

    def test_removed_command_is_unavailable(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            pdfdesign.build_parser().parse_args(["script", "deck.html"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice", stderr.getvalue())

    def test_check_script_injected_before_body_end(self) -> None:
        injected = deck_tools.inject_check_script(SAMPLE_DECK)
        self.assertLess(injected.index("pdf-design-check-runner"), injected.rindex("</body>"))
        fake_dom = '<html><body><script type="application/json" id="pdf-design-check-result">{"issues": [], "slides": 3}</script></body></html>'
        self.assertEqual(deck_tools.extract_check_result(fake_dom), {"issues": [], "slides": 3})


AI_TELL_DOC = """<html><head><style>
  .hero { background: linear-gradient(90deg, #6366f1, #a855f7); box-shadow: 0 4px 20px rgba(0,0,0,.2); }
  .label { text-transform: uppercase; letter-spacing: 0.2em; }
  .card { border-left: 4px solid var(--accent); border-radius: 999px; }
</style></head><body>
<h1>🚀 Launch plan</h1>
<p>We move fast — and we ship often.</p>
<p>Quality matters — every single time.</p>
<h2><span class="sec-num">01</span>Intro</h2>
<div class="eyebrow">A</div><div class="eyebrow">B</div><div class="eyebrow">C</div>
<div class="grid-3"><div class="card">1</div><div class="card">2</div><div class="card">3</div></div>
</body></html>"""


class AiTellAuditTest(unittest.TestCase):
    def test_detects_common_patterns(self) -> None:
        messages = " / ".join(issue["message"] for issue in deck_tools.audit_design(AI_TELL_DOC))
        for expected in ("그라데이션", "그림자", "대문자 라벨", "넓은 자간", "왼쪽 굵은 세로 바", "알약", "HEX", "이모지", "줄표", "0을 붙인 번호", "라벨이 3개", "카드 3개"):
            self.assertIn(expected, messages)
        self.assertTrue(all(issue["message"].startswith(deck_tools.AI_TELL_PREFIX) for issue in deck_tools.audit_design(AI_TELL_DOC)))

    def test_style_preferences_are_advisory_but_hex_stays_warning(self):
        issues = deck_tools.audit_design(AI_TELL_DOC)
        self.assertTrue(any(issue['level'] == 'info' and '카드 3개' in issue['message'] for issue in issues))
        self.assertTrue(any(issue['level'] == 'warn' and 'HEX' in issue['message'] for issue in issues))
        self.assertFalse(any(issue['level'] == 'warn' and 'HEX' not in issue['message'] for issue in issues))

    def test_ignores_functional_markup(self) -> None:
        clean = """<html><head><style>@page { size: A4; } #face { color: var(--ink); }</style>
        <style id="pdf-design-accent">html[data-palette] { --accent: #123456; }</style></head><body>
        <span class="pin" style="left: 40%; top: 12%">1</span><div class="bar"><span style="width:72%"></span></div>
        <table><tr><td>—</td><td>▲ 42%</td></tr></table><p>A → B</p></body></html>"""
        self.assertEqual(deck_tools.audit_design(clean), [])

    def test_shipped_templates_and_examples_are_clean(self) -> None:
        for html_path in [*pdfdesign.TEMPLATE_DIR.glob("*.html"), *(REPO_ROOT / "examples").glob("*.html")]:
            self.assertEqual(deck_tools.audit_design(html_path.read_text(encoding="utf-8")), [], html_path.name)

    def test_bundle_avoids_decorative_patterns(self) -> None:
        bundle = re.sub(r"/\*.*?\*/", "", pdfdesign.build_css_bundle(), flags=re.DOTALL)
        for pattern in ("decimal-leading-zero", "999px", "radial-gradient", "text-transform: uppercase", "box-shadow: 0 "):
            self.assertNotIn(pattern, bundle)
        self.assertIsNone(re.search(r"border-left:\s*[2-9](?:\.\d+)?pt solid var\(--accent\)", bundle))
        # 원형은 Figure 위치 핀(.pin, .callouts 번호)에만 허용한다.
        circle_rules = [rule for rule in re.findall(r"([^{}]+)\{[^}]*border-radius:\s*50%", bundle)]
        self.assertTrue(all(".pin" in rule or ".callouts" in rule for rule in circle_rules), circle_rules)
        self.assertIn(':root,\nhtml[data-palette="graphite"]', bundle, "기본 색조는 graphite")


BROKEN_DECK = """<!doctype html>
<html lang="en" data-style="academic" data-palette="graphite"><head><meta charset="utf-8"><title>Broken</title>
<link rel="stylesheet" href="pdf-design.css"><style>@page { size: 338.67mm 190.5mm; margin: 0; }</style></head>
<body class="deck">
<section class="slide">
  <header class="slide-head"><div class="slide-title">Overflowing body</div></header>
  <div class="slide-body l-points"><ol class="points">
    <li><strong>1</strong>x</li><li><strong>2</strong>x</li><li><strong>3</strong>x</li><li><strong>4</strong>x</li>
    <li><strong>5</strong>x</li><li><strong>6</strong>x</li><li><strong>7</strong>x</li><li><strong>8</strong>x</li>
  </ol></div>
  <footer class="slide-foot"><span class="source">Source</span><span class="page"></span></footer>
</section>
<section class="slide">
  <header class="slide-head"><div class="slide-title">Tiny text and missing image</div></header>
  <div class="slide-body"><p style="font-size: 8pt">too small</p><img src="missing.png" style="width: 40mm; height: 20mm"></div>
  <footer class="slide-foot"><span class="source"></span><span class="page"></span></footer>
</section>
</body></html>
"""


@unittest.skipUnless(HAS_RENDERER, "Chrome 또는 Poppler 가 없어 렌더링 테스트를 건너뜀")
class RenderSmokeTest(unittest.TestCase):
    def test_templates_render_expected_pages(self) -> None:
        expected_pages = {"onepager": 1, "deck": 3, "talk": 9}
        with tempfile.TemporaryDirectory(prefix="pdf-design-render-") as work_dir:
            for template, pages in expected_pages.items():
                doc = Path(work_dir) / f"{template}.html"
                self.assertEqual(run_cli("init", template, str(doc), "--style", "tech")[0], 0)
                exit_code, _, stderr = run_cli("render", str(doc), "--expect-pages", str(pages))
                self.assertEqual(exit_code, 0, stderr)
                self.assertTrue(doc.with_suffix(".pdf").exists())

    def test_check_passes_templates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdf-design-check-") as work_dir:
            for template in ("talk", "deck", "onepager"):
                doc = Path(work_dir) / f"{template}.html"
                run_cli("init", template, str(doc))
                exit_code, stdout, stderr = run_cli("check", str(doc))
                self.assertEqual(exit_code, 0, stdout + stderr)
                self.assertIn("오류 0건", stdout)
                self.assertNotIn(deck_tools.AI_TELL_PREFIX, stdout)

    def test_check_detects_defects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdf-design-check-") as work_dir:
            doc = Path(work_dir) / "broken.html"
            doc.write_text(BROKEN_DECK, encoding="utf-8")
            exit_code, stdout, _ = run_cli("check", str(doc))
            self.assertEqual(exit_code, 1)
            self.assertIn("[slide 1] 본문이 영역을 넘침", stdout)
            self.assertIn("핵심 포인트가 8개", stdout)
            self.assertIn("[slide 2] 글자가 너무 작음(8.0pt", stdout)
            self.assertIn("이미지를 불러오지 못함: missing.png", stdout)
            self.assertFalse((Path(work_dir) / ".broken.check.html").exists(), "검사용 사본은 지워져야 한다")


class StrictCheckTest(unittest.TestCase):
    @unittest.skipUnless(HAS_RENDERER, "Chrome 또는 Poppler가 없어 렌더링 검사를 건너뜀")
    def test_empty_document_has_no_detectable_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "empty.html"
            source.write_text("<html><p>페이지 없음</p></html>")
            code, stdout, stderr = run_cli("check", str(source))
            self.assertEqual(code, 1, stdout + stderr)
            self.assertIn("검사할 고정 크기 페이지가 없습니다", stdout)


    def test_information_does_not_fail_strict(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "deck.html"
            source.write_text('<html></html>')
            args = argparse.Namespace(input=str(source), strict=True, wait_ms=100)
            with patch.object(pdfdesign, 'run_layout_check', return_value=[{'level':'info','where':'slide 1','message':'manual review'}]):
                pdfdesign.cmd_check(args)
            with patch.object(pdfdesign, 'run_layout_check', return_value=[{'level':'warn','where':'slide 1','message':'small SVG text'}]):
                with self.assertRaises(pdfdesign.PdfDesignError):
                    pdfdesign.cmd_check(args)


if __name__ == "__main__":
    unittest.main()
