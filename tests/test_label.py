"""Test the classes and functions defined by gg/label.py"""

from mock import Mock, call

from tests import BaseTestCase


class LabelTestCase(BaseTestCase):
    filename = 'label'

    def setUp(self):
        super().setUp()
        self.mod.Widgets = Mock()
        self.mod.Binding = Mock()
        self.mod.MarkerLayer = Mock()
        self.mod.basename = Mock(return_value='bar.jpg')
        self.mod.Clutter.ModifierType.CONTROL_MASK = 5

    def test_clicked_ctrl_unselect(self):
        """Ensure that Ctrl+clicking a selected label deselects it."""
        label = Mock()
        label.get_name.return_value = label.photo.filename = 'foo.jpg'
        event = Mock()
        event.get_state.return_value = 5
        self.mod.clicked(label, event)
        event.get_state.assert_called_once_with()
        label.get_selected.assert_called_once_with()
        self.mod.Widgets.photos_selection.unselect_iter\
            .assert_called_once_with(label.photo.iter)
        self.mod.Widgets.photos_view.scroll_to_cell\
            .assert_called_once_with(
                self.mod.Widgets.loaded_photos.get_path.return_value)

    def test_clicked_ctrl_select(self):
        """Ensure that Ctrl+clicking an unselected label selects it."""
        label = Mock()
        label.get_name.return_value = label.photo.filename = 'foo.jpg'
        label.get_selected.return_value = False
        event = Mock()
        event.get_state.return_value = 5
        self.mod.clicked(label, event)
        event.get_state.assert_called_once_with()
        label.get_selected.assert_called_once_with()
        self.mod.Widgets.photos_selection.select_iter\
            .assert_called_once_with(label.photo.iter)
        self.mod.Widgets.photos_view.scroll_to_cell\
            .assert_called_once_with(
                self.mod.Widgets.loaded_photos.get_path.return_value)

    def test_clicked_select(self):
        """Ensure that clicking a label selects only it."""
        label = Mock()
        label.get_name.return_value = label.photo.filename = 'foo.jpg'
        label.get_selected.return_value = False
        event = Mock()
        event.get_state.return_value = 0
        self.mod.clicked(label, event)
        event.get_state.assert_called_once_with()
        self.mod.Widgets.photos_selection.unselect_all\
            .assert_called_once_with()
        self.mod.Widgets.photos_selection.select_iter\
            .assert_called_once_with(label.photo.iter)
        self.mod.Widgets.photos_view.scroll_to_cell\
            .assert_called_once_with(
                self.mod.Widgets.loaded_photos.get_path.return_value)

    def test_hover(self):
        """Ensure we can scale labels on hover."""
        label = Mock()
        label.get_scale.return_value = (1, 2, 3)
        self.mod.hover(label, Mock(), 2)
        label.get_scale.assert_called_once_with()
        label.set_scale.assert_called_once_with(2, 4, 6)

    def test_label_init(self):
        """Ensure we can initialize Labels."""
        photo = Mock()
        label = self.mod.Label(photo)
        self.assertEqual(label.photo, photo)
        label.set_name.assert_called_once_with(photo.filename)
        label.set_text.assert_called_once_with('bar.jpg')
        bidi = self.mod.GObject.BindingFlags.BIDIRECTIONAL
        expected = [
            call(photo, 'latitude', label, flags=bidi),
            call(photo, 'longitude', label, flags=bidi),
            call(photo, 'positioned', label, 'visible'),
        ]
        for i, kall in enumerate(expected):
            self.assertEqual(self.mod.Binding.mock_calls[i], kall)

    def test_label_set_highlight(self):
        """Ensure we can control the highlight when selecting labels."""
        photo = Mock()
        label = self.mod.Label(photo)
        highlight = True
        transparent = True
        label.set_highlight(highlight, transparent)
        label.set_scale.assert_called_once_with(1.1, 1.1)
        label.set_selected.assert_called_once_with(True)
        label.set_opacity.assert_called_once_with(255)
        label.raise_top.assert_called_once_with()

    def test_label_destroy(self):
        """Ensure we can unload labels."""
        photo = Mock()
        label = self.mod.Label(photo)
        self.assertIn(photo, self.mod.Label.cache)
        label.destroy()
        self.assertNotIn(photo, self.mod.Label.cache)
        label.unmap.assert_called_once_with()
        self.mod.Champlain.Label.destroy.assert_called_once_with(label)
