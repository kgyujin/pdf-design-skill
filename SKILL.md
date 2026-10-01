---
name: pdf-design
description: 보고서·원페이저·발표 자료를 디자인하고 PDF로 출력한다. 발표는 PowerPoint에서 편집 가능한 PPTX와 같은 원본에서 출력한 PDF를 제공한다. 참고 PDF 전체의 서체·정렬·여백·시각 위계·페이지 변화까지 분석하고, 주제에 맞는 선별 팔레트를 자동 선택한다. 차트·표·이미지·도식을 하나의 시각 체계로 구성하며 전체 페이지 렌더와 실제 크기 검수를 수행한다. "PDF 예쁘게 만들어줘", "발표자료 디자인", "PPTX로 편집", "보고서 PDF", "디자인 시안", "스타일만 바꿔줘" 요청에 사용한다. 기존 PDF의 단순 추출·병합·분할에는 사용하지 않는다.
---

# pdf-design

PDF를 읽기 편하게 디자인하고 수정 가능한 제작 원본을 함께 제공한다. 디자인만 요청받으면 글의 주장·순서·문장·수치를 임의로 고치지 않는다. 내용이 길어 배치가 어려우면 글자를 줄이기보다 영역 재배치나 페이지 분리를 검토한다.

`SKILL_DIR`는 이 파일이 있는 폴더다. CLI는 `python3 SKILL_DIR/scripts/pdfdesign.py <명령>`으로 실행한다.

## 제작 원칙

1. **전체 디자인을 참고한다.** 참고 PDF가 있으면 전 페이지를 펼쳐 보고 대표 페이지를 확대한다. 제목의 위치와 무게, 정렬축, 여백, 주영역과 보조영역의 비율, 표·차트의 규칙, 페이지별 밀도까지 분석한다. 도형이나 색 몇 개만 추출하는 것으로 대신하지 않는다.
2. **표지는 표지만 맡는다.** 제목·선택적 부제·팀/발표자·날짜·주제 이미지로 구성한다. KPI, 결론, 발표 목차, 분석 설명, 다음 행동을 기본으로 넣지 않는다. 넓은 빈 공간을 본문 상자로 채우지 않는다. 사용자가 명시한 추가 요소만 예외다.
3. **사용자가 편집할 수 있게 만든다.** 새 발표 자료의 기본 산출물은 PPTX와 그 PPTX에서 출력한 PDF다. 텍스트·표·단순 도식·지원 차트는 네이티브 개체로 만든다. 슬라이드 전체를 이미지로 넣은 PPTX는 편집용 원본이 아니다.
4. **화면에 불필요한 문구를 만들지 않는다.** 특별히 요청하지 않은 ‘출처’ 라벨·출처 푸터·참고자료 페이지를 자동으로 추가하지 않는다. 자산 경로·원본 페이지·라이선스 조건은 별도 제작 메타데이터에서 관리한다. 표시 의무가 있는 자산은 조건을 지킬 수 있는 대체 자산을 우선하거나 필요한 표시를 분명히 설명한다.
5. **색을 미리 설계한다.** 사용자 명시 설정 > 저장한 선호 > 주제 자동 선택 > neutral 순서다. [팔레트](references/palettes.md)의 선별 조합을 사용하고, 같은 데이터 그룹의 색은 문서 전체에서 유지한다. 기존 문서의 색을 유지하라는 요청이 있으면 자동 선택으로 덮어쓰지 않는다.
6. **완성도는 렌더 이미지로 판단한다.** 자동 검사 통과만으로 좋은 디자인이라고 판정하지 않는다. 전체 축소판과 개별 페이지를 모두 확인한다.

## 시작할 때 읽을 지침

- 공통: [디자인 규칙](references/design-rules.md), [반복 검토](references/anti-ai-design.md)
- 발표: [발표 제작 절차](references/presentation.md), [전체 시각 설계](references/visual-storytelling.md)
- PowerPoint 편집: [편집용 발표](references/editable-presentations.md)
- 컬러: [선별 팔레트](references/palettes.md)

2조 `독성예측_EDA_발표.pdf`와 3조 `광주캠퍼스_3조_EDA_발표.pdf`에서 확인한 전체 디자인 원리는 `visual-storytelling.md`에 기록되어 있다. 얇은 선·밝은 바탕·강한 제목·정렬된 표와 차트·변화하는 증거 영역을 함께 적용한다. 분석 내용이나 타 조의 수치는 가져오지 않는다. 원본 PDF가 제공되면 요약 지침만 읽지 말고 실제 전체 렌더를 확인한다.

## 작업 순서

1. **범위와 원본 확인**: 디자인만 바꾸는지 새 문서를 만드는지, 화면 비율, 편집 도구, 원본 자산 사용 조건을 확인한다. 작업 폴더의 설정과 기존 문서 색을 읽는다.
2. **참고 디자인 분석**: 전체 축소판과 대표 페이지를 보고 고정할 규칙과 바꿀 영역을 기록한다. `페이지 | 시각적 초점 | 주/보조 영역 | 자산 | 밀도 | 편집 방식` 표를 만든다. 내용 재작성 계획으로 바꾸지 않는다.
3. **팔레트 결정**: 명시·저장 선호가 없으면 `--topic`과 선별 조합을 사용한다. 키워드 선택 결과가 주제와 맞는지 확인한다. 본문 잉크, 보조 글자, 바탕, 선, 강조, 비교 그룹 색을 구분한다.
4. **원본 제작**: 발표는 PPTX 경로를 우선한다. [시각 예제](examples/visual-analysis.json)를 실제 읽어 차트·표·도식 개체 사용법을 참고하되, 7개 레이아웃을 기계적으로 채우지 않는다. HTML 경로가 필요한 문서는 아래 명령을 사용한다.
5. **구조 시안**: 디자인 개선 요청에는 같은 표지·대표 본문·마무리 세 페이지로 A/B를 비교한다. 내용과 자산은 같게 두고 주영역 비율, 시각자료 배치, 밀도를 달리한다. 색만 바꾼 갤러리로 대신하지 않는다. 사용자가 선택을 요청한 경우에만 기다린다.
6. **출력과 자동 검사**: 오류를 고치고 경고를 확인한다. PPTX와 HTML의 검증 경로를 혼동하지 않는다. 이미지 안 글자는 별도 판독한다.
7. **전체 시각 검수**: 전 페이지 축소판에서 일관성과 밀도 변화를, 개별 이미지에서 축·범례·숫자·정렬·겹침을 확인한다. 참고 PDF와 대응 페이지를 같은 크기로 비교한다. 수정 후 해당 페이지와 전체 흐름을 다시 확인한다.
8. **편집 검수와 전달**: 실제 PPTX의 텍스트·차트 데이터·표 셀 수정 및 PDF 재출력 경로를 확인한다. 확인한 앱과 미검증 앱을 구분한다. PDF/PPTX 링크, 페이지 수, 선택 팔레트, 검수 결과, 이미지로 남은 요소의 편집 범위를 전달한다.

## 디자인 축과 CLI

| 축 | 옵션 | 값 |
|---|---|---|
| 스타일 | `--style` | swiss, editorial, bold, minimal, tech, academic, soft, classic, split |
| 선별 팔레트 | `--palette` | scientific, technology, business, nature, education, neutral |
| 기존 색조 | `--palette` | indigo, navy, terracotta, forest, plum, mono, graphite, crimson, teal, sand |
| 주제 기반 선택 | `--topic` | 주제를 설명하는 문자열 |
| 폰트 | `--font` | auto, sans, serif, serif-all, mono |
| 밀도 | `--density` | normal, compact, airy |
| 모서리 | `--radius` | auto, sharp, soft, round |
| 포인트색 | `--accent` | #RRGGBB / none |

기본 폰트는 Pretendard다. 명조체는 명시 요청이 있을 때만 고운바탕으로 적용한다. 스타일만 바꾸라는 요청이면 색·내용을 유지한다. `pdfdesign.py options`로 실제 옵션을 확인한다.

```bash
python3 SKILL_DIR/scripts/pdfdesign.py pptx SKILL_DIR/examples/visual-analysis.json ./out/example.pptx --topic "물류 운영 분석"
python3 SKILL_DIR/scripts/pdfdesign.py init report ./out/report.html --style swiss --topic "과학 데이터 분석"
python3 SKILL_DIR/scripts/pdfdesign.py init talk ./out/talk.html --palette scientific
python3 SKILL_DIR/scripts/pdfdesign.py set ./out/report.html --style editorial
python3 SKILL_DIR/scripts/pdfdesign.py set ./out/report.html --save
python3 SKILL_DIR/scripts/pdfdesign.py gallery ./out/report.html --styles all
python3 SKILL_DIR/scripts/pdfdesign.py render ./out/report.html --preview
python3 SKILL_DIR/scripts/pdfdesign.py check ./out/talk.html --strict
```

HTML 템플릿: `report`는 A4 보고서, `onepager`는 A4 한 장, `deck`은 짧은 발표, `talk`는 수식·그림을 포함한 발표다. HTML 디자인은 속성과 토큰으로 분리한다. 공통 클래스는 `references/components.md`, 스타일 추가는 `references/extending.md`를 따른다. 생성된 `pdf-design.css`는 직접 수정하지 않는다. 문서 전용 CSS는 HTML의 `<style>`에 둔다.

## 요구 사항

HTML 출력은 Chrome/Chromium/Edge, 미리보기는 Poppler가 필요하다. Chrome을 직접 호출하지 말고 CLI를 사용한다. PPTX의 설치·PDF 출력 조건은 `editable-presentations.md`를 따른다. 웹폰트·KaTeX를 가져올 수 없는 환경에서는 대체 폰트·수식 렌더 상태를 확인한다. 실제 데이터 차트에 이미지 생성 모델을 사용하지 않는다. 가상 예제에는 예시 데이터임을 표시한다.
