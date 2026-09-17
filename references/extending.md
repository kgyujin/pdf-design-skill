# 스타일·색조 추가 방법

## 새 색조
1. `assets/css/palettes.css`에 `html[data-palette="이름"] { ... }` 블록을 추가한다. 기존 팔레트와 **같은 토큰 13개**를 모두 정의한다.
2. `scripts/pdfkit.py`의 `DESIGN_AXES["palette"]`에 이름과 설명을 추가한다.
3. `references/styles.md`의 색조 표에 추가한다.
4. 검증:
   ```bash
   python3 -m unittest discover -s tests
   python3 scripts/pdfkit.py gallery examples/ops-report.html --palettes keep,이름
   ```

## 새 스타일
1. `assets/css/styles/이름.css`를 만든다. 모든 선택자는 `html[data-style="이름"]`으로 시작한다.
2. 색은 토큰만 쓴다. 어두운 면이 필요하면 `bold.css`처럼 `:is(.cover, .slide.hero, .side)`에 inverse 토큰을 다시 정의한다.
3. 최소한 다음 요소의 모양을 정한다: `.cover`, `h2`(`.sec-num`), `th`/`td`, `.kpi`, `.card`(`.hl` 포함), `.callout`, `.slide.hero`, `.side`.
4. `DESIGN_AXES["style"]`와 `references/styles.md`에 추가한다. 번들 순서는 `DESIGN_AXES`의 순서를 따른다.
5. 검증: 테스트를 실행한 뒤 보고서·덱·원페이저 세 템플릿으로 갤러리를 만들어 모든 썸네일을 확인한다. 특히 `.card.hl`의 글자가 보이는지, 표 캡션이 표와 붙어 있는지 확인한다.

## 규칙
- `core.css`에는 모든 스타일이 공유하는 구조만 둔다. 특정 스타일에서만 쓰는 모양은 스타일 파일에 둔다.
- 옵션 축(font·density·radius)은 스타일보다 뒤에 번들되므로, 스타일 파일에서 `--font-head`, `--radius` 같은 토큰으로 기본값을 정하면 옵션이 덮어쓸 수 있다. 값을 속성에 직접 쓰면 옵션이 동작하지 않는다.
