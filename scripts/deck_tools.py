"""
작성자: Git 이력 참조
작성목적: 발표 자료(deck/talk) 전용 도구. 슬라이드·발표자 노트 파싱, 발표 시간 추정,
         헤드리스 Chrome에서 실행할 레이아웃 검사 스크립트, 검사 결과 해석을 담당한다.
작성일: 2026-09-17

주요 입력: section.slide 들로 이루어진 HTML 문자열
주요 출력: Slide 목록(제목·핵심 메시지·출처·노트 블록·대본 텍스트), 검사 이슈 목록
주의사항:
  - 노트 마크업 규칙: <aside class="notes"> 안의 h4 = 소제목, p/li = 설명, <div class="talk"> 안의 p = 실제로 읽을 대본.
  - 발표 시간은 .talk 텍스트만으로 추정한다. 한국어는 공백 제외 글자 수, 그 외 언어는 단어 수 기준이다.
  - CHECK_SCRIPT 의 임계값(pt)은 SKILL/프롬프트의 글자 크기 기준과 맞춰야 한다.
변경사항 내역:
- 2026-09-17 | 최초 작성 | 노트 파서, 시간 추정, 레이아웃 검사
- 2026-09-17 | AI 티 검사 | audit_design: 장식 효과·대문자 라벨·0 붙은 번호·이모지·줄표·카드 3개 나열 등
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

KOREAN_CHARS_PER_MINUTE = 330  # 발표 말하기 속도(공백 제외 음절). 설명 위주 발표의 보통 속도.
ENGLISH_WORDS_PER_MINUTE = 140
HANGUL_PATTERN = re.compile(r"[가-힣]")
SLIDE_PATTERN = re.compile(r"<section\b[^>]*\bclass=\"[^\"]*\bslide\b[^\"]*\"[^>]*>.*?</section>", re.DOTALL | re.IGNORECASE)
DURATION_META_PATTERN = re.compile(r'<meta\s+name="pdf-design:duration"\s+content="([\d.]+)"', re.IGNORECASE)
CHECK_RESULT_ID = "pdf-design-check-result"
VOID_TAGS = {"br", "img", "hr", "meta", "link", "input", "source", "wbr"}


@dataclass
class NoteBlock:
    kind: str  # heading | paragraph | bullet | talk
    runs: list[tuple[str, bool]] = field(default_factory=list)
    level: int = 0

    @property
    def text(self) -> str:
        return "".join(text for text, _ in self.runs).strip()


@dataclass
class Slide:
    index: int
    kinds: list[str]
    title: str = ""
    message: str = ""
    source: str = ""
    notes: list[NoteBlock] = field(default_factory=list)

    @property
    def talk_text(self) -> str:
        return " ".join(block.text for block in self.notes if block.kind == "talk")

    @property
    def has_notes(self) -> bool:
        return any(block.text for block in self.notes)


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _SlideParser(HTMLParser):
    """section.slide 하나를 읽어 제목·메시지·출처·노트 블록을 모은다."""

    CAPTURE_CLASSES = {"slide-title": "title", "slide-msg": "message", "source": "source"}
    BLOCK_TAGS = {"p": "paragraph", "li": "bullet", "h4": "heading", "h5": "heading", "h3": "heading", "div": None}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fields = {"title": [], "message": [], "source": []}
        self.notes: list[NoteBlock] = []
        self.slide_classes: list[str] = []
        self._stack: list[tuple[str, set[str]]] = []
        self._bold_depth = 0
        self._list_depth = 0
        self._current: NoteBlock | None = None

    def _inside(self, class_name: str) -> bool:
        return any(class_name in classes for _, classes in self._stack)

    def _in_notes(self) -> bool:
        return any(tag == "aside" and "notes" in classes for tag, classes in self._stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = set((dict(attrs).get("class") or "").split())
        if tag == "section" and not self._stack:
            self.slide_classes = sorted(classes)
        if tag in VOID_TAGS:
            if tag == "br":
                self.handle_data("\n")
            return
        self._stack.append((tag, classes))
        if not self._in_notes():
            return
        if tag in ("strong", "b"):
            self._bold_depth += 1
        elif tag in ("ul", "ol"):
            self._list_depth += 1
        elif tag in self.BLOCK_TAGS and self.BLOCK_TAGS[tag]:
            kind = self.BLOCK_TAGS[tag]
            if kind == "paragraph" and self._inside("talk"):
                kind = "talk"
            self._current = NoteBlock(kind=kind, level=max(self._list_depth - 1, 0))
            self.notes.append(self._current)

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        # 잘못 닫힌 태그가 있어도 스택이 어긋나지 않도록 가장 가까운 같은 태그까지 닫는다.
        for position in range(len(self._stack) - 1, -1, -1):
            if self._stack[position][0] == tag:
                was_in_notes = self._in_notes()
                del self._stack[position:]
                break
        else:
            return
        if not was_in_notes:
            return
        if tag in ("strong", "b"):
            self._bold_depth = max(self._bold_depth - 1, 0)
        elif tag in ("ul", "ol"):
            self._list_depth = max(self._list_depth - 1, 0)
        elif tag in self.BLOCK_TAGS:
            self._current = None

    def handle_data(self, data: str) -> None:
        if not self._stack:
            return
        if self._in_notes():
            if not data.strip() and self._current is None:
                return
            if self._current is None:
                # 블록 태그 없이 노트에 바로 쓴 글은 문단으로 취급한다(대본 div 안이면 대본).
                self._current = NoteBlock(kind="talk" if self._inside("talk") else "paragraph")
                self.notes.append(self._current)
            text = data if data == "\n" else re.sub(r"\s+", " ", data)
            self._current.runs.append((text, self._bold_depth > 0))
            return
        for class_name, field_name in self.CAPTURE_CLASSES.items():
            if self._inside(class_name):
                self.fields[field_name].append(data)


def parse_slides(html_text: str) -> list[Slide]:
    slides = []
    for index, match in enumerate(SLIDE_PATTERN.finditer(html_text), start=1):
        parser = _SlideParser()
        parser.feed(match.group(0))
        parser.close()
        notes = [block for block in parser.notes if block.text]
        for block in notes:
            block.runs = [(re.sub(r" {2,}", " ", text), is_bold) for text, is_bold in block.runs]
            if block.runs:
                first_text, first_bold = block.runs[0]
                block.runs[0] = (first_text.lstrip(), first_bold)
        slides.append(
            Slide(
                index=index,
                kinds=[name for name in parser.slide_classes if name != "slide"],
                title=_collapse(" ".join(parser.fields["title"])),
                message=_collapse(" ".join(parser.fields["message"])),
                source=_collapse(" ".join(parser.fields["source"])),
                notes=notes,
            )
        )
    return slides


def read_target_minutes(html_text: str) -> float | None:
    match = DURATION_META_PATTERN.search(html_text)
    return float(match.group(1)) if match else None


def estimate_seconds(text: str) -> int:
    if not text.strip():
        return 0
    hangul_count = len(HANGUL_PATTERN.findall(text))
    visible_count = len(re.sub(r"\s", "", text))
    if visible_count and hangul_count / visible_count >= 0.3:
        return round(visible_count / KOREAN_CHARS_PER_MINUTE * 60)
    return round(len(text.split()) / ENGLISH_WORDS_PER_MINUTE * 60)


def format_duration(seconds: int) -> str:
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes}분 {remainder:02d}초" if minutes else f"{remainder}초"


def audit_slides(slides: list[Slide]) -> list[dict]:
    """HTML 구조만으로 알 수 있는 문제(렌더링 없이). 노트·출처·대본 누락, 포인트 개수."""
    issues = []
    for slide in slides:
        where = f"slide {slide.index}"
        is_cover_like = bool({"hero", "section"} & set(slide.kinds))
        if not slide.has_notes:
            issues.append({"level": "warn", "where": where, "message": "발표자 노트(aside.notes)가 없습니다."})
        elif not slide.talk_text:
            issues.append({"level": "warn", "where": where, "message": "읽을 대본(div.talk)이 없어 발표 시간을 추정할 수 없습니다."})
        if not slide.source and not is_cover_like:
            issues.append({"level": "warn", "where": where, "message": "하단 출처(.slide-foot .source)가 비어 있습니다."})
        if not slide.title:
            issues.append({"level": "warn", "where": where, "message": "슬라이드 제목(.slide-title)이 없습니다."})
    return issues


AI_TELL_PREFIX = "AI 티: "
STYLE_BLOCK_PATTERN = re.compile(r"<style(?![^>]*id=\"pdf-design-accent\")[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
INLINE_STYLE_PATTERN = re.compile(r'\sstyle="([^"]*)"', re.IGNORECASE)
# (정규식, 설명). 문서가 직접 넣은 스타일에서만 찾는다. 스킬 CSS 번들은 references/anti-ai-design.md 기준으로 관리한다.
STYLE_TELLS = (
    (re.compile(r"gradient\s*\(", re.I), "그라데이션"),
    (re.compile(r"(?:box|text)-shadow\s*:", re.I), "그림자 효과"),
    (re.compile(r"backdrop-filter|filter\s*:\s*blur", re.I), "흐림(유리) 효과"),
    (re.compile(r"border-radius\s*:\s*(?:999|9999)px|border-radius\s*:\s*50%", re.I), "알약·원형 장식"),
    (re.compile(r"text-transform\s*:\s*uppercase", re.I), "대문자 라벨"),
    (re.compile(r"letter-spacing\s*:\s*0?\.(?:[1-9])\d*em", re.I), "넓은 자간 라벨"),
    (re.compile(r"border-left\s*:\s*(?:[2-9]|\d{2})(?:\.\d+)?(?:pt|px)", re.I), "왼쪽 굵은 세로 바"),
    (re.compile(r":[^;{}]*#[0-9a-f]{3}(?:[0-9a-f]{3})?\b", re.I), "토큰이 아닌 HEX 색"),
)
EMOJI_PATTERN = re.compile("[\U0001F000-\U0001FAFF☀-⛿✀-➿️]")
EM_DASH_PROSE_PATTERN = re.compile(r"\S\s*—\s*\S")
TAG_PATTERN = re.compile(r"<[^>]+>")
NON_TEXT_PATTERN = re.compile(r"<(style|script)\b.*?</\1>|<!--.*?-->", re.DOTALL | re.IGNORECASE)


def _visible_text(fragment: str) -> str:
    return _collapse(TAG_PATTERN.sub(" ", NON_TEXT_PATTERN.sub(" ", fragment)))


def audit_design(html_text: str) -> list[dict]:
    """문서 HTML에서 흔한 'AI가 만든 티' 패턴을 찾는다(references/anti-ai-design.md)."""
    issues = []

    def warn(message: str, where: str = "document") -> None:
        issues.append({"level": "warn", "where": where, "message": AI_TELL_PREFIX + message})

    style_sources = STYLE_BLOCK_PATTERN.findall(html_text)
    # 핀 위치·막대 길이처럼 값만 주는 인라인 스타일은 정상이다.
    style_sources += [value for value in INLINE_STYLE_PATTERN.findall(html_text) if not re.fullmatch(r"[\s;]*(?:(?:left|top|width|height)\s*:\s*[\d.]+(?:%|mm|pt|px)\s*;?\s*)+", value)]
    style_text = re.sub(r"/\*.*?\*/", "", "\n".join(style_sources), flags=re.DOTALL)
    for pattern, label in STYLE_TELLS:
        found = pattern.search(style_text)
        if found:
            warn(f"문서 스타일에 {label}이(가) 있습니다: `{found.group(0)}`. 토큰과 기본 스타일을 쓰세요.")

    body_text = _visible_text(html_text)
    emoji = EMOJI_PATTERN.findall(body_text)
    if emoji:
        warn(f"이모지·장식 기호가 {len(emoji)}개 있습니다: {''.join(dict.fromkeys(emoji))[:10]}")

    prose_blocks = re.findall(r"<(p|li|h[1-4])\b[^>]*>(.*?)</\1>", html_text, re.DOTALL | re.IGNORECASE)
    dash_blocks = [text for _, text in prose_blocks if EM_DASH_PROSE_PATTERN.search(_visible_text(text))]
    if len(dash_blocks) >= 2:
        warn(f"줄표(—)로 문장을 잇는 문단이 {len(dash_blocks)}개입니다. 쉼표·마침표·괄호로 바꾸세요.")

    padded = re.findall(r'class="(?:sec-num|sec-big)">\s*0\d', html_text)
    if padded:
        warn(f"0을 붙인 번호(01, 02 …)가 {len(padded)}곳에 있습니다. 1, 2 … 로 쓰세요.")

    slides = SLIDE_PATTERN.findall(html_text)
    if slides:
        content_slides = [chunk for chunk in slides if not re.search(r'class="[^"]*\bslide\b[^"]*\b(?:hero|section)\b', chunk)]
        labelled = [chunk for chunk in content_slides if 'class="eyebrow"' in chunk]
        if len(content_slides) >= 3 and len(labelled) * 2 > len(content_slides):
            warn(f"내용 슬라이드 {len(content_slides)}장 중 {len(labelled)}장에 제목 위 라벨이 있습니다. 표지·섹션에만 쓰세요.")
    else:
        body_only = re.sub(r'<section class="cover".*?</section>', "", html_text, flags=re.DOTALL)
        eyebrow_count = body_only.count('class="eyebrow"')
        if eyebrow_count >= 3:
            warn(f"본문에 제목 위 라벨이 {eyebrow_count}개 있습니다. 반복 라벨은 빼세요.")

    card_rows = re.findall(r'<div class="grid-3[^"]*">\s*(?:<div class="card[^"]*">.*?</div>\s*){3}</div>', html_text, re.DOTALL)
    if card_rows:
        warn(f"같은 모양 카드 3개를 나열한 곳이 {len(card_rows)}곳 있습니다. 번호 목록이나 표가 맞는지 확인하세요.")
    return issues


# 헤드리스 Chrome에서 폰트·이미지·수식 로딩 후 실행해 결과를 JSON으로 DOM에 남긴다.
CHECK_SCRIPT = r"""
<script id="pdf-design-check-runner">
(async () => {
  const PX_PER_PT = 96 / 72;
  const MIN_TEXT_PT = 10, MIN_BODY_PT = 16, MIN_TABLE_PT = 12, MIN_EQUATION_PT = 24, MAX_POINTS = 5;
  const issues = [];
  const add = (level, where, message) => issues.push({ level, where, message });
  const snippet = (el) => (el.textContent || el.getAttribute('src') || el.tagName).replace(/\s+/g, ' ').trim().slice(0, 40);
  const describe = (el) => el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).join('.') : '');
  const visible = (el) => { const cs = getComputedStyle(el); return cs.display !== 'none' && cs.visibility !== 'hidden'; };
  try { await document.fonts.ready; } catch (error) {}
  await Promise.all([...document.images].map((img) => img.complete ? null : new Promise((done) => { img.addEventListener('load', done); img.addEventListener('error', done); })));
  await new Promise((done) => setTimeout(done, 400));

  let slideNo = 0, sheetNo = 0, coverNo = 0;
  for (const page of document.querySelectorAll('.slide, .sheet, .cover')) {
    const isSlide = page.classList.contains('slide');
    const where = isSlide ? `slide ${++slideNo}` : page.classList.contains('sheet') ? `sheet ${++sheetNo}` : `cover ${++coverNo}`;
    const box = page.getBoundingClientRect();
    let overflowCount = 0;
    for (const el of page.querySelectorAll('*')) {
      if (el.closest('aside.notes, .katex-mathml') || (el.closest('svg') && el.tagName.toLowerCase() !== 'svg')) continue;
      if (!visible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      if ((r.right > box.right + 1 || r.bottom > box.bottom + 1 || r.left < box.left - 1 || r.top < box.top - 1) && overflowCount < 3) {
        overflowCount += 1;
        add('error', where, `페이지 밖으로 넘침: ${describe(el)} "${snippet(el)}"`);
      }
      const cs = getComputedStyle(el);
      if (cs.overflow !== 'visible' && !el.matches('.slide, .sheet, .cover, .bar, .source, .fig-frame') && (el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2)) {
        add('error', where, `내용이 잘림(스크롤 필요): ${describe(el)} "${snippet(el)}"`);
      }
    }
    const body = page.querySelector(':scope > .slide-body');
    const foot = page.querySelector(':scope > .slide-foot');
    if (body && body.scrollHeight > body.clientHeight + 2) add('error', where, `본문이 영역을 넘침(${Math.round((body.scrollHeight - body.clientHeight) / PX_PER_PT)}pt 초과)`);
    if (body && foot) {
      const footTop = foot.getBoundingClientRect().top;
      const lowest = Math.max(0, ...[...body.querySelectorAll('*')].filter(visible).map((el) => el.getBoundingClientRect().bottom));
      if (lowest > footTop - 2) add('error', where, '본문이 하단 출처·쪽번호와 겹칩니다.');
    }
    const source = page.querySelector('.slide-foot .source');
    if (source && source.scrollWidth > source.clientWidth + 1) add('warn', where, '출처 문구가 길어 잘렸습니다. 줄이거나 노트로 옮기세요.');

    if (isSlide) {
      const walker = document.createTreeWalker(page, NodeFilter.SHOW_TEXT);
      let smallCount = 0, bodyWarned = false;
      while (walker.nextNode()) {
        const node = walker.currentNode;
        const parent = node.parentElement;
        if (!node.textContent.trim() || !parent || parent.closest('aside.notes, .katex, svg') || !visible(parent)) continue;
        const pt = parseFloat(getComputedStyle(parent).fontSize) / PX_PER_PT;
        if (pt < MIN_TEXT_PT - 0.05 && smallCount < 2) { smallCount += 1; add('error', where, `글자가 너무 작음(${pt.toFixed(1)}pt < ${MIN_TEXT_PT}pt): "${node.textContent.trim().slice(0, 30)}"`); }
        const block = parent.closest('p, li, td, th');
        if (!bodyWarned && block && !parent.closest('.cond, code, .tag, .badge, .eyebrow, .pin') && !block.closest('.slide-foot, figcaption, caption, .fig-label, .card, .small, .derive, .symbols')) {
          const limit = block.matches('td, th') ? MIN_TABLE_PT : MIN_BODY_PT;
          if (pt < limit - 0.05) { bodyWarned = true; add('warn', where, `${block.matches('td, th') ? '표' : '본문'} 글자가 작음(${pt.toFixed(1)}pt < ${limit}pt)`); }
        }
      }
      let svgWarned = false;
      for (const label of page.querySelectorAll('svg text')) {
        const height = label.getBoundingClientRect().height / PX_PER_PT;
        if (!svgWarned && label.textContent.trim() && height > 0 && height < MIN_TEXT_PT) { svgWarned = true; add('warn', where, `Figure 안 글자가 작음(약 ${height.toFixed(1)}pt): "${label.textContent.trim().slice(0, 20)}" — 축·범례는 화면에서 읽혀야 합니다.`); }
      }
      for (const eq of page.querySelectorAll('.equation')) {
        const pt = parseFloat(getComputedStyle(eq).fontSize) / PX_PER_PT;
        if (pt < MIN_EQUATION_PT) add('warn', where, `수식이 작음(${pt.toFixed(1)}pt < ${MIN_EQUATION_PT}pt)`);
      }
      const points = page.querySelectorAll('.points > li').length;
      if (points > MAX_POINTS) add('warn', where, `핵심 포인트가 ${points}개입니다(권장 3~${MAX_POINTS}개). 나머지는 대본으로 옮기세요.`);
      if (/\\\(|\$\$/.test(page.querySelector('.slide-body')?.textContent || '')) add('error', where, '수식이 렌더링되지 않았습니다(KaTeX 로딩 실패 또는 구분자 오류).');
    }
    for (const err of page.querySelectorAll('.katex-error')) add('error', where, `수식 오류: ${err.getAttribute('title') || snippet(err)}`);
    for (const img of page.querySelectorAll('img')) {
      if (!img.naturalWidth) { add('error', where, `이미지를 불러오지 못함: ${img.getAttribute('src')}`); continue; }
      const r = img.getBoundingClientRect();
      const fit = getComputedStyle(img).objectFit;
      const natural = img.naturalWidth / img.naturalHeight, shown = r.width / r.height;
      if (!['contain', 'cover', 'scale-down'].includes(fit) && Math.abs(shown - natural) / natural > 0.02) add('error', where, `이미지 비율이 깨짐: ${img.getAttribute('src')}`);
      // 인쇄 시 약 200dpi 이상이어야 흐리지 않다. CSS px(96dpi) 기준 폭의 2배 정도의 원본 해상도를 권장한다.
      if (img.naturalWidth < r.width * 1.5) add('warn', where, `이미지 해상도가 낮아 흐릴 수 있음(${img.naturalWidth}px, 표시 폭 ${Math.round(r.width)}px): ${img.getAttribute('src')}`);
    }
    if (/\{\{[^}]*\}\}|TODO|자리표시/.test(page.innerText)) add('warn', where, '자리표시 문구({{…}}, TODO)가 남아 있습니다.');
  }
  const result = document.createElement('script');
  result.type = 'application/json';
  result.id = 'pdf-design-check-result';
  result.textContent = JSON.stringify({ issues, slides: slideNo }).replace(/</g, '\\u003c');
  document.body.appendChild(result);
})();
</script>
"""


def inject_check_script(html_text: str) -> str:
    body_end = html_text.lower().rfind("</body>")
    if body_end < 0:
        return html_text + CHECK_SCRIPT
    return html_text[:body_end] + CHECK_SCRIPT + html_text[body_end:]


def extract_check_result(dumped_dom: str) -> dict | None:
    match = re.search(rf'<script type="application/json" id="{CHECK_RESULT_ID}">(.*?)</script>', dumped_dom, re.DOTALL)
    if not match:
        return None
    return json.loads(match.group(1))
