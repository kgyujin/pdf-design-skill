# 발표 자료의 화면 변화 예시

[presentation-rhythm.html](presentation-rhythm.html)은 가상 업무 사례 4쪽이다. 2조·3조 참고 자료에서 확인한 큰 메시지, 의미 있는 비교 색면, 근거와 조건의 정렬을 일반화했다. 기존 PDF의 문구·수치·분자 그림·페이지를 복제하지 않았다. 실제 분석이나 성능 결과로 사용하지 않는다.

| 쪽 | 역할 | 재사용할 요소 |
|---|---|---|
| 1 | 밝은 표지 | 큰 제목과 발표 정보, 넓은 여백 |
| 2 | 비교 | 같은 행끼리 정렬된 두 색면, 차이가 있는 부분에 집중 |
| 3 | 근거 | 큰 비교 그림과 단위, 분모가 있는 작은 표 |
| 4 | 결론 | 발견·행동·판단 기준의 연결, 우선 행 강조 |

## 실행

실제 과제에서 시작점으로 쓰려면 HTML과 전용 CSS를 작업 폴더에 함께 복사한다. 논문·수식 발표의 기존 talk 템플릿을 대체하도록 강제하지 않는다.

```sh
mkdir -p /tmp/rhythm-reuse
cp examples/presentation-rhythm.html /tmp/rhythm-reuse/talk.html
cp examples/presentation-rhythm.css /tmp/rhythm-reuse/presentation-rhythm.css
python3 scripts/pdfdesign.py render /tmp/rhythm-reuse/talk.html --preview --expect-pages 4
```

저장소 루트에서 예제를 직접 확인하려면 다음을 실행한다. `render`가 예제 폴더에 공통 `pdf-design.css`를 생성하며 전용 CSS는 상대경로로 연결된다.

```sh
python3 scripts/pdfdesign.py render examples/presentation-rhythm.html --preview --expect-pages 4
python3 scripts/pdfdesign.py check examples/presentation-rhythm.html
```

HTML, `presentation-rhythm.css`, 생성된 `pdf-design.css`를 함께 복사하면 브라우저에서 열 수 있다. 원본 스타일 토큰을 유지하므로 색조 변경도 가능하다. 생성 CSS를 직접 고치지 않는다.

## 같은 내용의 구조 A/B 비교

이 예제는 완성 A/B 쌍이 아니라 재사용 가능한 네 레이아웃이다. 실제 작업에서는 표지·핵심 증거·결론의 같은 세 페이지로 두 방향을 만든다.

- A: 표지는 큰 제목과 넓은 여백, 본문은 넓은 색면과 실제 사례 중심
- B: 표와 차트 조합, 조건과 결과 정렬, 큰 단일 근거 중심

내용·수치·원본 PNG·화면 크기는 같게 유지한다. 팔레트만 바꾸지 않는다. 사용자가 시안 선택을 요청한 경우에만 선택을 기다린다.

## 원본 그림 사용과 검수

그림 목록에 파일, 출처, 본편·부록·미사용, 배치 페이지, 사유를 기록한다. 모든 원본 그림을 넣지 않아도 되지만 선택한 핵심 근거를 빠뜨리면 안 된다. 제공 PNG 재사용 조건이 있으면 다시 그리지 않는다.

전체 축소판은 흐름 확인용이다. 이후 모든 개별 페이지를 실제 표시 크기에서 열어 축·범례·숫자를 판독한다. PNG 내부 작은 글씨는 자동 검사 통과만으로 확인됐다고 기록하지 않는다. 같은 배치가 세 장 이상 이어질 때는 역할상 필요한지 검토하고, 유지 또는 변경 이유를 남긴다.
