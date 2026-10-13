"""Pure C-layout geometry checks; independent of Flask/SimPy dependencies."""
import unittest
from line_layout import c_layout, break_count, HEIGHT, WIDTH


class GeometryTests(unittest.TestCase):
    def test_generated_boxes_match_manual_station_geometry(self):
        self.assertEqual((WIDTH,HEIGHT),(150,96))
        for count in range(1,10):
            ids=[str(i) for i in range(1,count+1)]
            layout=c_layout(ids)
            for box in [*layout['positions'].values(),layout['input'],layout['output']]:
                self.assertEqual((box['w'],box['h']),(150,96))

    def test_c_layout_breaks_are_stable(self):
        for count in range(2,9):
            ids=[str(i) for i in range(count)]
            for split in range(1,count):
                layout=c_layout(ids,ids[split-1]);positions=layout['positions']
                self.assertEqual(layout['top_count'],split)
                self.assertGreater(layout['input']['x'],positions[ids[0]]['x'])
                self.assertEqual(positions[ids[split-1]]['x'],positions[ids[split]]['x'])
                self.assertGreater(positions[ids[split]]['y'],positions[ids[split-1]]['y'])
                self.assertGreater(layout['output']['x'],positions[ids[-1]]['x'])
                self.assertEqual(layout['output']['y'],positions[ids[-1]]['y'])
                self.assertEqual(layout['width'],max(layout['input']['x'],layout['output']['x'])+WIDTH+80)
                self.assertEqual(layout['height'],620+HEIGHT+80)


if __name__=='__main__':unittest.main()
