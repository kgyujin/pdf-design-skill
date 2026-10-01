"""Selection, recoloring and default-output regression checks."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import presentation_palette as palettes
import pdfdesign
ROOT=Path(__file__).resolve().parents[1]

def luminance(color):
    components=[int(color[i:i+2],16)/255 for i in (0,2,4)]
    linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in components]
    return sum(x*w for x,w in zip(linear,[.2126,.7152,.0722]))
def contrast(a,b):
    l1,l2=sorted([luminance(a),luminance(b)])
    return (l2+.05)/(l1+.05)

class PresentationPaletteTests(unittest.TestCase):
    def test_topic_selection_and_ascii_word_boundary(self):
        for topic,expected in [('분자 독성 분석','scientific'),('클라우드 API','technology'),('배송 운영','business'),('탄소 환경','nature'),('교육 학습','education'),('retail overview','neutral'),('','neutral')]:
            with self.subTest(topic=topic):self.assertEqual(palettes.choose_palette(topic)[0],expected)
    def test_explicit_then_saved_then_auto(self):
        self.assertEqual(palettes.choose_palette('환경', 'business','scientific'),('business','explicit'))
        self.assertEqual(palettes.choose_palette('환경', None,'scientific'),('scientific','saved'))
        self.assertEqual(palettes.choose_palette('환경', 'auto','scientific'),('scientific','saved'))
    def test_roles_recolor_chart_and_preserve_literal_and_input(self):
        scene={'title':'분자 독성','slides':[{'elements':[{'type':'text','color':'@accent','fill':'@accent/20','lineColor':'123456','series':[{'color':'@secondary','colors':['@accent','ABCDEF']}]}]}]}
        before=copy.deepcopy(scene)
        result,name,_=palettes.apply_scene_palette(scene)
        e=result['slides'][0]['elements'][0]
        self.assertEqual(name,'scientific');self.assertEqual(e['color'],'B63E4C');self.assertEqual(e['lineColor'],'123456')
        self.assertEqual(e['series'][0]['colors'],['B63E4C','ABCDEF']);self.assertNotIn('@',e['fill']);self.assertEqual(scene,before)
        with self.assertRaises(ValueError):palettes.apply_scene_palette({'slides':[{'elements':[{'color':'@accent/101'}]}]})
    def test_curated_text_pairs_have_readable_contrast(self):
        for name,p in palettes.catalog().items():
            c=p['colors']
            for fg,bg in [('ink','paper'),('muted','white'),('muted','paper'),('onAccent','accent')]:
                with self.subTest(name=name,pair=(fg,bg)):self.assertGreaterEqual(contrast(c[fg],c[bg]),4.5)
    def test_init_and_pptx_apply_topic_without_source_or_notes(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder); html=folder/'deck.html'
            self.assertEqual(pdfdesign.main(['init','deck',str(html),'--topic','분자 독성']),0)
            markup=html.read_text();self.assertIn('data-palette="scientific"',markup);self.assertNotIn('출처:',markup);self.assertNotIn('aside class="notes"',markup)
            scene={'title':'물류 배송','slides':[{'elements':[{'type':'text','x':10,'y':10,'w':200,'h':70,'text':'제목','color':'@accent'}]}]}
            source=folder/'scene.json';source.write_text(json.dumps(scene));out=folder/'scene.pptx'
            self.assertEqual(pdfdesign.main(['pptx',str(source),str(out)]),0)
            with zipfile.ZipFile(out) as z:
                self.assertIn(b'225CA8',z.read('ppt/slides/slide1.xml'))
                self.assertFalse(any('notesSlide' in name for name in z.namelist()))
    def test_existing_scene_palette_and_rgb_are_preserved(self):
        scene={'palette':'education','slides':[{'elements':[{'color':'@accent','fill':'123456'}]}]}
        out,name,_=palettes.apply_scene_palette(scene,topic='환경',stored='nature')
        self.assertEqual(name,'education');self.assertEqual(out['slides'][0]['elements'][0]['fill'],'123456')
        out,name,_=palettes.apply_scene_palette(scene,explicit='business');self.assertEqual(name,'business')

if __name__=='__main__':unittest.main()
