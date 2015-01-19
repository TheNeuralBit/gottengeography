"""Test the classes and functions defined by gg/drag.py"""

from mock import Mock, call

from tests import BaseTestCase


class DragTestCase(BaseTestCase):
    filename = 'drag'

    def setUp(self):
        super().setUp()
        self.mod.Widgets = Mock()
        self.mod.MapView = Mock()
        self.mod.Photograph = Mock()

    def test_dragcontroller_init(self):
        """Ensure we can initialize the DragController."""
        files = Mock()
        drag = self.mod.DragController(files)
        w = self.mod.Widgets
        w.photos_view.enable_model_drag_source.assert_called_once_with(
            self.mod.Gdk.ModifierType.BUTTON1_MASK,
            [],
            self.mod.Gdk.DragAction.COPY)
        w.photos_view.drag_source_add_text_targets.assert_called_once_with()
        w.photos_view.connect.assert_called_once_with(
            'drag-data-get', drag.photo_drag_start)
        w.photo_camera_gps.drag_dest_set.assert_called_once_with(
            self.mod.Gtk.DestDefaults.ALL, [], self.mod.Gdk.DragAction.COPY)
        w.photo_camera_gps.drag_dest_add_text_targets.assert_called_once_with()
        w.photo_camera_gps.connect.assert_called_once_with(
            'drag-data-received', drag.photo_drag_end, False)
        w.map_container.drag_dest_set(
            self.mod.Gtk.DestDefaults.ALL, [], self.mod.Gdk.DragAction.COPY)
        w.map_container.drag_dest_add_text_targets.assert_called_once_with()
        w.map_container.connect.assert_called_once_with(
            'drag-data-received', drag.photo_drag_end, True)
        self.assertEqual(drag.external_drag, True)
        self.assertEqual(
            drag.selection, w.photos_view.get_selection.return_value)
        self.assertEqual(drag.open_files, files)

    def test_dragcontroller_photo_drag_start(self):
        """Ensure we can begin dragging photos."""
        data = Mock()
        self.mod.selected = [
            Mock(filename='foo.jpg'),
            Mock(filename='bar.jpg'),
        ]
        drag = self.mod.DragController(None)
        drag.photo_drag_start(None, None, data, None, None)
        self.assertFalse(drag.external_drag)
        data.set_text.assert_called_once_with('foo.jpg\nbar.jpg', -1)

    def test_dragcontroller_photo_drag_end(self):
        """Ensure we can respond to dropped files."""
        photo = self.mod.Photograph.cache.get.return_value
        open_files = Mock()
        drag = self.mod.DragController(open_files)
        x = Mock()
        y = Mock()
        data = Mock()
        data.get_text.return_value = 'a.jpg\nb.jpg\nc.jpg'
        drag.photo_drag_end(None, None, x, y, data, None, None, True)
        self.mod.MapView.y_to_latitude.assert_called_once_with(y)
        self.mod.MapView.x_to_longitude.assert_called_once_with(x)
        open_files.assert_called_once_with(['a.jpg', 'b.jpg', 'c.jpg'])
        expected = [
            call(self.mod.MapView.y_to_latitude.return_value,
                 self.mod.MapView.x_to_longitude.return_value),
        ] * 3
        for i, kall in enumerate(expected):
            self.assertEqual(photo.set_location.mock_calls[i], kall)

    def test_dragcontroller_photo_drag_end_blank(self):
        """Ensure we ignore invalid drops."""
        photo = self.mod.Photograph.cache.get.return_value
        open_files = Mock()
        drag = self.mod.DragController(open_files)
        data = Mock()
        data.get_text.return_value = ''
        drag.photo_drag_end(None, None, None, None, data, None, None, False)
        self.assertEqual(self.mod.MapView.y_to_latitude.mock_calls, [])
        self.assertEqual(self.mod.MapView.x_to_longitude.mock_calls, [])
        self.assertEqual(photo.set_location.mock_calls, [])
