"""Test the classes and functions defined by gg/xmlfiles.py"""

from mock import Mock

from tests import BaseTestCase


class XmlFilesTestCase(BaseTestCase):
    filename = 'xmlfiles'

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
