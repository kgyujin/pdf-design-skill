# 선별한 발표용 컬러 조합

밝은 바탕·진한 본문·제한된 강조색이라는 2·3조의 전체 시각 체계를 기준으로 고른 조합이다. 참고 자료의 색을 주제와 무관하게 그대로 반복하지 않는다. 표지의 큰 면을 어둡게 칠하거나 모든 상자·그래프를 강조색으로 채우는 기본값은 두지 않는다.

| 팔레트 | 주제 | 강조 | 비교색 | 본문 | 옅은 바탕 |
|---|---|---|---|---|---|
| scientific | 연구·의료·화학 | #B63E4C | #246D82 | #20282D | #F3F5F5 |
| technology | 기술·소프트웨어·AI | #315CBD | #0B766E | #202735 | #F1F4F8 |
| business | 비즈니스·운영·금융 | #225CA8 | #A75420 | #242B32 | #F5F4F1 |
| nature | 환경·에너지 | #2D6E52 | #936324 | #23332C | #F2F5F0 |
| education | 교육·문화·인문 | #744885 | #326D88 | #302936 | #F6F3F6 |
| neutral | 일반·주제 미지정 | #3F6174 | #94553E | #252B2C | #F2F3F1 |

색 값·주제 키워드의 정본은 `assets/presentation-palettes.json`이다. 대비 테스트는 본문/보조 글자와 밝은 바탕, 강조색 위 흰 글자 조합을 검사한다. 색만으로 그룹을 구분하지 말고 범주 이름이나 선 모양을 함께 쓴다.

## 자동 선택

새 문서는 **사용자 명시 > 저장된 팔레트 > 주제 키워드 > neutral** 순서로 선택한다. 기존 문서의 RGB 색은 자동 교체하지 않는다. PPTX 장면에 명시한 palette는 제작자의 기존 선택으로 존중한다. 키워드가 여러 주제에 걸치면 매칭 수가 많은 조합을 선택하고, 동점은 목록 순서로 결정한다. 결과는 로그에 표시되므로 제작자가 주제·비교 목적에 맞는지 확인한다.

```bash
python3 SKILL_DIR/scripts/pdfdesign.py init talk ./out/research.html --topic "분자 독성 분석"
python3 SKILL_DIR/scripts/pdfdesign.py pptx ./scene.json ./out/scene.pptx --topic "클라우드 운영"  # technology
python3 SKILL_DIR/scripts/pdfdesign.py pptx ./scene.json ./out/scene.pptx --palette nature    # 명시 우선
```

PPTX는 `--topic`이 없으면 JSON의 topic, 다음으로 title을 사용한다. HTML init은 주제 본문이 아직 없으므로 `--topic`을 제공한다. 주제가 없는 새 발표는 neutral을 사용한다. `set`과 `render`는 기존 색을 보존하며 주제로 재분류하지 않는다.

## 색 역할을 써야 자동 적용된다

HTML은 `var(--ink)`, `var(--accent)`, `var(--secondary)`, `var(--surface-2)` 등을 쓴다. PPTX JSON은 색 필드에 다음 역할을 쓴다.

- `@ink`, `@muted`: 제목·본문, 보조 글자
- `@paper`, `@white`, `@line`: 옅은 면, 흰 바탕, 구분선
- `@accent`, `@secondary`: 주요 강조, 비교 그룹
- `@accentSoft`, `@onAccent`: 옅은 강조 면, 강조색 위 글자
- `@accent/20`: 강조색 20%와 흰색 80%를 섞은 색. 단계형 차트의 색상을 같은 조합에 맞춘다.

새 PPTX를 만들 때 제목·본문·표·그래프에 이 역할을 함께 적용한다. 기존 자산의 직접 RGB 값은 그대로 유지한다. 그래프에서 색이 집단을 뜻하면 다른 페이지에서도 같은 뜻을 유지한다. 특정 값 강조에 같은 색을 쓸 경우 집단 색과 혼동되지 않도록 확인한다.

표지는 제목·부제·기본 정보와 필요할 때 주제 이미지로 구성한다. 팔레트 시안표, 핵심 지표, 결론이나 목차를 표지에 자동 삽입하지 않는다.
