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
        self.mod.GSettings = Mock()
        self.mod.MapView = Mock()
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
        self.mod.ParserCreate = Mock()
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
        self.mod.ParserCreate = Mock()
        self.mod.ParserCreate.return_value.ParseFile.side_effect = ExpatError()
        with self.assertRaises(OSError):
            self.mod.XMLSimpleParser(self.normal_kml, 2, 3, 4, 5)

    def test_xmlsimpleparser_element_root(self):
        self.mod.ParserCreate = Mock()
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, 3, 4, 5)
        self.assertEqual(x.parser.StartElementHandler, x.element_root)
        x.element_root(2, 'five')
        self.assertEqual(x.parser.StartElementHandler, x.element_start)

    def test_xmlsimpleparser_element_root_failed(self):
        self.mod.ParserCreate = Mock()
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, 3, 4, 5)
        self.assertEqual(x.parser.StartElementHandler, x.element_root)
        with self.assertRaises(OSError):
            x.element_root(3, 'five')
        self.assertEqual(x.parser.StartElementHandler, x.element_root)

    def test_xmlsimpleparser_element_start_ignored(self):
        self.mod.ParserCreate = Mock()
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, [], 4, 5)
        x.call_start = Mock()
        x.element_start('foo', 'bar')
        self.assertEqual(x.call_start.mock_calls, [])
        self.assertIsNone(x.element)

    def test_xmlsimpleparser_element_start_watching(self):
        self.mod.ParserCreate = Mock()
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
        self.mod.ParserCreate = Mock()
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, ['foo'], 4, 5)
        self.assertEqual(x.state, {})
        x.element_data('        ')
        self.assertEqual(x.state, {})

    def test_xmlsimpleparser_element_data_something(self):
        self.mod.ParserCreate = Mock()
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, ['foo'], 4, 5)
        x.element = 'neon'
        self.assertEqual(x.state, {})
        x.element_data('atomic number: 10')
        self.assertEqual(x.state, dict(neon='atomic number: 10'))

    def test_xmlsimpleparser_element_data_chunked(self):
        self.mod.ParserCreate = Mock()
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, ['foo'], 4, 5)
        x.element = 'neon'
        self.assertEqual(x.state, {})
        x.element_data('atomic ')
        x.element_data('number: 10')
        self.assertEqual(x.state, dict(neon='atomic number: 10'))

    def test_xmlsimpleparser_element_end(self):
        self.mod.ParserCreate = Mock()
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
        self.mod.ParserCreate = Mock()
        x = self.mod.XMLSimpleParser(self.normal_kml, 2, ['foo'], 4, 5)
        x.call_end = Mock()
        x.tracking = 'neon'
        x.element_end('lithium')
        self.assertEqual(x.call_end.mock_calls, [])
        self.assertEqual(x.tracking, 'neon')

    def test_gpxfile(self):
        self.mod.Champlain.Coordinate.new_full = Mock
        gpx = join(self.demo_dir, '2010 10 16.gpx')
        g = self.mod.GPXFile(gpx)
        timestamps = sorted(g.tracks)
        self.assertEqual(len(timestamps), 374)
        middle = len(timestamps) // 2
        self.assertEqual(timestamps[0], 1287259751)
        self.assertEqual(g.tracks[timestamps[0]].lat, 53.52263)
        self.assertEqual(g.tracks[timestamps[0]].lon, -113.448979)
        self.assertEqual(g.tracks[timestamps[0]].ele, 671.666)
        self.assertEqual(timestamps[1], 1287259753)
        self.assertEqual(g.tracks[timestamps[1]].lat, 53.522731)
        self.assertEqual(g.tracks[timestamps[1]].lon, -113.448985)
        self.assertEqual(g.tracks[timestamps[1]].ele, 671.092)
        self.assertEqual(timestamps[middle], 1287260239)
        self.assertEqual(g.tracks[timestamps[middle]].lat, 53.534902)
        self.assertEqual(g.tracks[timestamps[middle]].lon, -113.443092)
        self.assertEqual(g.tracks[timestamps[middle]].ele, 655.542)
        self.assertEqual(timestamps[-2], 1287260754)
        self.assertEqual(g.tracks[timestamps[-2]].lat, 53.522584)
        self.assertEqual(g.tracks[timestamps[-2]].lon, -113.450535)
        self.assertEqual(g.tracks[timestamps[-2]].ele, 662.377)
        self.assertEqual(timestamps[-1], 1287260756)
        self.assertEqual(g.tracks[timestamps[-1]].lat, 53.522496)
        self.assertEqual(g.tracks[timestamps[-1]].lon, -113.450537)
        self.assertEqual(g.tracks[timestamps[-1]].ele, 662.475)

    def test_kmlfile(self, filename='normal.kml'):
        self.mod.Champlain.Coordinate.new_full = Mock
        self.mod.Coordinates = Mock()
        kml = join(self.data_dir, filename)
        k = self.mod.KMLFile(kml)
        timestamps = sorted(k.tracks)
        self.assertEqual(len(timestamps), 84)
        middle = len(timestamps) // 2
        self.assertEqual(timestamps[0], 1336169331)
        self.assertEqual(k.tracks[timestamps[0]].lat, 39.6012887)
        self.assertEqual(k.tracks[timestamps[0]].lon, 3.2617136)
        self.assertEqual(k.tracks[timestamps[0]].ele, 185.0)
        self.assertEqual(timestamps[1], 1336170232)
        self.assertEqual(k.tracks[timestamps[1]].lat, 39.6012887)
        self.assertEqual(k.tracks[timestamps[1]].lon, 3.2617136)
        self.assertEqual(k.tracks[timestamps[1]].ele, 185.0)
        self.assertEqual(timestamps[middle], 1336207136)
        self.assertEqual(k.tracks[timestamps[middle]].lat, 39.6013261)
        self.assertEqual(k.tracks[timestamps[middle]].lon, 3.2617602)
        self.assertEqual(k.tracks[timestamps[middle]].ele, 178.0)
        self.assertEqual(timestamps[-2], 1336253537)
        self.assertEqual(k.tracks[timestamps[-2]].lat, 39.6012402)
        self.assertEqual(k.tracks[timestamps[-2]].lon, 3.2617779)
        self.assertEqual(k.tracks[timestamps[-2]].ele, 0.0)
        self.assertEqual(timestamps[-1], 1336254435)
        self.assertEqual(k.tracks[timestamps[-1]].lat, 39.6012402)
        self.assertEqual(k.tracks[timestamps[-1]].lon, 3.2617779)
        self.assertEqual(k.tracks[timestamps[-1]].ele, 0.0)

    def test_kmlfile_disordered(self):
        self.test_kmlfile('disordered.kml')

    def test_csvfile_mytracks(self):
        self.mod.Champlain.Coordinate.new_full = Mock
        self.mod.Coordinates = Mock()
        csv = join(self.data_dir, 'mytracks.csv')
        c = self.mod.CSVFile(csv)
        timestamps = sorted(c.tracks)
        self.assertEqual(len(timestamps), 100)
        middle = len(timestamps) // 2
        self.assertEqual(timestamps[0], 1339795704)
        self.assertEqual(c.tracks[timestamps[0]].lat, 49.887554)
        self.assertEqual(c.tracks[timestamps[0]].lon, -97.131041)
        self.assertEqual(c.tracks[timestamps[0]].ele, 217.1999969482422)
        self.assertEqual(timestamps[1], 1339795705)
        self.assertEqual(c.tracks[timestamps[1]].lat, 49.887552)
        self.assertEqual(c.tracks[timestamps[1]].lon, -97.130966)
        self.assertEqual(c.tracks[timestamps[1]].ele, 220.6999969482422)
        self.assertEqual(timestamps[middle], 1339795840)
        self.assertEqual(c.tracks[timestamps[middle]].lat, 49.886054)
        self.assertEqual(c.tracks[timestamps[middle]].lon, -97.132061)
        self.assertEqual(c.tracks[timestamps[middle]].ele, 199.5)
        self.assertEqual(timestamps[-2], 1339795904)
        self.assertEqual(c.tracks[timestamps[-2]].lat, 49.885123)
        self.assertEqual(c.tracks[timestamps[-2]].lon, -97.136603)
        self.assertEqual(c.tracks[timestamps[-2]].ele, 195.60000610351562)
        self.assertEqual(timestamps[-1], 1339795905)
        self.assertEqual(c.tracks[timestamps[-1]].lat, 49.885108)
        self.assertEqual(c.tracks[timestamps[-1]].lon, -97.136677)
        self.assertEqual(c.tracks[timestamps[-1]].ele, 195.6999969482422)

    def test_csvfile_missing_alt(self):
        self.mod.Champlain.Coordinate.new_full = Mock
        self.mod.Coordinates = Mock()
        csv = join(self.data_dir, 'missing_alt.csv')
        c = self.mod.CSVFile(csv)
        timestamps = sorted(c.tracks)
        self.assertEqual(len(timestamps), 10)
        middle = len(timestamps) // 2
        self.assertEqual(timestamps[0], 1339795704)
        self.assertEqual(c.tracks[timestamps[0]].lat, 49.887554)
        self.assertEqual(c.tracks[timestamps[0]].lon, -97.131041)
        self.assertEqual(c.tracks[timestamps[0]].ele, 0)
        self.assertEqual(timestamps[1], 1339795705)
        self.assertEqual(c.tracks[timestamps[1]].lat, 49.887552)
        self.assertEqual(c.tracks[timestamps[1]].lon, -97.130966)
        self.assertEqual(c.tracks[timestamps[1]].ele, 0)
        self.assertEqual(timestamps[middle], 1339795751)
        self.assertEqual(c.tracks[timestamps[middle]].lat, 49.887298)
        self.assertEqual(c.tracks[timestamps[middle]].lon, -97.130747)
        self.assertEqual(c.tracks[timestamps[middle]].ele, 0)
        self.assertEqual(timestamps[-2], 1339795756)
        self.assertEqual(c.tracks[timestamps[-2]].lat, 49.887204)
        self.assertEqual(c.tracks[timestamps[-2]].lon, -97.130554)
        self.assertEqual(c.tracks[timestamps[-2]].ele, 0)
        self.assertEqual(timestamps[-1], 1339795760)
        self.assertEqual(c.tracks[timestamps[-1]].lat, 49.887156)
        self.assertEqual(c.tracks[timestamps[-1]].lon, -97.13052)
        self.assertEqual(c.tracks[timestamps[-1]].ele, 0)

    def test_csvfile_minimal(self, filename='minimal.csv'):
        self.mod.Champlain.Coordinate.new_full = Mock
        self.mod.Coordinates = Mock()
        csv = join(self.data_dir, filename)
        c = self.mod.CSVFile(csv)
        timestamps = sorted(c.tracks)
        self.assertEqual(len(timestamps), 3)
        self.assertEqual(timestamps[0], 1339792700)
        self.assertEqual(c.tracks[timestamps[0]].lat, 49.885583)
        self.assertEqual(c.tracks[timestamps[0]].lon, -97.151421)
        self.assertEqual(c.tracks[timestamps[0]].ele, 0)
        self.assertEqual(timestamps[1], 1339792701)
        self.assertEqual(c.tracks[timestamps[1]].lat, 49.885524)
        self.assertEqual(c.tracks[timestamps[1]].lon, -97.151472)
        self.assertEqual(c.tracks[timestamps[1]].ele, 0)
        self.assertEqual(timestamps[2], 1339792702)
        self.assertEqual(c.tracks[timestamps[2]].lat, 49.885576)
        self.assertEqual(c.tracks[timestamps[2]].lon, -97.151397)
        self.assertEqual(c.tracks[timestamps[2]].ele, 0)

    def test_csvfile_invalid(self):
        self.test_csvfile_minimal('invalid.csv')

    def test_csvfile_invalid2(self):
        self.test_csvfile_minimal('invalid2.csv')
