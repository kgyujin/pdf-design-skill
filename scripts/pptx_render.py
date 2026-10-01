"""Render an existing PPTX through macOS Keynote without modifying the source.

Inputs: trusted local PPTX, new PDF path. Output: PDF exported from that PPTX.
Only the opened task document is closed. Other open Keynote documents are untouched.
PowerPoint itself remains the reference application for final compatibility checks.
"""
from pathlib import Path
import subprocess
import tempfile
import sys


def render_pptx(pptx_path: Path, pdf_path: Path, app_path: Path) -> None:
    pptx_path, pdf_path, app_path = map(lambda p: Path(p).resolve(), (pptx_path, pdf_path, app_path))
    if sys.platform != 'darwin':
        raise ValueError('자동 PPTX→PDF 출력은 현재 macOS Keynote만 지원합니다. PowerPoint의 PDF 내보내기를 사용하세요.')
    if pptx_path.suffix.lower() != '.pptx' or not pptx_path.is_file():
        raise ValueError('입력 PPTX 파일을 확인하세요.')
    if not app_path.is_dir() or app_path.suffix != '.app':
        raise ValueError('설치된 Keynote 앱 경로를 --app으로 지정하세요.')
    if pdf_path.suffix.lower() != '.pdf' or pdf_path == pptx_path:
        raise ValueError('출력은 원본과 다른 PDF 경로여야 합니다.')
    if pdf_path.exists():
        raise ValueError('기존 PDF를 덮어쓰지 않습니다. 새 출력 경로를 지정하세요.')
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    # Pass paths as argv, not interpolated AppleScript source or shell command text.
    script = '''on run argv
set deckFile to POSIX file (item 1 of argv)
set pdfFile to POSIX file (item 2 of argv)
set appFile to item 3 of argv
using terms from application "Keynote"
 tell application appFile
  repeat with existingDocument in documents
   set existingName to name of existingDocument
   if existingName is (item 4 of argv) or existingName is (item 5 of argv) then
    error "같은 이름의 문서가 이미 열려 있습니다. 저장 후 닫거나 새 파일명으로 출력하세요."
   end if
  end repeat
  set taskDocument to open deckFile
  try
   export taskDocument to pdfFile as PDF
  on error errorMessage number errorNumber
   close taskDocument saving no
   error errorMessage number errorNumber
  end try
  close taskDocument saving no
 end tell
end using terms from
end run
'''
    with tempfile.TemporaryDirectory(prefix='pdf-design-keynote-') as temp:
        script_path = Path(temp) / 'render.applescript'
        script_path.write_text(script, encoding='utf-8')
        completed = subprocess.run(['osascript', str(script_path), str(pptx_path), str(pdf_path), str(app_path), pptx_path.stem, pptx_path.name], capture_output=True, text=True, timeout=120)
    if completed.returncode:
        raise ValueError('Keynote PDF 내보내기 실패: ' + completed.stderr.strip())
    if not pdf_path.exists() or pdf_path.read_bytes()[:5] != b'%PDF-':
        raise ValueError('Keynote가 유효한 PDF를 생성하지 못했습니다.')
