"""Native PowerPoint export tests: editable objects, chart workbooks, relationships.

작성자: Git 이력 참조
작성목적: 이미지로 평탄화되지 않은 PPTX 구조와 데이터 연결을 검증한다.
작성일: 2026-10-01
주의사항: XML 검증은 PowerPoint에서 직접 편집·저장한 검증을 대신하지 않는다.
"""
from __future__ import annotations

import copy
import io
import posixpath
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from native_pptx import A, C, P, R, S, export_pptx, validate_scene

NS = {'a': A, 'p': P, 'c': C, 's': S}
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
TINY_PNG = bytes.fromhex('89504e470d0a1a0a0000000d4948445200000002000000010806000000f478d4fa0000000d49444154789c63f8cf00020c0c0001050101e1d6d1f70000000049454e44ae426082')


def chart(kind: str = 'column') -> dict:
    return dict(type='chart', x=40, y=140, w=650, h=450, chartType=kind,
                categories=['오전', '오후', '저녁'], series=[dict(name='지연율', values=[8, 12, 24], color='B65443')],
                min=0, max=30, numberFormat='0"%"', dataLabels=True)


def scene(elements: list | None = None) -> dict:
    return dict(title='시험 & 분석', width=1280, height=720, font='Pretendard', slides=[dict(
        title='한글 <제목>', elements=elements or [
            dict(type='text', x=40, y=40, w=1100, h=70, text='결과 & 기준 <비교>', fontSize=42, bold=True, color='17232F'),
            chart(),
            dict(type='rect', x=800, y=200, w=300, h=100, fill='F2F3F5', radius=10),
            dict(type='line', x=800, y=320, w=300, h=0, color='B65443', width=2),
            dict(type='table', x=800, y=360, w=300, h=200, rows=[['구분', '건수'], ['A', '12']], columnWidths=[2, 1], headerFill='17232F')])])


class NativePptxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.output = self.root / 'editable.pptx'

    def tearDown(self) -> None:
        self.directory.cleanup()

    def package(self, spec: dict | None = None) -> zipfile.ZipFile:
        export_pptx(spec or scene(), self.output, self.root)
        return zipfile.ZipFile(self.output)

    def test_all_xml_well_formed_and_every_relationship_resolves(self) -> None:
        with self.package() as archive:
            names = set(archive.namelist())
            for name in names:
                if name.endswith(('.xml', '.rels')):
                    root = ET.fromstring(archive.read(name))
                    if name.endswith('.rels'):
                        directory = name.rsplit('/_rels/', 1)[0] if '/_rels/' in name else ''
                        relation_ids = []
                        for rel in root:
                            self.assertNotEqual(rel.attrib.get('TargetMode'), 'External')
                            target = posixpath.normpath(posixpath.join(directory, rel.attrib['Target']))
                            self.assertIn(target, names, (name, target))
                            relation_ids.append(rel.attrib['Id'])
                        self.assertEqual(len(relation_ids), len(set(relation_ids)))

    def test_text_shapes_and_table_are_native(self) -> None:
        with self.package() as archive:
            slide = ET.fromstring(archive.read('ppt/slides/slide1.xml'))
            self.assertEqual(len(slide.findall('.//p:sp', NS)), 2)
            self.assertEqual(len(slide.findall('.//p:cxnSp', NS)), 1)
            self.assertEqual(len(slide.findall('.//a:tbl', NS)), 1)
            self.assertEqual(len(slide.findall('.//p:pic', NS)), 0)
            self.assertIn('결과 & 기준 <비교>', [node.text for node in slide.findall('.//a:t', NS)])
            header = slide.find('.//a:tbl/a:tr/a:tc/a:txBody//a:rPr/a:solidFill/a:srgbClr', NS)
            self.assertEqual(header.attrib['val'], 'FFFFFF')
            font = slide.find('.//a:rPr/a:ea', NS)
            self.assertEqual(font.attrib['typeface'], 'Pretendard')

    def test_native_chart_contains_formula_references_and_editable_workbook(self) -> None:
        with self.package() as archive:
            slide = ET.fromstring(archive.read('ppt/slides/slide1.xml'))
            self.assertEqual(len(slide.findall('.//c:chart', NS)), 1)
            chart_xml = ET.fromstring(archive.read('ppt/charts/chart1.xml'))
            formulas = [node.text for node in chart_xml.findall('.//c:f', NS)]
            self.assertEqual(formulas, ['Data!$B$1', 'Data!$A$2:$A$4', 'Data!$B$2:$B$4'])
            self.assertEqual(chart_xml.find('.//c:barDir', NS).attrib['val'], 'col')
            with zipfile.ZipFile(io.BytesIO(archive.read('ppt/embeddings/data1.xlsx'))) as workbook:
                sheet = ET.fromstring(workbook.read('xl/worksheets/sheet1.xml'))
                self.assertEqual([node.text for node in sheet.findall('.//s:v', NS)], ['8', '12', '24'])
                self.assertEqual([node.text for node in sheet.findall('.//s:t', NS)], ['Category', '지연율', '오전', '오후', '저녁'])
                for name in workbook.namelist():
                    ET.fromstring(workbook.read(name))

    def test_bar_line_and_doughnut_are_native_charts(self) -> None:
        for kind, tag in [('bar', 'barChart'), ('line', 'lineChart'), ('doughnut', 'doughnutChart')]:
            with self.subTest(kind=kind), self.package(scene([chart(kind)])) as archive:
                tree = ET.fromstring(archive.read('ppt/charts/chart1.xml'))
                self.assertIsNotNone(tree.find('.//c:' + tag, NS))
                if kind == 'bar':
                    self.assertEqual(tree.find('.//c:barDir', NS).attrib['val'], 'bar')
                if kind == 'doughnut':
                    self.assertEqual(tree.find('.//c:holeSize', NS).attrib['val'], '50')
                    self.assertIsNone(tree.find('.//c:valAx', NS))

    def test_doughnut_point_colors_and_custom_hole(self) -> None:
        element = chart('doughnut')
        element['series'][0]['colors'] = ['52766F', 'B64F48', 'AAAAAA']
        element['holeSize'] = 70
        with self.package(scene([element])) as archive:
            tree = ET.fromstring(archive.read('ppt/charts/chart1.xml'))
            self.assertEqual(tree.find('.//c:holeSize', NS).attrib['val'], '70')
            self.assertEqual([node.attrib['val'] for node in tree.findall('.//c:dPt/c:spPr/a:solidFill/a:srgbClr', NS)], ['52766F', 'B64F48', 'AAAAAA'])

    def test_axis_ranges_number_formats_and_chart_fonts(self) -> None:
        with self.package() as archive:
            tree = ET.fromstring(archive.read('ppt/charts/chart1.xml'))
            self.assertEqual(tree.find('.//c:valAx/c:scaling/c:min', NS).attrib['val'], '0')
            self.assertEqual(tree.find('.//c:valAx/c:scaling/c:max', NS).attrib['val'], '30')
            self.assertEqual(tree.find('.//c:valAx/c:numFmt', NS).attrib['formatCode'], '0"%"')
            for node in tree.findall('.//c:txPr', NS):
                self.assertEqual(node.find('.//a:ea', NS).attrib['typeface'], 'Pretendard')
                self.assertEqual(node.find('.//a:defRPr', NS).attrib['sz'], '1500')

    def test_percent_labels_workbook_formats_and_major_unit(self) -> None:
        element = chart()
        element.update(numberFormat='0%', max=.3, majorUnit=.1)
        element['series'][0]['values'] = [.08, .12, .24]
        with self.package(scene([element])) as archive:
            tree = ET.fromstring(archive.read('ppt/charts/chart1.xml'))
            self.assertEqual(tree.find('.//c:dLbls/c:numFmt', NS).attrib, {'formatCode': '0%', 'sourceLinked': '0'})
            self.assertEqual(tree.find('.//c:valAx/c:majorUnit', NS).attrib['val'], '0.1')
            with zipfile.ZipFile(io.BytesIO(archive.read('ppt/embeddings/data1.xlsx'))) as workbook:
                styles = ET.fromstring(workbook.read('xl/styles.xml'))
                self.assertEqual(styles.find('s:numFmts/s:numFmt', NS).attrib['formatCode'], '0%')
                sheet = ET.fromstring(workbook.read('xl/worksheets/sheet1.xml'))
                numeric_cells = [cell for cell in sheet.findall('.//s:c', NS) if cell.find('s:v', NS) is not None]
                self.assertTrue(all(cell.attrib.get('s') == '1' for cell in numeric_cells))
                self.assertEqual([cell.find('s:v', NS).text for cell in numeric_cells], ['0.08', '0.12', '0.24'])
        element['majorUnit'] = 0
        with self.assertRaises(ValueError):
            validate_scene(scene([element]))

    def test_no_speaker_notes_and_geometry_preserved(self) -> None:
        with self.package() as archive:
            self.assertFalse(any('/notes' in name for name in archive.namelist()))
            pres = ET.fromstring(archive.read('ppt/presentation.xml'))
            self.assertEqual(pres.find('p:sldSz', NS).attrib, {'cx': '12192000', 'cy': '6858000'})

    def test_local_image_remains_separate_editable_object(self) -> None:
        (self.root / 'chart.png').write_bytes(TINY_PNG)
        image = dict(type='image', x=10, y=10, w=400, h=200, path='chart.png')
        with self.package(scene([image])) as archive:
            self.assertEqual(archive.read('ppt/media/image1.png'), TINY_PNG)
            slide = ET.fromstring(archive.read('ppt/slides/slide1.xml'))
            self.assertEqual(len(slide.findall('.//p:pic', NS)), 1)

    def test_multiple_slides_charts_and_series_have_distinct_parts(self) -> None:
        spec = scene([chart(), chart('line')])
        spec['slides'].append(copy.deepcopy(spec['slides'][0]))
        spec['slides'][1]['elements'][0]['series'].append(dict(name='비교군', values=[3, 5, 8], color='52766F'))
        with self.package(spec) as archive:
            self.assertEqual(len([name for name in archive.namelist() if re_chart(name)]), 4)
            tree = ET.fromstring(archive.read('ppt/charts/chart3.xml'))
            self.assertEqual(len(tree.findall('.//c:ser', NS)), 2)
            self.assertIn('Data!$C$2:$C$4', [node.text for node in tree.findall('.//c:f', NS)])

    def test_invalid_data_does_not_replace_existing_file(self) -> None:
        self.output.write_bytes(b'existing presentation')
        broken = scene()
        broken['slides'][0]['elements'][1]['series'][0]['values'] = [1]
        with self.assertRaises(ValueError):
            export_pptx(broken, self.output)
        self.assertEqual(self.output.read_bytes(), b'existing presentation')
        self.assertEqual(list(self.root.iterdir()), [self.output])

    def test_invalid_geometry_and_nonfinite_values_fail(self) -> None:
        for change in [dict(x=-1), dict(w=2000), dict(h=0), dict(x=float('nan')), dict(fontSize=0), dict(x=True), dict(fontSize=float('inf'))]:
            with self.subTest(change=change):
                spec = scene()
                spec['slides'][0]['elements'][0].update(change)
                with self.assertRaises(ValueError):
                    validate_scene(spec)

    def test_invalid_chart_cardinality_ranges_and_colors_fail(self) -> None:
        mutations = [dict(categories=[]), dict(series=[]), dict(min=40), dict(legend='yes'), dict(holeSize=101), dict(chartType='scatter')]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                element = chart()
                element.update(mutation)
                with self.assertRaises(ValueError):
                    validate_scene(scene([element]))
        for mutation in [dict(values=[1, 2]), dict(values=[1, float('nan'), 2]), dict(color='red'), dict(colors=['000000'])]:
            with self.subTest(mutation=mutation):
                element = chart()
                element['series'][0].update(mutation)
                with self.assertRaises(ValueError):
                    validate_scene(scene([element]))

    def test_doughnut_rejects_negative_zero_and_multiple_series(self) -> None:
        for values in [[1, -2, 3], [0, 0, 0]]:
            element = chart('doughnut')
            element['series'][0]['values'] = values
            with self.assertRaises(ValueError):
                validate_scene(scene([element]))
        element = chart('doughnut')
        element['series'] *= 2
        with self.assertRaises(ValueError):
            validate_scene(scene([element]))

    def test_invalid_table_and_unsafe_image_fail(self) -> None:
        for rows in [[], [['a'], []], [[3]]]:
            with self.subTest(rows=rows):
                table = dict(type='table', x=1, y=1, w=100, h=100, rows=rows)
                with self.assertRaises(ValueError):
                    validate_scene(scene([table]))
        for path in ['https://example.com/image.png', 'data:image/png,123', 'missing.png']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_scene(scene([dict(type='image', x=1, y=1, w=100, h=100, path=path)]), self.root)
        (self.root / 'fake.png').write_text('not an image')
        with self.assertRaises(ValueError):
            validate_scene(scene([dict(type='image', x=1, y=1, w=100, h=100, path='fake.png')]), self.root)

    def test_control_characters_and_wrong_output_extension_fail(self) -> None:
        spec = scene()
        spec['slides'][0]['title'] = 'bad\x01title'
        with self.assertRaises(ValueError):
            validate_scene(spec)
        with self.assertRaises(ValueError):
            export_pptx(scene(), self.root / 'wrong.pdf')

    def test_table_padding_borders_and_explicit_padding(self) -> None:
        for requested, expected in [(None, '152400'), (0, '0'), (12, '114300')]:
            spec = scene()
            table = spec['slides'][0]['elements'][-1]
            if requested is not None:
                table['cellPadding'] = requested
            with self.package(spec) as archive:
                slide = ET.fromstring(archive.read('ppt/slides/slide1.xml'))
                properties = slide.findall('.//a:tbl/a:tr/a:tc/a:tcPr', NS)
                for prop in properties:
                    self.assertTrue(all(prop.attrib[key] == expected for key in ('marL', 'marR', 'marT', 'marB')))
                self.assertIsNone(properties[0].find('a:lnB', NS))
                border = properties[2].find('a:lnB', NS)
                self.assertEqual(border.attrib['w'], '9525')
                self.assertEqual(border.find('a:solidFill/a:srgbClr', NS).attrib['val'], 'D5DAD7')
        for invalid in [-1, True, float('nan')]:
            spec = scene()
            spec['slides'][0]['elements'][-1]['cellPadding'] = invalid
            with self.assertRaises(ValueError):
                validate_scene(spec)

    def test_selection_pane_names_for_all_native_objects(self) -> None:
        spec = scene()
        expected = ['제목 & 요약', '지연율 차트', '설명 배경', '구분선', '비교표']
        for element, name in zip(spec['slides'][0]['elements'], expected):
            element['name'] = name
        with self.package(spec) as archive:
            slide = ET.fromstring(archive.read('ppt/slides/slide1.xml'))
            names = [node.attrib['name'] for node in slide.findall('.//p:cNvPr', NS)]
            self.assertEqual(names[1:], expected)
        spec['slides'][0]['elements'][0]['name'] = 123
        with self.assertRaises(ValueError):
            validate_scene(spec)

    def test_scene_inputs_are_not_mutated(self) -> None:
        spec = scene()
        before = copy.deepcopy(spec)
        export_pptx(spec, self.output)
        self.assertEqual(spec, before)


def re_chart(name: str) -> bool:
    return name.startswith('ppt/charts/chart') and name.endswith('.xml')


if __name__ == '__main__':
    unittest.main()
