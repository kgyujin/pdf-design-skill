"""
작성자: Git 이력 참조
작성목적: 외부 패키지 없이(표준 라이브러리만) 발표 대본용 DOCX를 만든다.
작성일: 2026-09-17

주요 입력: 제목·문단·글머리표·표·PNG 이미지를 순서대로 추가하는 호출
주요 출력: Word·Pages·LibreOffice에서 열리는 .docx (OOXML, A4)
주의사항:
  - 필요한 최소 OOXML 부품만 쓴다: [Content_Types], rels, document, styles, core/app props, media.
  - 텍스트는 반드시 xml_escape 를 거친다. 제어 문자는 Word가 파일 손상으로 판단하므로 제거한다.
  - 길이 단위: 쪽 설정은 twip(1/1440 inch), 이미지는 EMU(1cm = 360000), 글자 크기는 half-point.
변경사항 내역:
- 2026-09-17 | 최초 작성 | 제목/문단/글머리표/대본 문단/표/이미지/쪽 나눔
"""

from __future__ import annotations

import re
import struct
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

EMU_PER_CM = 360000
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
BODY_FONT = "Pretendard"
EAST_ASIA_FALLBACK_FONT = "Apple SD Gothic Neo"

NAMESPACES = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'
)

# (텍스트, 굵게 여부) 목록. 한 문단 안에서 굵기가 섞일 때 쓴다.
Runs = list[tuple[str, bool]]


def xml_escape(text: str) -> str:
    return escape(CONTROL_CHARS.sub("", text), {'"': "&quot;"})


def png_dimensions(png_path: Path) -> tuple[int, int]:
    with png_path.open("rb") as png_file:
        header = png_file.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"PNG 파일이 아닙니다: {png_path}")
    return struct.unpack(">II", header[16:24])


def _run_xml(text: str, is_bold: bool = False, color: str | None = None, size_half_pt: int | None = None) -> str:
    properties = ""
    if is_bold:
        properties += "<w:b/>"
    if color:
        properties += f'<w:color w:val="{color}"/>'
    if size_half_pt:
        properties += f'<w:sz w:val="{size_half_pt}"/>'
    run_properties = f"<w:rPr>{properties}</w:rPr>" if properties else ""
    # 줄바꿈은 <w:br/>로 변환한다.
    pieces = text.split("\n")
    body = '<w:br/>'.join(f'<w:t xml:space="preserve">{xml_escape(piece)}</w:t>' for piece in pieces)
    return f"<w:r>{run_properties}{body}</w:r>"


@dataclass
class DocxBuilder:
    title: str
    creator: str = "pdf-design"
    _body: list[str] = field(default_factory=list)
    _images: list[tuple[str, Path]] = field(default_factory=list)

    # ------------------------------------------------------------ 블록

    def heading(self, text: str, level: int = 1) -> None:
        style = "Title" if level == 0 else f"Heading{min(max(level, 1), 3)}"
        self._paragraph(_run_xml(text), style)

    def paragraph(self, runs: Runs | str, style: str | None = None) -> None:
        if isinstance(runs, str):
            runs = [(runs, False)]
        self._paragraph("".join(_run_xml(text, is_bold) for text, is_bold in runs), style)

    def bullet(self, runs: Runs | str, level: int = 0) -> None:
        if isinstance(runs, str):
            runs = [(runs, False)]
        style = "ListBullet" if level == 0 else "ListBullet2"
        marker = "•\t" if level == 0 else "–\t"
        self._paragraph(_run_xml(marker) + "".join(_run_xml(text, is_bold) for text, is_bold in runs), style)

    def caption(self, text: str) -> None:
        self._paragraph(_run_xml(text), "Caption")

    def page_break(self) -> None:
        self._body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def image(self, png_path: Path, width_cm: float) -> None:
        width_px, height_px = png_dimensions(png_path)
        width_emu = int(width_cm * EMU_PER_CM)
        height_emu = int(width_emu * height_px / width_px)
        image_number = len(self._images) + 1
        relation_id = f"rIdImg{image_number}"
        self._images.append((relation_id, png_path))
        drawing = (
            f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{width_emu}" cy="{height_emu}"/>'
            f'<wp:docPr id="{image_number}" name="Slide {image_number}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{image_number}" name="image{image_number}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{relation_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{width_emu}" cy="{height_emu}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            # 흰 배경 슬라이드는 경계가 안 보이므로 옅은 회색 테두리를 둔다(0.5pt = 6350 EMU).
            '<a:ln w="6350"><a:solidFill><a:srgbClr val="BFBFBF"/></a:solidFill></a:ln></pic:spPr></pic:pic>'
            "</a:graphicData></a:graphic></wp:inline></w:drawing></w:r>"
        )
        self._paragraph(drawing, "Figure")

    def table(self, header: list[str], rows: list[list[str]], widths_cm: list[float]) -> None:
        grid = "".join(f'<w:gridCol w:w="{int(width * 567)}"/>' for width in widths_cm)

        def cell(text: str, width_cm: float, is_header: bool) -> str:
            shading = '<w:shd w:val="clear" w:color="auto" w:fill="F1F1F1"/>' if is_header else ""
            return (
                f'<w:tc><w:tcPr><w:tcW w:w="{int(width_cm * 567)}" w:type="dxa"/>{shading}</w:tcPr>'
                f'<w:p><w:pPr><w:pStyle w:val="TableText"/></w:pPr>{_run_xml(text, is_header)}</w:p></w:tc>'
            )

        def row(values: list[str], is_header: bool) -> str:
            header_mark = "<w:trPr><w:tblHeader/></w:trPr>" if is_header else ""
            return f"<w:tr>{header_mark}" + "".join(cell(value, width, is_header) for value, width in zip(values, widths_cm)) + "</w:tr>"

        borders = "".join(f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>' for side in ("top", "left", "bottom", "right", "insideH", "insideV"))
        self._body.append(
            f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders>{borders}</w:tblBorders>'
            '<w:tblCellMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>'
            f"<w:tblGrid>{grid}</w:tblGrid>{row(header, True)}{''.join(row(values, False) for values in rows)}</w:tbl>"
        )
        self._paragraph("", None)

    def _paragraph(self, inner_xml: str, style: str | None) -> None:
        properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        self._body.append(f"<w:p>{properties}{inner_xml}</w:p>")

    # ------------------------------------------------------------ 저장

    def save(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._content_types())
            archive.writestr("_rels/.rels", ROOT_RELS)
            archive.writestr("docProps/core.xml", self._core_properties())
            archive.writestr("docProps/app.xml", APP_PROPERTIES)
            archive.writestr("word/styles.xml", STYLES_XML)
            archive.writestr("word/_rels/document.xml.rels", self._document_rels())
            archive.writestr("word/document.xml", self._document())
            for index, (_, png_path) in enumerate(self._images, start=1):
                archive.write(png_path, f"word/media/image{index}.png")
        return output_path

    def _document(self) -> str:
        section = (
            '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr>'
        )
        return (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {NAMESPACES}>'
            f"<w:body>{''.join(self._body)}{section}</w:body></w:document>"
        )

    def _document_rels(self) -> str:
        relations = ['<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>']
        for index, (relation_id, _) in enumerate(self._images, start=1):
            relations.append(
                f'<Relationship Id="{relation_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image{index}.png"/>'
            )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(relations)
            + "</Relationships>"
        )

    def _content_types(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            "</Types>"
        )

    def _core_properties(self) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f"<dc:title>{xml_escape(self.title)}</dc:title><dc:creator>{xml_escape(self.creator)}</dc:creator>"
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
            "</cp:coreProperties>"
        )


ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
    "</Relationships>"
)

APP_PROPERTIES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
    "<Application>pdf-design</Application></Properties>"
)


def _style(style_id: str, name: str, paragraph: str = "", run: str = "", based_on: str = "Normal") -> str:
    based = f'<w:basedOn w:val="{based_on}"/>' if based_on else ""
    # 기본 문단 스타일 표시가 없으면 pStyle 없는 문단의 스타일을 Word 외 도구가 찾지 못한다.
    default_mark = ' w:default="1"' if style_id == "Normal" else ""
    return (
        f'<w:style w:type="paragraph"{default_mark} w:styleId="{style_id}"><w:name w:val="{name}"/>{based}'
        f'<w:qFormat/><w:pPr>{paragraph}</w:pPr><w:rPr>{run}</w:rPr></w:style>'
    )


STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:docDefaults><w:rPrDefault><w:rPr>"
    f'<w:rFonts w:ascii="{BODY_FONT}" w:hAnsi="{BODY_FONT}" w:eastAsia="{BODY_FONT}" w:cs="{EAST_ASIA_FALLBACK_FONT}"/>'
    '<w:sz w:val="21"/><w:szCs w:val="21"/><w:lang w:val="ko-KR" w:eastAsia="ko-KR"/>'
    "</w:rPr></w:rPrDefault>"
    '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="300" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
    "</w:docDefaults>"
    + _style("Normal", "Normal", based_on="")
    + _style("Title", "Title", '<w:spacing w:after="160"/>', '<w:b/><w:sz w:val="40"/>')
    + _style("Heading1", "heading 1", '<w:keepNext/><w:spacing w:before="120" w:after="160"/><w:outlineLvl w:val="0"/>', '<w:b/><w:sz w:val="32"/>')
    + _style("Heading2", "heading 2", '<w:keepNext/><w:spacing w:before="200" w:after="80"/><w:outlineLvl w:val="1"/>', '<w:b/><w:sz w:val="26"/>')
    + _style("Heading3", "heading 3", '<w:keepNext/><w:spacing w:before="200" w:after="60"/><w:outlineLvl w:val="2"/>', '<w:b/><w:color w:val="2F5D8A"/><w:sz w:val="22"/>')
    + _style("Talk", "Talk Script", '<w:ind w:left="284"/><w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="2F5D8A"/></w:pBdr><w:spacing w:after="100" w:line="340" w:lineRule="auto"/>', '<w:sz w:val="23"/>')
    + _style("ListBullet", "List Bullet", '<w:tabs><w:tab w:val="left" w:pos="360"/></w:tabs><w:ind w:left="360" w:hanging="360"/><w:spacing w:after="60"/>')
    + _style("ListBullet2", "List Bullet 2", '<w:tabs><w:tab w:val="left" w:pos="720"/></w:tabs><w:ind w:left="720" w:hanging="360"/><w:spacing w:after="40"/>')
    + _style("Caption", "Caption", '<w:spacing w:after="80"/>', '<w:color w:val="777777"/><w:sz w:val="17"/>')
    + _style("Figure", "Figure", '<w:spacing w:before="80" w:after="80"/><w:keepNext/>')
    + _style("KeyMessage", "Key Message", '<w:shd w:val="clear" w:color="auto" w:fill="F1F1F1"/><w:spacing w:after="120"/>', '<w:b/>')
    + _style("TableText", "Table Text", '<w:spacing w:after="0"/>', '<w:sz w:val="19"/>')
    + "</w:styles>"
)
