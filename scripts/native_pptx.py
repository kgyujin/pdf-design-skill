"""Editable PowerPoint export using only the Python standard library.

작성자: Git 이력 참조
작성목적: JSON 장면을 네이티브 PowerPoint 문구·도형·표·차트로 저장한다.
작성일: 2026-10-01
주의사항: 좌표와 fontSize는 px(96 dpi). 이미지 자체는 래스터 개체이며,
폰트는 포함하지 않는다. 차트 데이터는 내장 XLSX에 저장한다. 외부 URL은 읽지 않는다.
"""
from __future__ import annotations

import io
import math
import os
import re
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
C = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
PX_EMU = 9525


def _esc(value: object) -> str:
    return escape(str(value), {'"': '&quot;', "'": '&apos;'})


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', value):
        raise ValueError(f'{name}: valid XML text required')
    return value


def _number(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name}: finite number required')
    if positive and value <= 0:
        raise ValueError(f'{name}: positive number required')
    return float(value)


def _color(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'#?[0-9a-fA-F]{6}', value):
        raise ValueError(f'Invalid RGB color: {value!r}')
    return value.lstrip('#').upper()


def _boolean(element: dict, key: str) -> None:
    if key in element and not isinstance(element[key], bool):
        raise ValueError(f'{key}: boolean required')


def _image_path(value: object, base_dir: Path) -> Path:
    value = _text(value, 'image.path')
    if '://' in value or value.startswith('data:'):
        raise ValueError('image.path must be a local PNG or JPEG file')
    path = Path(value).expanduser()
    path = path if path.is_absolute() else base_dir / path
    if not path.is_file():
        raise ValueError(f'Image not found: {path}')
    with path.open('rb') as stream:
        signature = stream.read(24)
    if not (signature.startswith(b'\x89PNG\r\n\x1a\n') or signature.startswith(b'\xff\xd8\xff')):
        raise ValueError(f'Only PNG and JPEG images are supported: {path}')
    return path.resolve()


def validate_scene(scene: dict, base_dir: str | Path | None = None) -> None:
    """Reject invalid geometry/data before creating or replacing a PPTX file."""
    if not isinstance(scene, dict):
        raise ValueError('scene must be an object')
    base = Path(base_dir or '.')
    _text(scene.get('title', 'Presentation'), 'title')
    _text(scene.get('font', 'Pretendard'), 'font')
    width = _number(scene.get('width', 1280), 'width', positive=True)
    height = _number(scene.get('height', 720), 'height', positive=True)
    if not isinstance(scene.get('slides'), list) or not scene['slides']:
        raise ValueError('slides must be a nonempty list')
    for slide_index, slide in enumerate(scene['slides'], 1):
        if not isinstance(slide, dict) or not isinstance(slide.get('elements'), list):
            raise ValueError(f'Slide {slide_index}: elements list required')
        _text(slide.get('title', ''), 'slide.title')
        for element in slide['elements']:
            if not isinstance(element, dict):
                raise ValueError('element must be an object')
            kind = element.get('type')
            if 'name' in element:
                _text(element['name'], 'element.name')
            if kind not in {'text', 'rect', 'line', 'chart', 'image', 'table'}:
                raise ValueError(f'Unsupported element type: {kind!r}')
            for key in ('x', 'y', 'w', 'h'):
                _number(element.get(key), key)
            if element['x'] < 0 or element['y'] < 0 or element['w'] < 0 or element['h'] < 0:
                raise ValueError('Geometry must not be negative')
            if (kind != 'line' and (element['w'] == 0 or element['h'] == 0)) or (element['w'] == element['h'] == 0):
                raise ValueError('Geometry must have a nonzero extent')
            if element['x'] + element['w'] > width + .01 or element['y'] + element['h'] > height + .01:
                raise ValueError(f'Slide {slide_index}: element exceeds slide bounds')
            for key in ('color', 'fill', 'lineColor', 'headerFill', 'headerColor'):
                if key in element:
                    _color(element[key])
            if 'fontSize' in element:
                _number(element['fontSize'], 'fontSize', positive=True)
            for key in ('bold', 'legend', 'dataLabels'):
                _boolean(element, key)
            if kind == 'text':
                _text(element.get('text'), 'text')
                if element.get('align', 'left') not in ('left', 'center', 'right'):
                    raise ValueError('align must be left, center or right')
            elif kind == 'rect' and 'radius' in element:
                _number(element['radius'], 'radius')
                if element['radius'] < 0:
                    raise ValueError('radius must not be negative')
            elif kind == 'line':
                _number(element.get('width', 1), 'line.width', positive=True)
            elif kind == 'image':
                _image_path(element.get('path'), base)
            elif kind == 'table':
                padding = _number(element.get('cellPadding', 16), 'cellPadding')
                if padding < 0:
                    raise ValueError('cellPadding must not be negative')
                rows = element.get('rows')
                if not isinstance(rows, list) or not rows or not isinstance(rows[0], list) or not rows[0]:
                    raise ValueError('table.rows must be a nonempty matrix')
                count = len(rows[0])
                for row in rows:
                    if not isinstance(row, list) or len(row) != count:
                        raise ValueError('table rows must have equal length')
                    for cell in row:
                        _text(cell, 'table cell')
                widths = element.get('columnWidths', [1] * count)
                if not isinstance(widths, list) or len(widths) != count:
                    raise ValueError('columnWidths must match column count')
                for column_width in widths:
                    _number(column_width, 'columnWidth', positive=True)
            elif kind == 'chart':
                if element.get('chartType') not in ('bar', 'column', 'line', 'doughnut'):
                    raise ValueError('Unsupported chartType')
                categories, series = element.get('categories'), element.get('series')
                if not isinstance(categories, list) or not categories or not isinstance(series, list) or not series:
                    raise ValueError('Chart categories and series must be nonempty lists')
                for category in categories:
                    _text(category, 'category')
                for entry in series:
                    if not isinstance(entry, dict):
                        raise ValueError('series must be an object')
                    _text(entry.get('name'), 'series.name')
                    _color(entry.get('color', '315B72'))
                    if 'colors' in entry:
                        if not isinstance(entry['colors'], list) or len(entry['colors']) != len(categories):
                            raise ValueError('series.colors must match category count')
                        for point_color in entry['colors']:
                            _color(point_color)
                    if not isinstance(entry.get('values'), list) or len(entry['values']) != len(categories):
                        raise ValueError('Every series must match category count')
                    for number in entry['values']:
                        _number(number, 'series value')
                    if element['chartType'] == 'doughnut' and (min(entry['values']) < 0 or sum(entry['values']) <= 0):
                        raise ValueError('Doughnut data must be nonnegative with positive total')
                if element['chartType'] == 'doughnut' and len(series) != 1:
                    raise ValueError('Doughnut supports one series')
                for key in ('min', 'max'):
                    if key in element:
                        _number(element[key], key)
                if 'majorUnit' in element:
                    _number(element['majorUnit'], 'majorUnit', positive=True)
                if 'min' in element and 'max' in element and element['min'] >= element['max']:
                    raise ValueError('Chart min must be smaller than max')
                _text(element.get('numberFormat', 'General'), 'numberFormat')
                if 'holeSize' in element:
                    hole_size = _number(element['holeSize'], 'holeSize')
                    if not 10 <= hole_size <= 90 or hole_size != int(hole_size):
                        raise ValueError('holeSize must be an integer between 10 and 90')


def _emu(number: float) -> int:
    return round(number * PX_EMU)


def _solid(color: str) -> str:
    return f'<a:solidFill><a:srgbClr val="{_color(color)}"/></a:solidFill>'


def _font(font: str) -> str:
    return ''.join(f'<a:{kind} typeface="{_esc(font)}"/>' for kind in ('latin', 'ea', 'cs'))


def _paragraphs(text: str, font: str, size: float, color: str, bold: bool = False, align: str = 'left') -> str:
    alignment = {'left': 'l', 'center': 'ctr', 'right': 'r'}[align]
    props = f'sz="{round(size * 75)}" b="{int(bold)}" lang="ko-KR"'
    return ''.join(
        f'<a:p><a:pPr algn="{alignment}"/><a:r><a:rPr {props}>{_solid(color)}{_font(font)}</a:rPr>'
        f'<a:t xml:space="preserve">{_esc(line)}</a:t></a:r><a:endParaRPr {props}/></a:p>'
        for line in text.split('\n')
    )


def _transform(element: dict, prefix: str = 'a') -> str:
    return (f'<{prefix}:xfrm><a:off x="{_emu(element["x"])}" y="{_emu(element["y"])}"/>'
            f'<a:ext cx="{_emu(element["w"])}" cy="{_emu(element["h"])}"/></{prefix}:xfrm>')


def _shape(element: dict, shape_id: int, font: str) -> str:
    kind = element['type']
    name = _esc(element.get('name', f'{kind} {shape_id}'))
    prefix = f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
    geom = 'roundRect' if kind == 'rect' and element.get('radius', 0) else 'rect'
    fill = _solid(element.get('fill', 'FFFFFF')) if kind == 'rect' else '<a:noFill/>'
    line = f'<a:ln>{_solid(element["lineColor"])}</a:ln>' if 'lineColor' in element else '<a:ln><a:noFill/></a:ln>'
    body = f'<p:spPr>{_transform(element)}<a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>{fill}{line}</p:spPr>'
    if kind == 'text':
        body += '<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="t"><a:noAutofit/></a:bodyPr><a:lstStyle/>'
        body += _paragraphs(element['text'], font, element.get('fontSize', 24), element.get('color', '17232F'), element.get('bold', False), element.get('align', 'left'))
        body += '</p:txBody>'
    return prefix + body + '</p:sp>'


def _line(element: dict, shape_id: int) -> str:
    return (f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{shape_id}" name="{_esc(element.get("name", f"Line {shape_id}"))}"/>'
            '<p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr><p:spPr>' + _transform(element)
            + '<a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
            + f'<a:ln w="{_emu(element.get("width", 1))}">{_solid(element.get("color", "17232F"))}<a:prstDash val="solid"/></a:ln></p:spPr></p:cxnSp>')


def _frame_start(element: dict, shape_id: int, name: str) -> str:
    return (f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{shape_id}" name="{_esc(element.get("name", f"{name} {shape_id}"))}"/>'
            '<p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>' + _transform(element, 'p'))


def _table(element: dict, shape_id: int, font: str) -> str:
    rows = element['rows']
    padding = _emu(element.get('cellPadding', 16))
    widths = element.get('columnWidths', [1] * len(rows[0]))
    grid = ''.join(f'<a:gridCol w="{_emu(element["w"] * width / sum(widths))}"/>' for width in widths)
    body = ''
    for row_index, row in enumerate(rows):
        body += f'<a:tr h="{_emu(element["h"] / len(rows))}">'
        for cell in row:
            fill = element.get('headerFill', 'E6EDF0') if row_index == 0 else element.get('fill', 'FFFFFF')
            body += '<a:tc><a:txBody><a:bodyPr/><a:lstStyle/>'
            rgb = _color(fill)
            luminance = sum(int(rgb[i:i + 2], 16) * weight for i, weight in ((0, .2126), (2, .7152), (4, .0722)))
            header_color = element.get('headerColor', 'FFFFFF' if luminance < 140 else element.get('color', '17232F'))
            cell_color = header_color if row_index == 0 else element.get('color', '17232F')
            body += _paragraphs(cell, font, element.get('fontSize', 20), cell_color, row_index == 0)
            body += f'</a:txBody><a:tcPr marL="{padding}" marR="{padding}" marT="{padding}" marB="{padding}" anchor="ctr">'
            if row_index > 0:
                body += f'<a:lnB w="{PX_EMU}">{_solid("D5DAD7")}<a:prstDash val="solid"/></a:lnB>'
            body += _solid(fill) + '</a:tcPr></a:tc>'
        body += '</a:tr>'
    return (_frame_start(element, shape_id, 'Table') + f'<a:graphic><a:graphicData uri="{A}/table">'
            '<a:tbl><a:tblPr firstRow="1" bandRow="0"/><a:tblGrid>' + grid + '</a:tblGrid>' + body
            + '</a:tbl></a:graphicData></a:graphic></p:graphicFrame>')


def _rels(entries: list[tuple[str, str, str]]) -> str:
    return ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + ''.join(f'<Relationship Id="{_esc(rid)}" Type="{R}/{kind}" Target="{_esc(target)}"/>' for rid, kind, target in entries)
            + '</Relationships>')


def _column(index: int) -> str:
    result = ''
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _xlsx(categories: list[str], series: list[dict], number_format: str = 'General') -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        def put(name: str, content: str) -> None:
            archive.writestr(name, XML_HEADER + content)
        put('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
        put('_rels/.rels', _rels([('rId1', 'officeDocument', 'xl/workbook.xml')]))
        put('xl/workbook.xml', f'<workbook xmlns="{S}" xmlns:r="{R}"><sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>')
        put('xl/_rels/workbook.xml.rels', _rels([('rId1', 'worksheet', 'worksheets/sheet1.xml'), ('rId2', 'styles', 'styles.xml')]))
        put('xl/styles.xml', f'<styleSheet xmlns="{S}"><numFmts count="1"><numFmt numFmtId="164" formatCode="{_esc(number_format)}"/></numFmts><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        rows = [['Category'] + [entry['name'] for entry in series]]
        rows += [[category] + [entry['values'][index] for entry in series] for index, category in enumerate(categories)]
        body = ''
        for row_index, row in enumerate(rows, 1):
            body += f'<row r="{row_index}">'
            for column_index, cell in enumerate(row, 1):
                reference = f'{_column(column_index)}{row_index}'
                if isinstance(cell, str):
                    body += f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">{_esc(cell)}</t></is></c>'
                else:
                    body += f'<c r="{reference}" s="1"><v>{cell}</v></c>'
            body += '</row>'
        put('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{S}"><dimension ref="A1:{_column(len(series) + 1)}{len(categories) + 1}"/><sheetData>{body}</sheetData></worksheet>')
    return buffer.getvalue()


def _chart_text(font: str, size: float = 20) -> str:
    return ('<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr>'
            f'<a:defRPr sz="{round(size * 75)}">{_solid("374151")}{_font(font)}</a:defRPr>'
            '</a:pPr><a:endParaRPr lang="ko-KR"/></a:p></c:txPr>')


def _chart(element: dict, font: str) -> str:
    kind = element['chartType']
    chart_tag = {'bar': 'barChart', 'column': 'barChart', 'line': 'lineChart', 'doughnut': 'doughnutChart'}[kind]
    categories = element['categories']
    count = len(categories)
    series_xml = ''
    for index, entry in enumerate(element['series']):
        column = _column(index + 2)
        series_xml += f'<c:ser><c:idx val="{index}"/><c:order val="{index}"/>'
        series_xml += f'<c:tx><c:strRef><c:f>Data!${column}$1</c:f><c:strCache><c:ptCount val="1"/><c:pt idx="0"><c:v>{_esc(entry["name"])}</c:v></c:pt></c:strCache></c:strRef></c:tx>'
        series_xml += '<c:spPr>' + (_solid(entry.get('color', '315B72')) if kind != 'line' else '<a:noFill/>')
        series_xml += f'<a:ln w="28575">{_solid(entry.get("color", "315B72"))}</a:ln></c:spPr>'
        if kind == 'line':
            series_xml += '<c:marker><c:symbol val="circle"/><c:size val="5"/></c:marker>'
        for point_index, point_color in enumerate(entry.get('colors', [])):
            series_xml += f'<c:dPt><c:idx val="{point_index}"/><c:spPr>{_solid(point_color)}<a:ln><a:noFill/></a:ln></c:spPr></c:dPt>'
        series_xml += f'<c:cat><c:strRef><c:f>Data!$A$2:$A${count + 1}</c:f><c:strCache><c:ptCount val="{count}"/>'
        series_xml += ''.join(f'<c:pt idx="{i}"><c:v>{_esc(category)}</c:v></c:pt>' for i, category in enumerate(categories))
        series_xml += '</c:strCache></c:strRef></c:cat>'
        series_xml += f'<c:val><c:numRef><c:f>Data!${column}$2:${column}${count + 1}</c:f><c:numCache><c:formatCode>{_esc(element.get("numberFormat", "General"))}</c:formatCode><c:ptCount val="{count}"/>'
        series_xml += ''.join(f'<c:pt idx="{i}"><c:v>{number}</c:v></c:pt>' for i, number in enumerate(entry['values']))
        series_xml += '</c:numCache></c:numRef></c:val></c:ser>'
    chart_xml = f'<c:{chart_tag}>'
    if kind in ('bar', 'column'):
        chart_xml += f'<c:barDir val="{"bar" if kind == "bar" else "col"}"/><c:grouping val="clustered"/>'
    elif kind == 'line':
        chart_xml += '<c:grouping val="standard"/>'
    chart_xml += f'<c:varyColors val="{int(kind == "doughnut")}"/>' + series_xml
    if element.get('dataLabels', False):
        chart_xml += f'<c:dLbls><c:numFmt formatCode="{_esc(element.get("numberFormat", "General"))}" sourceLinked="0"/>' + _chart_text(font, element.get('fontSize', 20)) + '<c:showLegendKey val="0"/><c:showVal val="1"/><c:showCatName val="0"/><c:showSerName val="0"/><c:showPercent val="0"/><c:showBubbleSize val="0"/></c:dLbls>'
    if kind == 'doughnut':
        chart_xml += f'<c:firstSliceAng val="270"/><c:holeSize val="{element.get("holeSize", 50)}"/>'
    else:
        if kind in ('bar', 'column'):
            chart_xml += '<c:gapWidth val="100"/><c:overlap val="0"/>'
        chart_xml += '<c:axId val="10001"/><c:axId val="10002"/>'
    chart_xml += f'</c:{chart_tag}>'
    if kind != 'doughnut':
        cat_pos, val_pos = ('l', 'b') if kind == 'bar' else ('b', 'l')
        chart_xml += '<c:catAx><c:axId val="10001"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/>'
        chart_xml += f'<c:axPos val="{cat_pos}"/><c:majorTickMark val="none"/><c:minorTickMark val="none"/><c:tickLblPos val="nextTo"/>'
        chart_xml += _chart_text(font, element.get('fontSize', 20)) + '<c:crossAx val="10002"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/></c:catAx>'
        scaling = '<c:orientation val="minMax"/>'
        for bound in ('max', 'min'):
            if bound in element:
                scaling += f'<c:{bound} val="{element[bound]}"/>'
        chart_xml += f'<c:valAx><c:axId val="10002"/><c:scaling>{scaling}</c:scaling><c:delete val="0"/><c:axPos val="{val_pos}"/>'
        chart_xml += '<c:majorGridlines><c:spPr><a:ln w="6350">' + _solid('DEE3E7') + '</a:ln></c:spPr></c:majorGridlines>'
        chart_xml += f'<c:numFmt formatCode="{_esc(element.get("numberFormat", "General"))}" sourceLinked="0"/><c:majorTickMark val="none"/><c:minorTickMark val="none"/><c:tickLblPos val="nextTo"/>'
        chart_xml += _chart_text(font, element.get('fontSize', 20)) + '<c:crossAx val="10001"/><c:crosses val="autoZero"/><c:crossBetween val="between"/>'
        if 'majorUnit' in element:
            chart_xml += f'<c:majorUnit val="{element["majorUnit"]}"/>'
        chart_xml += '</c:valAx>'
    legend = '<c:legend><c:legendPos val="b"/>' + _chart_text(font) + '</c:legend>' if element.get('legend', len(element['series']) > 1 or kind == 'doughnut') else ''
    return (f'<c:chartSpace xmlns:c="{C}" xmlns:a="{A}" xmlns:r="{R}"><c:lang val="ko-KR"/><c:roundedCorners val="0"/>'
            '<c:chart><c:autoTitleDeleted val="1"/><c:plotArea><c:layout/>' + chart_xml + '</c:plotArea>' + legend
            + '<c:plotVisOnly val="1"/><c:dispBlanksAs val="gap"/></c:chart><c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>'
            + _chart_text(font) + '<c:externalData r:id="rId1"><c:autoUpdate val="0"/></c:externalData></c:chartSpace>')


GROUP_TREE = ('<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
              '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>')
NS = f'xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}"'
COLOR_MAP = '<p:clrMap accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"/>'


def _theme(font: str) -> str:
    colors = {'dk1': '17232F', 'lt1': 'FFFFFF', 'dk2': '374151', 'lt2': 'F3F5F7', 'accent1': '315B72', 'accent2': 'B65443', 'accent3': '809A84', 'accent4': 'D6AB59', 'accent5': '8793A3', 'accent6': 'AE80A0', 'hlink': '0563C1', 'folHlink': '954F72'}
    color_xml = ''.join(f'<a:{name}><a:srgbClr val="{color}"/></a:{name}>' for name, color in colors.items())
    fill = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    return (f'<a:theme xmlns:a="{A}" name="Editable presentation"><a:themeElements><a:clrScheme name="Neutral">{color_xml}</a:clrScheme>'
            f'<a:fontScheme name="Presentation"><a:majorFont>{_font(font)}</a:majorFont><a:minorFont>{_font(font)}</a:minorFont></a:fontScheme>'
            '<a:fmtScheme name="Plain"><a:fillStyleLst>' + fill * 3 + '</a:fillStyleLst><a:lnStyleLst>'
            + ''.join(f'<a:ln w="{width}" cap="flat" cmpd="sng" algn="ctr">{fill}<a:prstDash val="solid"/></a:ln>' for width in (6350, 12700, 19050))
            + '</a:lnStyleLst><a:effectStyleLst>' + '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3
            + '</a:effectStyleLst><a:bgFillStyleLst>' + fill * 3 + '</a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>')


def export_pptx(scene: dict, output: str | Path, base_dir: str | Path | None = None) -> Path:
    """Write an editable .pptx atomically; return its path. No external dependencies."""
    validate_scene(scene, base_dir)
    output = Path(output)
    if output.suffix.lower() != '.pptx':
        raise ValueError('Output extension must be .pptx')
    base = Path(base_dir or '.')
    font = scene.get('font', 'Pretendard')
    parts: dict[str, str | bytes] = {}
    overrides: dict[str, str] = {}
    def xml(name: str, content: str, content_type: str | None = None) -> None:
        parts[name] = XML_HEADER + content
        if content_type:
            overrides['/' + name] = content_type
    ppt_type = 'application/vnd.openxmlformats-officedocument.presentationml.'
    xml('_rels/.rels', _rels([('rId1', 'officeDocument', 'ppt/presentation.xml')]))
    xml('ppt/theme/theme1.xml', _theme(font), 'application/vnd.openxmlformats-officedocument.theme+xml')
    xml('ppt/slideMasters/slideMaster1.xml', f'<p:sldMaster {NS}><p:cSld><p:spTree>{GROUP_TREE}</p:spTree></p:cSld>{COLOR_MAP}<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>', ppt_type + 'slideMaster+xml')
    xml('ppt/slideMasters/_rels/slideMaster1.xml.rels', _rels([('rId1', 'slideLayout', '../slideLayouts/slideLayout1.xml'), ('rId2', 'theme', '../theme/theme1.xml')]))
    xml('ppt/slideLayouts/slideLayout1.xml', f'<p:sldLayout {NS} type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>{GROUP_TREE}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>', ppt_type + 'slideLayout+xml')
    xml('ppt/slideLayouts/_rels/slideLayout1.xml.rels', _rels([('rId1', 'slideMaster', '../slideMasters/slideMaster1.xml')]))
    slide_ids, presentation_rels = '', [('rId1', 'slideMaster', 'slideMasters/slideMaster1.xml')]
    chart_number = image_number = 0
    for slide_number, slide in enumerate(scene['slides'], 1):
        slide_ids += f'<p:sldId id="{255 + slide_number}" r:id="rId{slide_number + 2}"/>'
        presentation_rels.append((f'rId{slide_number + 2}', 'slide', f'slides/slide{slide_number}.xml'))
        relationships = [('rId1', 'slideLayout', '../slideLayouts/slideLayout1.xml')]
        body = ''
        for shape_id, element in enumerate(slide['elements'], 2):
            kind = element['type']
            if kind in ('text', 'rect'):
                body += _shape(element, shape_id, font)
            elif kind == 'line':
                body += _line(element, shape_id)
            elif kind == 'table':
                body += _table(element, shape_id, font)
            elif kind == 'chart':
                chart_number += 1
                relation_id = f'rId{len(relationships) + 1}'
                relationships.append((relation_id, 'chart', f'../charts/chart{chart_number}.xml'))
                body += _frame_start(element, shape_id, 'Chart') + f'<a:graphic><a:graphicData uri="{C}"><c:chart xmlns:c="{C}" r:id="{relation_id}"/></a:graphicData></a:graphic></p:graphicFrame>'
                xml(f'ppt/charts/chart{chart_number}.xml', _chart(element, font), 'application/vnd.openxmlformats-officedocument.drawingml.chart+xml')
                xml(f'ppt/charts/_rels/chart{chart_number}.xml.rels', _rels([('rId1', 'package', f'../embeddings/data{chart_number}.xlsx')]))
                parts[f'ppt/embeddings/data{chart_number}.xlsx'] = _xlsx(element['categories'], element['series'], element.get('numberFormat', 'General'))
            elif kind == 'image':
                image_number += 1
                image_bytes = _image_path(element['path'], base).read_bytes()
                extension = 'png' if image_bytes.startswith(b'\x89PNG') else 'jpeg'
                image_name = f'image{image_number}.{extension}'
                parts['ppt/media/' + image_name] = image_bytes
                relation_id = f'rId{len(relationships) + 1}'
                relationships.append((relation_id, 'image', '../media/' + image_name))
                body += f'<p:pic><p:nvPicPr><p:cNvPr id="{shape_id}" name="{_esc(element.get("name", f"Image {shape_id}"))}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="{relation_id}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr>{_transform(element)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
        xml(f'ppt/slides/slide{slide_number}.xml', f'<p:sld {NS}><p:cSld name="{_esc(slide.get("title", ""))}"><p:bg><p:bgPr>{_solid("FFFFFF")}<a:effectLst/></p:bgPr></p:bg><p:spTree>{GROUP_TREE}{body}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>', ppt_type + 'slide+xml')
        xml(f'ppt/slides/_rels/slide{slide_number}.xml.rels', _rels(relationships))
    xml('ppt/presentation.xml', f'<p:presentation {NS}><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>{slide_ids}</p:sldIdLst><p:sldSz cx="{_emu(scene.get("width", 1280))}" cy="{_emu(scene.get("height", 720))}"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle/></p:presentation>', ppt_type + 'presentation.main+xml')
    xml('ppt/_rels/presentation.xml.rels', _rels(presentation_rels))
    defaults = {'rels': 'application/vnd.openxmlformats-package.relationships+xml', 'xml': 'application/xml', 'png': 'image/png', 'jpeg': 'image/jpeg', 'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
    xml('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' + ''.join(f'<Default Extension="{key}" ContentType="{value}"/>' for key, value in defaults.items()) + ''.join(f'<Override PartName="{key}" ContentType="{value}"/>' for key, value in overrides.items()) + '</Types>')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, suffix='.pptx', delete=False) as stream:
            temporary = Path(stream.name)
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, content in parts.items():
                archive.writestr(name, content)
        os.replace(temporary, output)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return output
