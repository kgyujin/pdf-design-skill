# 편집용 발표 원본과 PDF

사용자가 PowerPoint 편집을 원하면 PPTX를 정본으로 제작하고 같은 파일에서 PDF를 출력한다. PDF를 슬라이드 전체 이미지로 넣은 PPTX, HTML을 수정하라는 안내, 코드 파일만 제공하는 방식은 편집용 원본을 대신하지 못한다.

## 무엇을 편집할 수 있어야 하나

- 제목·본문·주석: 각각 텍스트 개체. 복사·수정·색·크기 변경 가능.
- 표: 네이티브 표. 셀 내용과 행·열 폭 수정 가능.
- 도식: 연결선과 도형·텍스트를 개별 개체로 유지. 이동·색·크기 수정 가능.
- 새 그래프: 지원되는 경우 네이티브 차트와 내장 데이터 통합문서. PowerPoint의 ‘데이터 편집’에서 범주·값을 수정 가능.
- 사진·사용자 지정 PNG: 비율을 유지한 이미지. 교체·크기·위치·자르기는 가능하지만 이미지 내부 글자와 데이터는 편집 불가. 원본 보존 요구가 있으면 그림을 새 차트로 바꾸지 않는다.
- 각 개체가 편집 가능하다는 이유로 편집이 쉬운 것은 아니다. 의미 단위로 이름을 붙이고, 겹친 투명 상자나 글자 단위 분해를 피하며, 차트 라벨을 중복 텍스트로 덮지 않는다.

## 제작 경로

기존 HTML은 HTML→PDF 경로를 유지한다. **임의 HTML→네이티브 PPTX 자동 변환은 지원하지 않는다.** 편집성이 필요한 새 발표는 처음부터 네이티브 요소로 설계한다. 외부 편집 도구가 지정되어 있으면 해당 도구를 우선한다.

내장된 `pptx` 명령은 Python 표준 라이브러리로 구조화된 장면 JSON을 PPTX로 작성한다. 기본 막대·세로막대·꺾은선·도넛, 표, 텍스트, 사각형, 연결선, PNG/JPEG를 지원한다. 복잡한 연구 그래프·수식·그라데이션·애니메이션·기존 PPTX 가져오기를 범용 지원한다고 주장하지 않는다. 지원하지 않는 개체가 필요하면 사용 가능한 전용 발표 도구를 쓰고, 편집성 손실을 감추지 않는다.

```bash
python3 SKILL_DIR/scripts/pdfdesign.py pptx SKILL_DIR/examples/visual-analysis.json ./out/visual-analysis.pptx
```

JSON의 예제는 좌표·스타일·데이터를 재생성하기 위한 제작 원본이다. **사용자가 수정할 파일은 PPTX**다. PPTX를 PowerPoint에서 고친 뒤에는 그 파일에서 PDF를 내보낸다. 이전 JSON을 다시 실행하면 수동 수정이 포함되지 않으므로, 사용자 편집 후 PPTX가 정본이라는 점을 명시한다.

### 최소 입력

```json
{
  "title": "편집용 발표",
  "width": 1280,
  "height": 720,
  "font": "Pretendard",
  "slides": [{
    "title": "비교 결과",
    "elements": [
      {"type":"text", "x":60, "y":60, "w":1160, "h":70,
       "text":"비교 결과", "fontSize":44, "color":"252B2C", "bold":true},
      {"type":"chart", "x":60, "y":180, "w":900, "h":420,
       "chartType":"column", "categories":["A","B"],
       "series":[{"name":"비율", "values":[0.2,0.35], "color":"B64F48"}],
       "min":0, "max":1, "numberFormat":"0%", "dataLabels":true}
    ]
  }]
}
```

좌표·fontSize는 96dpi px, 색은 `#` 없는 6자리 RGB다. 상대비율 0.2를 20%로 표시하려면 `numberFormat: "0%"`를 사용한다. 축 범위와 단위를 명시한다. 사진을 외부 URL로 불러오지 않으며 로컬 PNG/JPEG 경로를 사용한다.

## PDF 출력과 확인

PowerPoint에서는 ‘파일 → 내보내기 → PDF’를 사용한다. macOS에서 로컬 Keynote가 있고 사용자 작업 범위에 앱 실행이 포함되면 다음 경로도 쓸 수 있다.

```bash
python3 SKILL_DIR/scripts/pdfdesign.py render-pptx ./out/visual-analysis.pptx ./out/visual-analysis.pdf --app '/Applications/Keynote.app' --preview
```

앱 경로는 실제 설치 위치를 확인한다. 기존 PDF와 PPTX는 덮어쓰지 않는다. 이 경로는 입력 PPTX를 Keynote에서 열어 PDF로 내보내므로 HTML을 별도로 그려서 비슷한 PDF를 만드는 방식과 다르다. Keynote 출력 검증은 PowerPoint에서의 렌더링·차트 편집 검증을 대신하지 않는다. 앱이 없으면 PDF 자동 출력을 완료했다고 주장하지 않는다.

1. PPTX의 모든 페이지를 대상 앱 또는 이용 가능한 호환 앱에서 열어 렌더한다. 전체 페이지를 확인한다.
2. 대표 제목, 표 셀, 차트 값, 도형 위치를 복사본에서 바꿔 저장·다시 열기를 확인한다. PowerPoint 미설치 시 해당 앱의 직접 검증은 미검증으로 구분한다.
3. 차트 XML과 내장 XLSX의 값·범주·순서가 맞는지 확인한다. 이미지 한 장뿐인 슬라이드를 편집 가능으로 세지 않는다.
4. 새 PDF와 PPTX가 같은 버전인지 파일명과 해시로 기록한다. PDF에서 폰트 대체, 줄바꿈, 축·범례·표·한글 깨짐을 확인한다.
5. 사용자에게 PPTX와 PDF, 짧은 편집 안내를 함께 전달한다. 폰트 설치가 필요한 경우 이름을 알려준다. 폰트 파일은 라이선스가 허용되는 경우에만 함께 배포한다.

HTML용 `check`는 PPTX 검사가 아니다. OOXML 구조 검사도 실제 화면 검수를 대신하지 않는다. 편집성과 시각 정확성은 별도로 검증한다.
