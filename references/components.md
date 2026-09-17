# 공통 클래스

모든 스타일에서 같은 마크업을 쓴다. 모양은 스타일이 결정한다.

## 구조
| 클래스 | 용도 | 비고 |
|---|---|---|
| `.cover` > `.cover-top`, `.cover-body`(`.eyebrow`, `.cover-title`, `.cover-sub`), `dl.cover-foot` | 보고서 표지 | 표지는 쪽번호·러닝 헤더가 숨겨진다 |
| `.sheet` > `aside.side` + `main.main-col` | 원페이저 2단 | `.name`, `.role`, `.side h3`, `.entry` 계열과 함께 |
| `body.deck` > `section.slide` | 16:9 슬라이드 | 첫 장은 `.slide.hero`, 하단은 `.slide-foot` |
| `.page-break` | 새 페이지에서 시작 | |
| `.grid-2`, `.grid-3`, `.row`, `.stack`, `.center` | 레이아웃 | `.center`는 슬라이드에서 세로 중앙 |

## 텍스트
| 클래스 | 용도 |
|---|---|
| `.eyebrow` | 제목 위 작은 라벨 |
| `.lead` | 요약 문단 |
| `h2 > .sec-num` | 장 번호. 예: `<h2><span class="sec-num">01</span>배경</h2>` |
| `.slide-title`, `.big-number` (`.muted`) | 슬라이드 제목, 큰 수치 |
| `.muted`, `.small` | 보조 텍스트 |

## 컴포넌트
| 클래스 | 용도 |
|---|---|
| `.kpis` > `.kpi` > `.kpi-label`, `.kpi-value`, `.kpi-delta.up/.down` | 지표 묶음. 변화 표시는 ▲▼ 기호와 함께 쓴다 |
| `.callout` > `.callout-title` | 강조 박스. 페이지당 1개 |
| `.card`, `.card.soft`, `.card.hl` | 카드. `hl`은 포인트색으로 채운 강조 카드 |
| `.tag` | 기술 스택 같은 짧은 태그 |
| `.badge` (`.good` `.warn` `.bad` `.accent`) | 상태·등급 표시 |
| `.bar > span[style="width:NN%"]` (`.warn` `.bad`) | 진행 막대 |
| `ol.toc > li > .sec-num + span` | 목차 |
| `.flow`(카드 → `.arrow` → 카드), `.compare` | 슬라이드용 흐름도·전후 비교 |
| `table` + `thead` + `caption` + `td.num` | 표. 캡션은 표 위에 표시된다 |
| `figure > svg.chart + figcaption` | 차트. SVG 안에서 `.grid` `.series` `.dot` `.target` `.marker` `.strong` 사용 |

## SVG 차트 예
```html
<svg class="chart" viewBox="0 0 480 170" width="100%">
  <g class="grid"><line x1="36" y1="20" x2="470" y2="20"/></g>
  <line class="target" x1="36" y1="92" x2="470" y2="92"/>
  <polyline class="series" points="56,44 106,40 156,90"/>
  <g class="dot"><circle cx="156" cy="90" r="3"/></g>
  <text x="56" y="158" text-anchor="middle">1주</text>
</svg>
```
좌표는 viewBox 기준으로 직접 계산한다. 색을 SVG 속성에 HEX로 쓰지 않는다.
