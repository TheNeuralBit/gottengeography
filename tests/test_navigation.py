"""Test the classes and functions defined by gg/navigation.py"""

from mock import Mock

from tests import BaseTestCase


class NavigationTestCase(BaseTestCase):
    filename = 'navigation'

    def setUp(self):
        super().setUp()
        self.mod.MapView = Mock()
        self.mod.Gst = Mock()

    def test_move_by_arrow_keys_up(self):
        """Ensure we can navigate with the Up arrow key."""
        keyval = Mock()
        self.mod.valid_coords = Mock(return_value=True)
        self.mod.Gdk.keyval_name.return_value = 'Up'
        self.mod.MapView.get_height.return_value = 2
        self.mod.MapView.get_width.return_value = 4
        self.mod.move_by_arrow_keys(
            Mock(), Mock(), keyval, Mock())
        self.mod.Gdk.keyval_name.assert_called_once_with(keyval)
        self.mod.MapView.y_to_latitude.assert_called_once_with(0.9)  # 0.45*2
        self.mod.MapView.get_center_longitude.assert_called_once_with()
        self.mod.MapView.center_on.assert_called_once_with(
            self.mod.MapView.y_to_latitude.return_value,
            self.mod.MapView.get_center_longitude.return_value)

    def test_move_by_arrow_keys_right(self):
        """Ensure we can navigate with the Right arrow key."""
        keyval = Mock()
        self.mod.valid_coords = Mock(return_value=True)
        self.mod.Gdk.keyval_name.return_value = 'Right'
        self.mod.MapView.get_height.return_value = 2
        self.mod.MapView.get_width.return_value = 4
        self.mod.move_by_arrow_keys(
            Mock(), Mock(), keyval, Mock())
        self.mod.Gdk.keyval_name.assert_called_once_with(keyval)
        self.mod.MapView.x_to_longitude.assert_called_once_with(2.2)  # 0.55*4
        self.mod.MapView.get_center_latitude.assert_called_once_with()
        self.mod.MapView.center_on.assert_called_once_with(
            self.mod.MapView.get_center_latitude.return_value,
            self.mod.MapView.x_to_longitude.return_value)

    def test_remember_location(self):
        """Ensure we can record the current location in the history stack."""
        self.mod.Gst.get.return_value = ['hi'] * 50
        view = Mock()
        view.get_property = lambda x: x
        self.mod.remember_location(view)
        self.mod.Gst.set_history.assert_called_once_with(
            (['hi'] * 29) + [('latitude', 'longitude', 'zoom-level')])

    def test_go_back(self):
        """Ensure we can go back to the previous entry in the history stack."""
        self.mod.Gst.get.return_value = [('lat', 'lon', 'zoom')]
        self.mod.valid_coords = Mock(return_value=True)
        self.mod.go_back()
        self.mod.MapView.set_zoom_level.assert_called_once_with('zoom')
        self.mod.MapView.center_on.assert_called_once_with('lat', 'lon')
        self.mod.Gst.reset.assert_called_once_with('history')

    def test_go_back_with_history(self):
        """Ensure we preserve the remaining history stack when going back."""
        self.mod.Gst.get.return_value = [('lat', 'lon', 'zoom')] * 3
        self.mod.valid_coords = Mock(return_value=True)
        self.mod.go_back()
        self.mod.MapView.set_zoom_level.assert_called_once_with('zoom')
        self.mod.MapView.center_on.assert_called_once_with('lat', 'lon')
        self.mod.Gst.set_history.assert_called_once_with([
            ('lat', 'lon', 'zoom'), ('lat', 'lon', 'zoom')])

    def test_zoom_button_sensitivity(self):
        """Ensure we set the zoom button sensitivity."""
        view = Mock()
        in_sensitive = Mock()
        out_sensitive = Mock()
        self.mod.zoom_button_sensitivity(
            view, None, in_sensitive, out_sensitive)
        out_sensitive.assert_called_once_with(True)
        in_sensitive.assert_called_once_with(True)
