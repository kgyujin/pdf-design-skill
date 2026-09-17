---
name: pdf-design
description: 디자인을 골라 쓰는 PDF 제작 스킬. 보고서·제안서·원페이저·이력서와 16:9 발표 자료를 HTML/CSS 템플릿으로 만들고 Chrome으로 PDF를 렌더링한다. 스타일 9종·색조 10종·폰트·밀도·모서리·포인트색을 따로 바꿀 수 있고, 여러 디자인 안을 비교표로 뽑아 고르게 한다. 논문·보고서를 발표용 슬라이드 PDF와 슬라이드별 발표 대본 DOCX로 만드는 발표 자료 모드와, 넘침·작은 글씨·노트 누락을 잡는 자동 검수를 포함한다. "PDF 예쁘게 만들어줘", "보고서 PDF", "디자인 시안 여러 개", "스타일만 바꿔줘(색은 유지)", "발표자료/PPT를 PDF로", "논문 발표 슬라이드와 대본", "원페이저" 같은 요청에 사용한다. 기존 PDF의 텍스트 추출·병합·분할에는 사용하지 않는다.
---

# pdf-design

내용(HTML)과 디자인(`<html data-*>` 속성)을 분리해 둔다. 한 축만 바꿔도 나머지 축과 내용은 그대로 유지된다.

`SKILL_DIR`는 이 파일이 있는 폴더다. Claude Code는 `~/.claude/skills/pdf-design`, Codex는 `~/.codex/skills/pdf-design`이며, 두 경로 모두 같은 저장소를 가리킨다.
CLI는 `python3 SKILL_DIR/scripts/pdfdesign.py <명령>` 형태로 실행한다.

## 디자인 축

| 축 | 옵션 | 값 (첫 값이 기본) |
|---|---|---|
| 스타일(조판·표지·제목·표·카드 모양) | `--style` | `swiss` `editorial` `bold` `minimal` `tech` `academic` `soft` `classic` `split` |
| 색조 | `--palette` | `indigo` `navy` `terracotta` `forest` `plum` `mono` `graphite` `crimson` `teal` `sand` |
| 폰트 조합 | `--font` | `auto` `sans` `serif` `serif-all` `mono` |
| 밀도 | `--density` | `normal` `compact` `airy` |
| 모서리 | `--radius` | `auto` `sharp` `soft` `round` |
| 포인트색만 교체 | `--accent` | `#RRGGBB` / `none` |

각 값의 설명은 `pdfdesign.py options`로 확인한다. 스타일별 특징과 추천 조합은 `references/styles.md`에 있다.

**폰트 규칙**: 기본 폰트는 모든 스타일에서 Pretendard다(제목·본문·라벨 모두). 코드(`code`, `pre`)만 모노 폰트를 쓰고, 라벨을 모노로 바꾸는 `--font mono`도 요청할 때만 쓴다. 바탕체·명조체(세리프)는 **사용자가 명시적으로 요청했을 때만** 쓴다. 그때는 `--font serif`(제목만) 또는 `--font serif-all`(본문까지)을 지정하며, 폰트는 고운바탕(Gowun Batang)이다. "격식 있게", "클래식하게", "잡지처럼" 같은 요청만으로는 바탕체를 쓰지 않는다. 문서 `<style>`에서 다른 세리프 폰트를 직접 지정하지 않는다.

## 템플릿

| 템플릿 | 용도 | 기본 디자인 |
|---|---|---|
| `report` | 표지·러닝 헤더·쪽번호가 있는 A4 문서 | swiss + indigo |
| `onepager` | A4 한 장(이력서, 프로젝트 요약) | swiss + indigo |
| `deck` | 짧은 16:9 발표(피치, 사내 공유) | swiss + indigo |
| `talk` | 논문·보고서 기반 발표. 레이아웃 8종, 수식(KaTeX), 발표자 노트 → DOCX 대본 | academic + graphite |

**발표 자료(슬라이드 PDF + 대본)를 만들 때는 먼저 `references/presentation.md`를 읽고 그 절차를 따른다.** 사용자가 자세한 요구사항을 주지 않았으면 `prompts/presentation.md`의 지침을 기본값으로 삼는다.

## 작업 순서

1. **요청 해석**: 독자·결론·템플릿을 정한다. `references/design-rules.md`를 읽는다.
   - 사용자가 디자인을 지정했으면 그 값을 쓴다. "색은 그대로, 스타일만 다르게"처럼 일부만 말했으면 **말한 축만** 바꾼다.
   - 지정이 없으면 작업 폴더의 `pdf-design.json`(저장된 취향)을 따른다. 그것도 없으면 템플릿 기본값이나 `references/styles.md`의 추천 조합을 쓰고, 무엇을 골랐는지 알린다.
2. **템플릿 복사**:
   ```bash
   python3 SKILL_DIR/scripts/pdfdesign.py init report ./out/report.html --style swiss --palette navy
   ```
   `pdf-design.css`가 함께 생성된다. 이 파일은 생성물이므로 직접 수정하지 않는다.
3. **내용 채우기**: 복사한 HTML을 편집한다.
   - 공통 클래스를 쓴다. 스타일에 따라 모양이 자동으로 바뀐다. 목록은 `references/components.md`에 있다.
   - 색은 `var(--accent)` 같은 토큰으로만 쓴다. HEX를 직접 쓰면 색조를 바꿔도 그 부분은 바뀌지 않는다.
   - 문서 전용 스타일은 `<head>`의 `<style>`에 둔다. 러닝 헤더 문구와 `<title>`을 실제 제목으로 바꾼다.
4. **디자인 안 비교** (사용자가 시안·후보·여러 안을 원하거나 디자인을 정하지 못했을 때):
   ```bash
   python3 SKILL_DIR/scripts/pdfdesign.py gallery ./out/report.html --styles all              # 색조 유지, 스타일 9안
   python3 SKILL_DIR/scripts/pdfdesign.py gallery ./out/report.html --palettes all            # 스타일 유지, 색조 10안
   python3 SKILL_DIR/scripts/pdfdesign.py gallery ./out/report.html --styles bold,tech --palettes keep,navy   # 조합 4안
   ```
   - 지정하지 않은 축은 현재 값으로 고정된다(`keep`). 후보는 최대 60개다. 처음에는 한 축씩 비교하는 편이 고르기 쉽다.
   - 결과는 `<문서명>_gallery/`에 생긴다: `gallery.pdf`, `sheet/page-N.png`(비교표), 후보별 `A/doc.pdf`.
   - 비교표 PNG를 열어 확인한 뒤 사용자에게 보여주고(파일 전달 도구가 있으면 사용), 후보 라벨(A, B, …)로 고르게 한다.
   - 선택되면 출력된 적용 명령으로 원본에 반영한다.
5. **디자인 적용·미세 조정**: 바꿀 축만 넘긴다. 나머지 축과 본문은 그대로 유지된다.
   ```bash
   python3 SKILL_DIR/scripts/pdfdesign.py set ./out/report.html --style editorial               # 색조 유지
   python3 SKILL_DIR/scripts/pdfdesign.py set ./out/report.html --accent "#e8590c" --density compact
   python3 SKILL_DIR/scripts/pdfdesign.py set ./out/report.html --save                          # 현재 설정을 폴더 기본값으로 저장
   ```
   사용자가 "앞으로도 이 디자인으로"라고 하면 `--save`로 `pdf-design.json`에 저장한다. 같은 폴더에서 다음에 `init`하면 이 값이 기본으로 적용된다.
6. **렌더링**:
   ```bash
   python3 SKILL_DIR/scripts/pdfdesign.py render ./out/report.html --preview
   python3 SKILL_DIR/scripts/pdfdesign.py render ./out/talk.html --preview --expect-pages <슬라이드 수>
   python3 SKILL_DIR/scripts/pdfdesign.py render ./out/onepager.html --preview --expect-pages 1
   ```
7. **자동 검수**: 고정 크기 페이지(슬라이드·원페이저·표지)가 있으면 반드시 실행하고, 오류가 0건이 될 때까지 고친다.
   ```bash
   python3 SKILL_DIR/scripts/pdfdesign.py check ./out/talk.html        # --strict 를 붙이면 경고도 실패 처리
   ```
   넘친 요소, 본문과 출처·쪽번호의 겹침, 잘린 내용, 작은 글씨, 깨지거나 흐린 이미지, 수식 오류, 노트·출처 누락을 찾는다.
8. **시각 검수 (생략 금지)**: `<이름>_preview/page-N.png`를 **모든 페이지** 열어 `design-rules.md`의 체크리스트로 확인한다. `check`는 SVG·이미지 **안쪽**의 겹침(핀이 라벨을 가리는 경우 등)과 수치의 정확성은 판단하지 못한다. 문제가 있으면 고친 뒤 6번부터 다시 한다.
9. **발표 대본** (`deck`·`talk`):
   ```bash
   python3 SKILL_DIR/scripts/pdfdesign.py script ./out/talk.html       # talk_script.docx + 슬라이드별 예상 시간
   ```
   목표 시간(`<meta name="pdf-design:duration">` 또는 `--minutes`)과 ±15% 넘게 차이 나면 대본 분량을 조정한다.
10. **보고**: PDF(와 DOCX) 경로, 쪽수, 최종 디자인 설정(`render`가 출력하는 `디자인:` 줄), `check` 결과, 검수에서 고친 부분을 알린다. 갤러리·미리보기 폴더는 필요 없으면 지워도 된다고 안내한다.

## 요구 사항·주의
- Chrome, Chromium, Edge 중 하나가 필요하다(`CHROME_PATH`로 경로 지정 가능). 미리보기·갤러리·대본 썸네일에는 Poppler(`pdftoppm`, `pdfinfo`)가 필요하다. DOCX 생성에는 추가 패키지가 필요 없다.
- Chrome을 직접 호출하지 않는다. macOS Chrome은 작업을 끝낸 뒤에도 종료되지 않을 수 있는데, 스크립트가 이를 처리한다.
- 폰트(Pretendard, 고운바탕, JetBrains Mono)와 수식(KaTeX)은 로컬에 없으면 CDN에서 받는다. 오프라인이면 폰트는 OS 한글 폰트로 대체되고 수식은 렌더링되지 않는다(`check`가 오류로 알려준다).
- 사용자가 주지 않은 수치나 사실을 지어내지 않는다. 데모가 필요하면 문서에 "예시 데이터"라고 표시한다.
- 새 스타일이나 색조를 추가할 때는 `references/extending.md`를 따른다.
