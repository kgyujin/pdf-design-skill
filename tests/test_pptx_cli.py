"""PPTX CLI and renderer boundary tests; native package tests live separately."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pdfdesign
import pptx_render

class PptxCliTests(unittest.TestCase):
    def test_cli_writes_editable_file_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "deck.json"
            dest = source.with_suffix(".pptx")
            source.write_text(json.dumps({"slides":[{"elements":[{"type":"text","x":1,"y":1,"w":100,"h":50,"text":"안녕하세요"}]}]}))
            self.assertEqual(pdfdesign.main(["pptx",str(source)]),0)
            original = dest.read_bytes()
            self.assertEqual(pdfdesign.main(["pptx",str(source)]),1)
            self.assertEqual(original,dest.read_bytes())

    def test_pdf_existing_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "deck.pptx"; source.write_bytes(b"test")
            dest = source.with_suffix(".pdf"); dest.write_bytes(b"existing")
            app = Path(folder) / "Keynote.app"; app.mkdir()
            with patch.object(pptx_render.sys,"platform","darwin"), patch.object(pptx_render.subprocess,"run") as run:
                with self.assertRaisesRegex(ValueError,"덮어쓰지"):
                    pptx_render.render_pptx(source,dest,app)
                run.assert_not_called()
            self.assertEqual(dest.read_bytes(),b"existing")

    def test_paths_are_argv_and_open_user_document_is_guarded(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'quote" deck.pptx'; source.write_bytes(b"test")
            dest = source.with_suffix(".pdf")
            app = Path(folder) / "Keynote.app"; app.mkdir()
            def export(argv, **kwargs):
                script = Path(argv[1]).read_text()
                self.assertNotIn(str(source),script)
                self.assertIn("repeat with existingDocument in documents",script)
                self.assertEqual(argv[2],str(source.resolve()))
                self.assertEqual(argv[-2:], [source.stem,source.name])
                dest.write_bytes(b"%PDF-valid-test")
                return type("Completed",(),{"returncode":0})()
            with patch.object(pptx_render.sys,"platform","darwin"),patch.object(pptx_render.subprocess,"run",side_effect=export):
                pptx_render.render_pptx(source,dest,app)

if __name__ == "__main__":
    unittest.main()
