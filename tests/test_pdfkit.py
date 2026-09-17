"""
작성자: Git 이력 참조
작성목적: pdfkit.py 의 디자인 설정 로직과 CSS 축 정합성을 검증한다.
작성일: 2026-09-17
주의사항:
  - 표준 라이브러리 unittest 만 사용한다. 실행: python3 -m unittest discover -s tests
  - 렌더링 테스트는 Chrome과 pdfinfo가 있을 때만 실행하고, 없으면 skip 한다.
변경사항 내역:
- 2026-09-17 | 최초 작성 | set 부분 변경, accent, prefs, CSS 축 정합성, 렌더 스모크
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
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pdfkit  # noqa: E402


def run_cli(*argv: str) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = pdfkit.main(list(argv))
    return exit_code, stdout.getvalue(), stderr.getvalue()


class DesignSettingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(tempfile.mkdtemp(prefix="pdfkit-test-"))
        self.doc = self.work_dir / "doc.html"
        exit_code, _, stderr = run_cli("init", "report", str(self.doc), "--style", "bold", "--palette", "forest")
        self.assertEqual(exit_code, 0, stderr)

    def tearDown(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def design(self) -> dict[str, str]:
        return pdfkit.read_design(self.doc.read_text(encoding="utf-8"))

    def test_init_applies_options_and_writes_bundle(self) -> None:
        self.assertEqual(self.design()["style"], "bold")
        self.assertEqual(self.design()["palette"], "forest")
        self.assertTrue((self.work_dir / pdfkit.BUNDLE_NAME).exists())

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
        self.assertEqual(text.count(pdfkit.ACCENT_STYLE_ID), 1, "포인트색 블록은 하나만 있어야 한다")
        self.assertEqual(self.design()["accent"], "#123456")
        self.assertEqual(self.design()["palette"], "forest")
        run_cli("set", str(self.doc), "--accent", "none")
        self.assertNotIn(pdfkit.ACCENT_STYLE_ID, self.doc.read_text(encoding="utf-8"))

    def test_invalid_accent_is_rejected_without_writing(self) -> None:
        original = self.doc.read_text(encoding="utf-8")
        exit_code, _, stderr = run_cli("set", str(self.doc), "--accent", "orange")
        self.assertEqual(exit_code, 1)
        self.assertIn("#RRGGBB", stderr)
        self.assertEqual(self.doc.read_text(encoding="utf-8"), original)

    def test_saved_prefs_become_defaults_for_next_init(self) -> None:
        run_cli("set", str(self.doc), "--radius", "round", "--save")
        prefs = json.loads((self.work_dir / pdfkit.PREFS_NAME).read_text(encoding="utf-8"))
        self.assertEqual(prefs["radius"], "round")

        next_doc = self.work_dir / "deck.html"
        run_cli("init", "deck", str(next_doc), "--palette", "navy")
        next_design = pdfkit.read_design(next_doc.read_text(encoding="utf-8"))
        self.assertEqual(next_design["style"], "bold", "저장된 기본값을 따라야 한다")
        self.assertEqual(next_design["radius"], "round")
        self.assertEqual(next_design["palette"], "navy", "CLI 옵션이 저장된 기본값보다 우선한다")

    def test_init_refuses_to_overwrite(self) -> None:
        exit_code, _, stderr = run_cli("init", "report", str(self.doc))
        self.assertEqual(exit_code, 1)
        self.assertIn("--force", stderr)


class GalleryOptionTest(unittest.TestCase):
    def test_parse_axis_values(self) -> None:
        self.assertEqual(pdfkit.parse_axis_values("style", None, "tech"), ["tech"])
        self.assertEqual(pdfkit.parse_axis_values("style", "all", "tech"), list(pdfkit.DESIGN_AXES["style"]))
        self.assertEqual(pdfkit.parse_axis_values("palette", "keep,navy,navy", "plum"), ["plum", "navy"])
        with self.assertRaises(pdfkit.PdfKitError):
            pdfkit.parse_axis_values("palette", "rainbow", "plum")

    def test_variant_labels_are_unique(self) -> None:
        labels = [pdfkit.variant_label(index) for index in range(pdfkit.GALLERY_MAX_VARIANTS)]
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
        self.bundle = pdfkit.build_css_bundle()

    def test_every_axis_value_has_selector(self) -> None:
        for axis, choices in pdfkit.DESIGN_AXES.items():
            for value in choices:
                if value in self.NEUTRAL_VALUES.get(axis, set()):
                    continue
                self.assertIn(f'data-{axis}="{value}"', self.bundle, f"{axis}={value} 규칙 없음")

    def test_every_style_file_exists(self) -> None:
        for source in pdfkit.css_sources():
            self.assertTrue(source.exists(), source)

    def test_every_palette_defines_all_tokens(self) -> None:
        palettes_css = (pdfkit.CSS_DIR / "palettes.css").read_text(encoding="utf-8")
        for name in pdfkit.DESIGN_AXES["palette"]:
            block = re.search(rf'html\[data-palette="{name}"\]\s*\{{(.*?)\}}', palettes_css, re.DOTALL)
            self.assertIsNotNone(block, name)
            defined = set(re.findall(r"(--[a-z0-9-]+):", block.group(1)))
            self.assertEqual(defined, set(self.PALETTE_TOKENS), f"{name} 팔레트 토큰 불일치")

    def test_import_rules_stay_at_top_of_bundle(self) -> None:
        # @import 는 주석 외 다른 규칙보다 앞에 있어야 브라우저가 무시하지 않는다.
        without_comments = re.sub(r"/\*.*?\*/", "", self.bundle, flags=re.DOTALL).lstrip()
        self.assertTrue(without_comments.startswith("@import"))


@unittest.skipUnless(
    shutil.which("pdfinfo") and any(Path(path).exists() or shutil.which(path) for path in pdfkit.CHROME_CANDIDATES),
    "Chrome 또는 pdfinfo 가 없어 렌더링 테스트를 건너뜀",
)
class RenderSmokeTest(unittest.TestCase):
    def test_templates_render_expected_pages(self) -> None:
        expected_pages = {"onepager": 1, "deck": 3}
        with tempfile.TemporaryDirectory(prefix="pdfkit-render-") as work_dir:
            for template, pages in expected_pages.items():
                doc = Path(work_dir) / f"{template}.html"
                self.assertEqual(run_cli("init", template, str(doc), "--style", "tech")[0], 0)
                exit_code, _, stderr = run_cli("render", str(doc), "--expect-pages", str(pages))
                self.assertEqual(exit_code, 0, stderr)
                self.assertTrue(doc.with_suffix(".pdf").exists())


if __name__ == "__main__":
    unittest.main()
