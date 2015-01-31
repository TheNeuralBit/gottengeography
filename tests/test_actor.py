"""Test the classes and functions defined by gg/actor.py"""

from mock import Mock, call

from tests import BaseTestCase


class ActorTestCase(BaseTestCase):
    filename = 'actor'

    def setUp(self):
        super().setUp()
        self.mod.Gtk.RadioMenuItem.__init__ = Mock()
        self.mod.Gtk.RadioMenuItem.set_label = Mock()
        self.mod.Gtk.RadioMenuItem.connect = Mock()
        self.mod.Widgets = Mock()
        self.mod.Gst = Mock()

    def test_radiomenuitem(self):
        """Ensure we can create a RadioMenuItem."""
        source = Mock()
        self.mod.RadioMenuItem.cache.clear()
        rmi = self.mod.RadioMenuItem(source)
        self.mod.Gtk.RadioMenuItem.__init__.assert_called_once_with(rmi)
        rmi.set_label.assert_called_once_with(source.get_name.return_value)
        rmi.connect.assert_called_once_with(
            'activate', rmi.menu_item_clicked, source.get_id.return_value)
        self.mod.Widgets.map_source_menu.append.assert_called_once_with(rmi)
        self.mod.RadioMenuItem(Mock())
        rmi.set_property.assert_called_once_with('group', rmi)

    def test_radiomenuitem_menu_item_clicked(self):
        """Ensure we set the map when a map source is clicked."""
        map_id = Mock()
        source = Mock()
        self.mod.MAP_SOURCES = {map_id: source}
        rmi = self.mod.RadioMenuItem(Mock())
        rmi.menu_item_clicked(None, map_id)
        self.mod.MapView.set_map_source.assert_called_once_with(source)

    def test_sources(self):
        """Ensure we can initialize the map source menu."""
        self.mod.Gst.get_string.return_value = 'osm-mapnik'
        self.mod.RadioMenuItem = Mock()
        self.mod.Sources.__init__()
        self.mod.Gst.get_string.assert_called_once_with('map-source-id')
        expected = [call(v) for k, v in sorted(self.mod.MAP_SOURCES.items())]
        expected = expected[:4] + [call().set_active(True)] + expected[4:]
        self.assertEqual(len(expected), len(self.mod.RadioMenuItem.mock_calls))
        for i, exp in enumerate(expected):
            self.assertEqual(self.mod.RadioMenuItem.mock_calls[i], exp)
