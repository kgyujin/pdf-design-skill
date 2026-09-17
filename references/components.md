# 공통 클래스

모든 스타일에서 같은 마크업을 쓴다. 모양은 스타일이 결정한다.

## 구조
| 클래스 | 용도 | 비고 |
|---|---|---|
| `.cover` > `.cover-top`, `.cover-body`(`.eyebrow`, `.cover-title`, `.cover-sub`), `dl.cover-foot` | 보고서 표지 | 표지는 쪽번호·러닝 헤더가 숨겨진다 |
| `.sheet` > `aside.side` + `main.main-col` | 원페이저 2단 | `.name`, `.role`, `.side h3`, `.entry` 계열과 함께 |
| `body.deck` > `section.slide` | 16:9 슬라이드 | 아래 "슬라이드" 절 참고 |
| `.page-break` | 새 페이지에서 시작 | |
| `.grid-2`, `.grid-3`, `.row`, `.stack`, `.center` | 레이아웃 | `.center`는 슬라이드에서 세로 중앙 |

## 텍스트
| 클래스 | 용도 |
|---|---|
| `.eyebrow` | 제목 위 작은 라벨. 표지·히어로에서 문서 종류나 행사명을 밝힐 때만 쓴다(모든 제목 위에 반복하지 않는다) |
| `.lead` | 요약 문단 |
| `h2 > .sec-num` | 장 번호. 예: `<h2><span class="sec-num">1</span>배경</h2>` (0을 붙이지 않는다) |
| `.slide-title`, `.big-number` (`.muted`) | 슬라이드 제목, 큰 수치 |
| `.muted`, `.small` | 보조 텍스트 |

## 컴포넌트
| 클래스 | 용도 |
|---|---|
| `.kpis` > `.kpi` > `.kpi-label`, `.kpi-value`, `.kpi-delta.up/.down` | 지표 묶음. 변화 표시는 ▲▼ 기호와 함께 쓴다 |
| `.callout` > `.callout-title` | 강조 박스. 페이지당 1개 |
| `.card`, `.card.soft`, `.card.hl` | 카드. `hl`은 먹색 테두리로 구분한 강조 카드. 같은 카드 3개를 나열하기 전에 번호 목록·표가 맞는지 먼저 본다 |
| `.tag` | 기술 스택 같은 짧은 태그(테두리만 있는 작은 사각형) |
| `.badge` (`.good` `.warn` `.bad` `.accent`) | 상태·등급 표시. 표 안의 상태 값에만 쓴다 |
| `.bar > span[style="width:NN%"]` (`.warn` `.bad`) | 진행 막대 |
| `ol.toc > li > .sec-num + span` | 목차 |
| `.flow`(카드 → `.arrow` → 카드), `.compare`, `.big-number` | `deck`용 간단한 흐름도·전후 비교·큰 수치 |
| `table` + `thead` + `caption` + `td.num` | 표. 캡션은 표 위에 표시된다 |
| `figure > svg.chart + figcaption` | 차트. SVG 안에서 `.grid` `.series` `.dot` `.target` `.marker` `.strong` 사용 |

## 슬라이드 (`deck`, `talk`)

```html
<section class="slide">                      <!-- .hero(표지) .section(파트 구분) .appendix(부록) -->
  <header class="slide-head">
    <div class="slide-title">결론을 담은 제목</div>
    <p class="slide-msg">핵심 메시지 한 문장(선택)</p>
  </header>
  <div class="slide-body l-points"> … </div>
  <footer class="slide-foot"><span class="source">Source: 원본, Fig. 3 (p. 5)</span><span class="page"></span></footer>
  <aside class="notes">                     <!-- PDF에는 안 보이고 script 명령이 DOCX로 옮긴다 -->
    <h4>화면에서 먼저 가리킬 부분</h4><p>…</p>
    <div class="talk"><p>실제로 읽을 대본</p></div>
  </aside>
</section>
```

| 레이아웃(`.slide-body`에 추가) | 내용 마크업 | 용도 |
|---|---|---|
| `l-points` (`two-col`) | `ol.points > li > strong + 설명` | 핵심 포인트 3~5개 |
| `l-figure` (`wide` `flip`) | `figure.fig > .fig-frame > img/svg` + `.pin` + `figcaption`, 옆에 `ol.callouts` | Figure 중심. `.pin`은 `style="left:%; top:%"`로 위치 지정 |
| `l-equation` | `.equation` (`$$…$$`) + `dl.symbols > div > dt + dd` 또는 `ol.derive > li + .why` | 수식·기호 설명·단계별 계산 |
| `l-steps` | `ol.steps > li > strong + 설명` (`.vertical`, 조건식은 `.cond`) | 절차·Algorithm. 번호와 룰로 순서를 보이며 화살표를 넣지 않는다 |
| `l-compare` | `.col`(선택안은 `.col.pick`) `> h3 + ul`, 마지막에 `.verdict` | 비교와 결론 |
| `l-table` | `table` + `caption`, 강조 행 `tr.hl`, 강조 칸 `td.hl` | 표 |
| `l-split` | `.text` + 시각자료나 `.interp` | 글과 시각자료 나란히 |

| 보조 클래스 | 용도 |
|---|---|
| `.fig-label` | Figure 왼쪽 위 표시: "adapted from …", "simplified view" |
| `.look` | "Look at:"(한국어 문서는 "볼 곳:")으로 시작하는 한 줄 안내 |
| `.interp` | 제작자 해석(점선 박스, "Interpretation"/"제작자 해석" 라벨). 원본 주장과 구분 |
| `.sec-big` | 섹션 구분 슬라이드의 큰 번호 |
| `.meta` | 표지 슬라이드의 발표자·소속·원본 정보 |

수식(KaTeX)은 `talk` 템플릿의 `<head>`에 포함돼 있다. 다른 템플릿에서 수식을 쓰려면 그 세 줄(`katex.min.css`, `katex.min.js`, `auto-render.min.js`)을 복사한다.

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
