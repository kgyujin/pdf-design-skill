# 발표 자료 모드 (슬라이드 PDF + 대본 DOCX)

논문·보고서 같은 원본 자료로 발표용 슬라이드와 발표 대본을 만들 때의 절차다.
사용자가 준 프롬프트가 없으면 `prompts/presentation.md`의 지침을 기본 요구사항으로 삼는다.

## 1. 준비
1. 입력을 확인한다: 원본 자료, 참고 발표 자료, 발표 시간, 목표 슬라이드 수, 청중, 언어, 디자인.
   - 빠진 항목은 원본 자료의 성격에 맞게 정하고, 무엇으로 정했는지 보고한다.
   - 슬라이드 수가 없으면 발표 시간 1.5~2분당 1장을 기준으로 한다.
2. 원본을 끝까지 읽고 다음 목록을 먼저 만든다(작업 메모). 이 목록이 누락 검수의 기준이 된다.
   - 핵심 주장과 결론, 조건
   - Figure / Table / 수식 / Algorithm / 사례 번호와 쪽
   - 결과 수치(비교 대상·조건·단위 포함), 한계와 반례
3. 슬라이드 제목만으로 스토리라인을 먼저 쓴다(결론형 문장). 슬라이드마다 레이아웃을 정한다.

## 2. Figure 추출
원본이 PDF이면 Poppler로 추출한다. 결과는 작업 폴더의 `figures/`에 둔다.
```bash
pdfimages -list source.pdf                          # 내장 이미지 목록(쪽·크기)
pdfimages -png -f 5 -l 5 source.pdf figures/p5      # 5쪽의 내장 이미지 추출
pdftoppm -png -r 300 -f 5 -l 5 source.pdf figures/p5-page   # 벡터 Figure는 쪽 전체를 300dpi로 렌더링
```
- 벡터 Figure는 쪽 전체를 렌더링한 뒤 필요한 영역만 잘라낸다. 이때 축·범례·단위·캡션이 잘리지 않게 여유를 둔다.
  잘라내기는 `pdftoppm -x -y -W -H`(픽셀 좌표)로 한다. 좌표는 렌더링한 쪽 이미지를 열어 확인한다.
- 추출한 이미지는 반드시 열어서 내용이 맞는지 확인한다. 파일 이름에 원본 Figure 번호를 넣는다(예: `fig3_p5.png`).
- HTML에서는 상대경로로 참조한다: `<div class="fig-frame"><img src="figures/fig3_p5.png" alt="..."></div>`.

## 3. 작성
```bash
python3 SKILL_DIR/scripts/pdfdesign.py init talk ./presentation/talk.html                  # academic + graphite
python3 SKILL_DIR/scripts/pdfdesign.py init talk ./presentation/talk.html --style bold --palette navy
```
- 템플릿에는 레이아웃별 예시 슬라이드가 들어 있다. 필요한 것을 복제해 쓰고, 쓰지 않는 예시는 지운다.
- 구조: `section.slide > header.slide-head + div.slide-body.l-* + footer.slide-foot + aside.notes`
- 레이아웃과 클래스는 `components.md`의 "슬라이드" 절을 따른다.
- 수식은 KaTeX 문법이다. 블록 수식은 `$$ ... $$`, 인라인 수식은 `\( ... \)`. 노트 안의 수식은 일반 텍스트로 쓴다(DOCX로 옮겨지므로).
- 제작자 해석은 `.interp`, 다시 그린 도식은 `.fig-label`("adapted from …" / "simplified view")로 구분한다.
- 부록은 `section.slide.appendix`로 표시한다.
- 노트 작성법은 `prompts/presentation.md` 5절을 따른다. 읽을 대본은 반드시 `div.talk` 안의 `p`로 쓴다.

## 4. 검수 순서
```bash
python3 SKILL_DIR/scripts/pdfdesign.py render talk.html --preview --expect-pages N
python3 SKILL_DIR/scripts/pdfdesign.py check talk.html          # 오류 0건이 될 때까지 수정
python3 SKILL_DIR/scripts/pdfdesign.py script talk.html         # talk_script.docx + 발표 시간 추정
```
1. `check` 오류는 모두 고친다. 경고는 원인을 확인하고, 의도한 것이면 보고에 적는다.
2. 미리보기 PNG를 모든 슬라이드 열어 `check`가 못 잡는 문제를 본다: SVG·이미지 안의 겹침, 핀 위치, 흐림, 의미 왜곡.
3. 1단계에서 만든 목록과 대조해 빠진 Figure·수식·Algorithm·결과가 없는지 확인한다. 슬라이드 수치를 원본과 한 번 더 대조한다.
4. `script` 결과의 예상 시간이 목표와 ±15% 넘게 차이 나면 대본 분량을 조정하고 다시 실행한다.
5. DOCX가 열리는지 확인한다. macOS는 `textutil -convert txt -stdout talk_script.docx | head`, python-docx가 있으면 `python3 -c "import docx; docx.Document('talk_script.docx')"`.

## 5. 디자인 바꾸기
발표 자료도 보고서와 같은 디자인 축을 쓴다. 기본값은 흑백 미니멀(`academic` + `graphite`)이다.
```bash
python3 SKILL_DIR/scripts/pdfdesign.py gallery talk.html --styles all --pages 3
python3 SKILL_DIR/scripts/pdfdesign.py set talk.html --style soft          # 색조 유지
```
디자인을 바꾼 뒤에는 `check`를 다시 실행한다. 스타일마다 여백과 글자 굵기가 달라 넘침이 새로 생길 수 있다.

## 6. 보고 형식
- PDF, DOCX, HTML 경로
- 슬라이드 수(본편/부록), 예상 발표 시간과 목표 시간
- 원본에서 가져온 주요 Figure·표(번호)
- 검수 결과: `check` 오류·경고 건수, 직접 확인한 항목, 확인하지 못한 항목(예: 오프라인이라 수식 미확인)
