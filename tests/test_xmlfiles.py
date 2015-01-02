"""Test the classes and functions defined by gg/xmlfiles.py"""

from mock import Mock
from os.path import join
from xml.parsers.expat import ExpatError

from tests import BaseTestCase


class XmlFilesTestCase(BaseTestCase):
    filename = 'xmlfiles'

    def setUp(self):
        super().setUp()
        self.mod.Gst = Mock()
        self.mod.MapView = Mock()
        self.mod.ParserCreate = Mock()
        self.normal_kml = join(self.data_dir, 'normal.kml')

    def test_gtkclutter_init(self):
        self.mod.GtkClutter.init.assert_called_once_with([])

    def test_make_clutter_color(self):
        m = Mock(red=32767, green=65535, blue=32767)
        color = self.mod.make_clutter_color(m)
        self.assertEqual(color, self.mod.Clutter.Color.new.return_value)
        self.mod.Clutter.Color.new.assert_called_once_with(
            127.99609375, 255.99609375, 127.99609375, 192.0)

    def test_track_color_changed(self):
        s = Mock()
        p = [Mock(), Mock()]
        self.mod.make_clutter_color = Mock()
        self.mod.track_color_changed(s, p)
        s.get_color.assert_called_once_with()
        self.mod.Gst.set_color.assert_called_once_with(s.get_color.return_value)
        self.mod.make_clutter_color.assert_called_once_with(s.get_color.return_value)
        c = self.mod.make_clutter_color.return_value
        c.lighten.return_value.lighten.assert_called_once_with()
        p[0].set_stroke_color.assert_called_once_with(c)
        p[1].set_stroke_color.assert_called_once_with(c.lighten().lighten())

    def test_polygon_init(self):
        p = self.mod.Polygon()
        p.set_stroke_width.assert_called_once_with(4)
        self.mod.MapView.add_layer.assert_called_once_with(p)

    def test_polygon_append_point(self):
        p = self.mod.Polygon()
        coord = p.append_point(1, 2, 3)
        self.mod.Champlain.Coordinate.new_full.assert_called_once_with(1, 2)
        self.assertEqual(coord.lat, 1)
        self.assertEqual(coord.lon, 2)
        self.assertEqual(coord.ele, 3.0)
        p.add_node.assert_called_once_with(coord)

    def test_polygon_append_point_invalid_elevation(self):
        p = self.mod.Polygon()
        coord = p.append_point(1, 2, 'five')
        self.mod.Champlain.Coordinate.new_full.assert_called_once_with(1, 2)
        self.assertEqual(coord.lat, 1)
        self.assertEqual(coord.lon, 2)
        self.assertEqual(coord.ele, 0.0)
        p.add_node.assert_called_once_with(coord)

    def test_xmlsimpleparser_init(self):
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, 3, 4, 5)
        self.assertEqual(x.call_start, 4)
        self.assertEqual(x.call_end, 5)
        self.assertEqual(x.watchlist, 3)
        self.assertEqual(x.rootname, 2)
        self.assertIsNone(x.tracking)
        self.assertIsNone(x.element)
        self.mod.ParserCreate.assert_called_once_with()
        self.assertEqual(x.parser.ParseFile.mock_calls[0][1][0].name, self.normal_kml)
        self.assertEqual(x.parser.StartElementHandler, x.element_root)

    def test_xmlsimpleparser_init_failed(self):
        self.mod.ParserCreate.return_value.ParseFile.side_effect = ExpatError()
        with self.assertRaises(OSError):
            self.mod.XMLSimpleParser(self.normal_kml, 2, 3, 4, 5)

    def test_xmlsimpleparser_element_root(self):
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, 3, 4, 5)
        self.assertEqual(x.parser.StartElementHandler, x.element_root)
        x.element_root(2, 'five')
        self.assertEqual(x.parser.StartElementHandler, x.element_start)

    def test_xmlsimpleparser_element_root_failed(self):
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, 3, 4, 5)
        self.assertEqual(x.parser.StartElementHandler, x.element_root)
        with self.assertRaises(OSError):
            x.element_root(3, 'five')
        self.assertEqual(x.parser.StartElementHandler, x.element_root)

    def test_xmlsimpleparser_element_start_ignored(self):
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, [], 4, 5)
        x.call_start = Mock()
        x.element_start('foo', 'bar')
        self.assertEqual(x.call_start.mock_calls, [])
        self.assertIsNone(x.element)

    def test_xmlsimpleparser_element_start_watching(self):
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, ['foo'], 4, 5)
        x.call_start = Mock()
        x.element_start('foo', dict(bar='grill'))
        x.call_start.assert_called_once_with('foo', dict(bar='grill'))
        self.assertEqual(x.tracking, 'foo')
        self.assertEqual(x.element, 'foo')
        self.assertEqual(x.parser.CharacterDataHandler, x.element_data)
        self.assertEqual(x.parser.EndElementHandler, x.element_end)
        self.assertEqual(x.state, dict(bar='grill'))

    def test_xmlsimpleparser_element_data_empty(self):
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, ['foo'], 4, 5)
        self.assertEqual(x.state, {})
        x.element_data('        ')
        self.assertEqual(x.state, {})

    def test_xmlsimpleparser_element_data_something(self):
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, ['foo'], 4, 5)
        x.element = 'neon'
        self.assertEqual(x.state, {})
        x.element_data('atomic number: 10')
        self.assertEqual(x.state, dict(neon='atomic number: 10'))

    def test_xmlsimpleparser_element_data_chunked(self):
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, ['foo'], 4, 5)
        x.element = 'neon'
        self.assertEqual(x.state, {})
        x.element_data('atomic ')
        x.element_data('number: 10')
        self.assertEqual(x.state, dict(neon='atomic number: 10'))

    def test_xmlsimpleparser_element_end(self):
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, ['foo'], 4, 5)
        x.call_end = Mock()
        x.tracking = 'neon'
        x.state = dict(neon='atomic number: 10')
        x.element_end('neon')
        x.call_end.assert_called_once_with('neon', x.state)
        self.assertIsNone(x.tracking)
        self.assertEqual(x.state, dict())
        self.assertIsNone(x.parser.CharacterDataHandler)
        self.assertIsNone(x.parser.EndElementHandler)

    def test_xmlsimpleparser_element_end_ignored(self):
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, ['foo'], 4, 5)
        x.call_end = Mock()
        x.tracking = 'neon'
        x.element_end('lithium')
        self.assertEqual(x.call_end.mock_calls, [])
        self.assertEqual(x.tracking, 'neon')
