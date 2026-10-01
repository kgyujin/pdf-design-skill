# pdf-design

Claude Code와 Codex에서 함께 쓰는 PDF 디자인 스킬입니다. 발표 자료는 **PowerPoint에서 편집할 PPTX와 같은 원본에서 출력한 PDF**를 제공합니다. 보고서·원페이저는 HTML/CSS에서 PDF로 출력합니다.

참고 PDF 전체의 서체, 제목 위계, 정렬, 여백, 정보 밀도, 색의 의미, 차트·표·이미지 배치를 분석합니다. 도형 몇 개를 추가하거나 카드 색만 바꾸는 방식으로 디자인 개선을 대신하지 않습니다. 디자인만 요청하면 원문의 글과 수치를 유지합니다.

## 발표 디자인 기본값

- 표지는 제목·부제·팀/발표자·날짜·선택적 주제 이미지만 담습니다. KPI·결론·발표 목차·설명 본문을 자동으로 넣지 않습니다.
- ‘출처’ 라벨이나 출처 푸터, 참고자료 페이지를 요청 없이 추가하지 않습니다. 원본 자산은 별도 제작 기록에서 추적합니다.
- 제목·여백·서체는 일관되게 유지하고 본문은 큰 차트, 정렬된 표, 대상 이미지, 공통 축 비교 등 자산에 맞게 설계합니다.
- 텍스트·표·도식·지원 차트는 네이티브 개체로 만듭니다. 전체 슬라이드를 이미지로 넣은 PPTX를 편집용 원본으로 제공하지 않습니다.
- 전체 축소판과 모든 개별 페이지를 확인합니다. 자동 검사 통과와 시각적 완성도를 구분합니다.

[전체 시각 설계](references/visual-storytelling.md)는 2조와 3조 참고 PDF의 전 페이지 디자인 관찰을 일반화한 지침입니다. [편집용 시각 예제](examples/visual-analysis.md)는 가상 데이터로 만든 7쪽 예제입니다. 참고 자료의 문구·수치·이미지를 분석 결과로 재사용하지 않습니다.

## 주제에 맞는 팔레트

명시 설정 > 저장한 선호 > 주제 자동 선택 > neutral 순으로 적용합니다. 기존 문서의 색 유지 요청이 우선하며, 키워드가 선택한 팔레트의 실제 적합성도 확인합니다. [팔레트 지침](references/palettes.md)에 역할별 색과 적용 기준을 정리했습니다.

| 팔레트 | 용도 |
|---|---|
| scientific | 과학·실험·데이터 분석 |
| technology | 기술·소프트웨어·시스템 |
| business | 사업·운영·재무 |
| nature | 환경·생태·지속가능성 |
| education | 교육·학습·워크숍 |
| neutral | 주제 미지정·범용 |

기존 색조 indigo, navy, terracotta, forest, plum, mono, graphite, crimson, teal, sand도 명시적으로 선택할 수 있습니다. 색은 ink, muted, paper, line, accent, secondary, accentSoft 역할로 관리합니다.

## 빠른 시작

```bash
git clone https://github.com/kgyujin/pdf-design-skill.git ~/workspace/pdf-design-skill
~/workspace/pdf-design-skill/install.sh
```

Codex와 Claude의 스킬 경로에 같은 저장소를 가리키는 심볼릭 링크가 만들어집니다. `git pull`로 둘 다 갱신되며 `./install.sh --uninstall`로 링크를 제거합니다.

```bash
K=~/workspace/pdf-design-skill/scripts/pdfdesign.py
python3 $K pptx examples/visual-analysis.json ./out/example.pptx --topic "물류 운영 분석"
python3 $K init report ./out/report.html --topic "과학 데이터 분석"
python3 $K init talk ./out/talk.html --palette scientific
python3 $K render ./out/talk.html --preview
python3 $K check ./out/talk.html --strict
```

PPTX 생성·PDF 내보내기·편집 범위는 [편집 안내](references/editable-presentations.md)를 따릅니다. 사용자가 PowerPoint에서 수정한 PPTX를 정본으로 유지합니다. 이전 JSON을 다시 생성하면 수동 편집을 덮어쓸 수 있습니다.

## 스타일과 템플릿

| 축 | 옵션 |
|---|---|
| 스타일 | swiss, editorial, bold, minimal, tech, academic, soft, classic, split |
| 폰트 | auto, sans, serif, serif-all, mono |
| 밀도 | normal, compact, airy |
| 모서리 | auto, sharp, soft, round |
| 포인트색 | `--accent #RRGGBB` |

기본 폰트는 Pretendard입니다. 명조체는 명시 요청이 있을 때만 고운바탕으로 적용합니다. `report`는 A4 보고서, `onepager`는 A4 한 장, `deck`은 짧은 발표, `talk`는 그림·수식·표를 포함한 발표 템플릿입니다.

```bash
python3 $K options
python3 $K set ./out/report.html --style editorial
python3 $K set ./out/report.html --save
python3 $K gallery ./out/report.html --styles all
```

스타일만 바꾸면 색과 내용을 유지합니다. `--save`는 폴더의 `pdf-design.json`에 선호를 저장합니다. 디자인 개선 시에는 같은 대표 페이지의 구조 A/B도 비교합니다. 팔레트만 바꾼 갤러리가 구조 시안을 대신하지 않습니다.

## 검수와 실행 환경

HTML PDF에는 Chrome/Chromium/Edge, 미리보기에는 Poppler가 필요합니다. PPTX 생성에는 [편집 안내](references/editable-presentations.md)의 별도 의존성이 필요합니다. 글꼴·수식 리소스의 다운로드가 불가능하면 대체 폰트와 수식 출력 상태를 확인합니다.

`check`는 넘침, 겹침, 작은 글씨, 깨진 이미지, 수식 문제 등을 확인합니다. 이미지 안의 축·범례·수치는 직접 읽어야 합니다. 편집 원본에서 텍스트·표 셀·차트 데이터를 바꾸고 PDF로 재출력할 수 있는지 확인합니다. PowerPoint를 직접 실행하지 않았다면 그 점을 검수 기록에 남깁니다.

```bash
python3 -m compileall -q scripts tests
python3 -m unittest discover -s tests
```

Chrome과 Poppler가 없는 환경에서는 렌더 테스트가 건너뛰어질 수 있으므로 실행 결과를 확인해야 합니다.

## 지침과 예제

- [발표 제작 절차](references/presentation.md)
- [요청 프롬프트](prompts/presentation.md)
- [전체 시각 설계](references/visual-storytelling.md)
- [디자인 규칙](references/design-rules.md)
- [반복 검토 기준](references/anti-ai-design.md)
- [편집용 시각 예제](examples/visual-analysis.md)
- [확장 방법](references/extending.md)

`init`·`set`·`render`가 생성하는 `pdf-design.css`는 직접 수정하지 않습니다. 문서 전용 스타일은 HTML의 `<style>`에 작성합니다.
