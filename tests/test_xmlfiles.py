"""Test the classes and functions defined by gg/xmlfiles.py"""

from mock import Mock, call
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

    def test_trackfile_update_range(self):
        self.mod.TrackFile.range = [9, 10]
        self.mod.TrackFile.instances = ['something']
        self.mod.points = [1, 2, 3]
        self.mod.TrackFile.update_range()
        self.mod.Widgets.empty_trackfile_list.hide.assert_called_once_with()
        self.assertEqual(self.mod.TrackFile.range, [1, 3])

    def test_trackfile_update_range_empty(self):
        self.mod.TrackFile.range = [9, 10]
        self.mod.points = [1, 2, 3]
        self.mod.TrackFile.update_range()
        self.mod.Widgets.empty_trackfile_list.show.assert_called_once_with()
        self.assertEqual(self.mod.TrackFile.range, [])

    def test_trackfile_get_bounding_box(self):
        class tf:
            polygons = [Mock(), Mock()]
        self.mod.TrackFile.instances = [tf]
        bounds = self.mod.TrackFile.get_bounding_box()
        self.mod.Champlain.BoundingBox.new.assert_called_once_with()
        self.assertEqual(bounds.compose.mock_calls, [
            call(tf.polygons[0].get_bounding_box.return_value),
            call(tf.polygons[1].get_bounding_box.return_value),
        ])

    def test_trackfile_query_all_timezones(self):
        class tf:
            class start:
                geotimezone = 'hello'
        self.mod.TrackFile.instances = [tf]
        self.assertEqual(self.mod.TrackFile.query_all_timezones(), 'hello')

    def test_trackfile_query_all_timezones_none(self):
        self.mod.TrackFile.instances = []
        self.assertIsNone(self.mod.TrackFile.query_all_timezones())
        class tf:
            class start:
                geotimezone = None
        self.mod.TrackFile.instances = [tf]
        self.assertIsNone(self.mod.TrackFile.query_all_timezones())

    def test_trackfile_clear_all(self):
        self.mod.points = Mock()
        self.mod.TrackFile.instances = tf = [Mock()]
        self.mod.TrackFile.clear_all()
        tf[0].destroy.assert_called_once_with()
        self.mod.points.clear.assert_called_once_with()

    def test_trackfile_load_from_file(self):
        times = [2, 1]
        self.mod.clock = lambda: times.pop()
        self.mod.Camera = Mock()
        self.mod.GPXFile = Mock()
        self.mod.GPXFile.return_value.tracks = [1, 2, 3]
        self.mod.Widgets = Mock()
        self.mod.TrackFile.get_bounding_box = Mock()
        self.mod.TrackFile.instances = Mock()
        self.mod.TrackFile.update_range = Mock()
        self.mod.TrackFile.load_from_file('foo.gpx')
        self.mod.GPXFile.assert_called_once_with('foo.gpx')
        self.mod.Widgets.status_message.assert_called_once_with(
            '3 points loaded in 1.00s.', True)
        self.mod.TrackFile.instances.add.assert_called_once_with(
            self.mod.GPXFile.return_value)
        self.mod.MapView.emit.assert_called_once_with('realize')
        self.mod.MapView.get_max_zoom_level.assert_called_once_with()
        self.mod.MapView.set_zoom_level.assert_called_once_with(
            self.mod.MapView.get_max_zoom_level.return_value)
        self.mod.MapView.ensure_visible.assert_called_once_with(
            self.mod.TrackFile.get_bounding_box.return_value, False)
        self.mod.TrackFile.update_range.assert_called_once_with()
        self.mod.Camera.set_all_found_timezone.assert_called_once_with(
            self.mod.GPXFile.return_value.start.geotimezone)

    def test_trackfile_load_from_file_keyerror(self):
        with self.assertRaises(OSError):
            self.mod.TrackFile.load_from_file('foo.unsupported')

    def test_trackfile_load_from_file_no_tracks(self):
        self.mod.GPXFile = Mock()
        self.mod.GPXFile.return_value.tracks = [1]
        self.mod.TrackFile.update_range = Mock()
        self.mod.TrackFile.load_from_file('foo.gpx')
        self.assertEqual(self.mod.MapView.emit.mock_calls, [])
        self.assertEqual(self.mod.MapView.ensure_visible.mock_calls, [])
        self.assertEqual(self.mod.TrackFile.update_range.mock_calls, [])

    def test_gpxfile(self, filename='minimal.gpx'):
        self.mod.Champlain.Coordinate.new_full = Mock
        self.mod.Coordinates = Mock()
        gpx = join(self.data_dir, filename)
        g = self.mod.GPXFile(gpx)
        timestamps = sorted(g.tracks)
        self.assertEqual(len(timestamps), 3)
        self.assertEqual(timestamps[0], 1287259751)
        self.assertEqual(g.tracks[timestamps[0]].lat, 53.52263)
        self.assertEqual(g.tracks[timestamps[0]].lon, -113.448979)
        self.assertEqual(g.tracks[timestamps[0]].ele, 671.666)
        self.assertEqual(timestamps[1], 1287259753)
        self.assertEqual(g.tracks[timestamps[1]].lat, 53.522731)
        self.assertEqual(g.tracks[timestamps[1]].lon, -113.448985)
        self.assertEqual(g.tracks[timestamps[1]].ele, 671.092)
        self.assertEqual(timestamps[2], 1287259755)
        self.assertEqual(g.tracks[timestamps[2]].lat, 53.52283)
        self.assertEqual(g.tracks[timestamps[2]].lon, -113.448985)
        self.assertEqual(g.tracks[timestamps[2]].ele, 671.307)

    def test_gpxfile_unusual(self):
        self.test_gpxfile('unusual.gpx')

    def test_gpxfile_invalid(self):
        self.test_gpxfile('invalid.gpx')

    def test_tcxfile(self):
        self.mod.Champlain.Coordinate.new_full = Mock
        self.mod.Coordinates = Mock()
        tcx = join(self.data_dir, 'sample.tcx')
        t = self.mod.TCXFile(tcx)
        timestamps = sorted(t.tracks)
        self.assertEqual(len(timestamps), 9)
        middle = len(timestamps) // 2
        self.assertEqual(timestamps[0], 1235221063)
        self.assertEqual(t.tracks[timestamps[0]].lat, 52.148514)
        self.assertEqual(t.tracks[timestamps[0]].lon, 4.500887)
        self.assertEqual(t.tracks[timestamps[0]].ele, -91.731)
        self.assertEqual(timestamps[1], 1235221067)
        self.assertEqual(t.tracks[timestamps[1]].lat, 52.148326)
        self.assertEqual(t.tracks[timestamps[1]].lon, 4.500603)
        self.assertEqual(t.tracks[timestamps[1]].ele, -90.795)
        self.assertEqual(timestamps[middle], 1235229207)
        self.assertEqual(t.tracks[timestamps[middle]].lat, 52.148655)
        self.assertEqual(t.tracks[timestamps[middle]].lon, 4.504016)
        self.assertEqual(t.tracks[timestamps[middle]].ele, 2.33)
        self.assertEqual(timestamps[-2], 1235229241)
        self.assertEqual(t.tracks[timestamps[-2]].lat, 52.149542)
        self.assertEqual(t.tracks[timestamps[-2]].lon, 4.502316)
        self.assertEqual(t.tracks[timestamps[-2]].ele, 2.443)
        self.assertEqual(timestamps[-1], 1235229253)
        self.assertEqual(t.tracks[timestamps[-1]].lat, 52.149317)
        self.assertEqual(t.tracks[timestamps[-1]].lon, 4.50191)
        self.assertEqual(t.tracks[timestamps[-1]].ele, 2.803)

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

    def test_kmlfile_invalid(self):
        self.test_kmlfile('invalid.kml')

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
