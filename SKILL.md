---
name: pdf-kit
description: 디자인을 골라 쓰는 PDF 제작 스킬. 보고서·제안서·원페이저·이력서·16:9 발표 자료를 HTML/CSS 템플릿으로 만들고 Chrome으로 PDF를 렌더링한다. 스타일(swiss·editorial·bold·minimal·tech), 색조, 폰트, 밀도, 모서리, 포인트색을 각각 따로 바꿀 수 있고, 여러 디자인 안을 비교표로 뽑아 고르게 한다. "PDF 예쁘게 만들어줘", "보고서 PDF", "디자인 시안 여러 개", "다른 스타일로 바꿔줘(색은 유지)", "슬라이드 PDF", "원페이저" 같은 요청에 사용한다. 기존 PDF의 텍스트 추출·병합·분할에는 사용하지 않는다.
---

# pdf-kit

내용(HTML)과 디자인(`<html data-*>` 속성)을 분리해 둔다. 한 축만 바꿔도 나머지 축과 내용은 그대로 유지된다.

`KIT`는 이 파일이 있는 폴더다. Claude Code는 `~/.claude/skills/pdf-kit`, Codex는 `~/.codex/skills/pdf-kit`이며, 두 경로 모두 같은 저장소를 가리킨다.
CLI는 `python3 KIT/scripts/pdfkit.py <명령>` 형태로 실행한다.

## 디자인 축

| 축 | 옵션 | 값 (첫 값이 기본) |
|---|---|---|
| 스타일(조판·표지·제목·표·카드 모양) | `--style` | `swiss` `editorial` `bold` `minimal` `tech` |
| 색조 | `--palette` | `indigo` `navy` `terracotta` `forest` `plum` `mono` |
| 폰트 조합 | `--font` | `auto` `sans` `serif` `mono` |
| 밀도 | `--density` | `normal` `compact` `airy` |
| 모서리 | `--radius` | `auto` `sharp` `soft` `round` |
| 포인트색만 교체 | `--accent` | `#RRGGBB` / `none` |

각 값의 설명은 `pdfkit.py options`로 확인한다. 스타일별 특징과 용도는 `references/styles.md`에 있다.

## 작업 순서

1. **요청 해석**: 독자·결론·형식(`report`·`onepager`·`deck`)을 정한다. `references/design-rules.md`를 읽는다.
   - 사용자가 디자인을 지정했으면 그 값을 쓴다. "색은 그대로, 스타일만 다르게"처럼 일부만 말했으면 **말한 축만** 바꾼다.
   - 지정이 없으면 작업 폴더의 `pdf-kit.json`(저장된 취향)을 따른다. 그것도 없으면 내용에 맞춰 `references/styles.md` 기준으로 고르고, 무엇을 골랐는지 알린다.
2. **템플릿 복사**:
   ```bash
   python3 KIT/scripts/pdfkit.py init report ./out/report.html --style swiss --palette navy
   ```
   `pdf-kit.css`가 함께 생성된다. 이 파일은 생성물이므로 직접 수정하지 않는다.
3. **내용 채우기**: 복사한 HTML을 편집한다.
   - 공통 클래스를 쓴다. 스타일에 따라 모양이 자동으로 바뀐다. 목록은 `references/components.md`에 있다.
   - 색은 `var(--accent)` 같은 토큰으로만 쓴다. HEX를 직접 쓰면 색조를 바꿔도 그 부분은 바뀌지 않는다.
   - 문서 전용 스타일은 `<head>`의 `<style>`에 둔다. 러닝 헤더 문구와 `<title>`을 실제 제목으로 바꾼다.
4. **디자인 안 비교** (사용자가 시안·후보·여러 안을 원하거나 디자인을 정하지 못했을 때):
   ```bash
   python3 KIT/scripts/pdfkit.py gallery ./out/report.html --styles all              # 색조는 유지, 스타일 5안
   python3 KIT/scripts/pdfkit.py gallery ./out/report.html --palettes all            # 스타일은 유지, 색조 6안
   python3 KIT/scripts/pdfkit.py gallery ./out/report.html --styles bold,tech --palettes keep,navy   # 조합 4안
   ```
   - 지정하지 않은 축은 현재 값으로 고정된다(`keep`). 후보는 최대 36개다.
   - 결과는 `<문서명>_gallery/`에 생긴다: `gallery.pdf`, `sheet/page-N.png`(비교표), 후보별 `A/doc.pdf`.
   - 비교표 PNG를 열어 확인한 뒤 사용자에게 보여주고(파일 전달 도구가 있으면 사용), 후보 라벨(A, B, …)로 고르게 한다.
   - 선택되면 출력된 적용 명령으로 원본에 반영한다.
5. **디자인 적용·미세 조정**: 바꿀 축만 넘긴다. 나머지 축과 본문은 그대로 유지된다.
   ```bash
   python3 KIT/scripts/pdfkit.py set ./out/report.html --style editorial               # 색조 유지
   python3 KIT/scripts/pdfkit.py set ./out/report.html --accent "#e8590c" --density compact
   python3 KIT/scripts/pdfkit.py set ./out/report.html --save                          # 현재 설정을 폴더 기본값으로 저장
   ```
   사용자가 "앞으로도 이 디자인으로"라고 하면 `--save`로 `pdf-kit.json`에 저장한다. 같은 폴더에서 다음에 `init`하면 이 값이 기본으로 적용된다.
6. **렌더링**:
   ```bash
   python3 KIT/scripts/pdfkit.py render ./out/report.html --preview
   python3 KIT/scripts/pdfkit.py render ./out/deck.html --preview --expect-pages <슬라이드 수>
   python3 KIT/scripts/pdfkit.py render ./out/onepager.html --preview --expect-pages 1
   ```
7. **시각 검수 (생략 금지)**: `<이름>_preview/page-N.png`를 **모든 페이지** 열어 `design-rules.md`의 체크리스트로 확인한다. 문제가 있으면 고친 뒤 6번부터 다시 한다.
8. **보고**: PDF 경로, 쪽수, 최종 디자인 설정(`render`가 출력하는 `디자인:` 줄), 검수에서 고친 부분을 알린다. 갤러리·미리보기 폴더는 필요 없으면 지워도 된다고 안내한다.

## 요구 사항·주의
- Chrome, Chromium, Edge 중 하나가 필요하다(`CHROME_PATH`로 경로 지정 가능). 미리보기·갤러리에는 Poppler(`pdftoppm`, `pdfinfo`)가 필요하다.
- Chrome을 직접 호출하지 않는다. macOS Chrome은 PDF를 다 쓴 뒤에도 종료되지 않을 수 있는데, 스크립트가 이를 처리한다.
- 폰트는 Pretendard(산세리프), Noto Serif KR(세리프), JetBrains Mono(모노)를 쓴다. 로컬에 없으면 CDN에서 받고, 오프라인이면 OS 기본 한글 폰트로 대체된다.
- 사용자가 주지 않은 수치나 사실을 지어내지 않는다. 데모가 필요하면 문서에 "예시 데이터"라고 표시한다.
- 새 스타일이나 색조를 추가할 때는 `references/extending.md`를 따른다.
