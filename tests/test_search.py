"""Test the classes and functions defined by gg/search.py"""

from mock import Mock, call

from tests import BaseTestCase


class SearchTestCase(BaseTestCase):
    filename = 'search'

    def setUp(self):
        super().setUp()
        self.mod.Widgets = Mock()
        self.controller = self.mod.SearchController()

    def test_search_init(self):
        """Ensure we can set up searching."""
        self.mod.Gtk.ListStore.new.assert_called_once_with([str, float, float])
        self.mod.Gtk.EntryCompletion.new.assert_called_once_with()
        search = self.mod.Gtk.EntryCompletion.new.return_value
        self.assertIsNone(self.controller.search)
        search.set_model.assert_called_once_with(self.controller.results)
        search.connect.assert_called_once_with(
            'match-selected', self.controller.search_completed)
        entry = self.mod.Widgets.search_box
        entry.set_completion.assert_called_once_with(search)
        self.assertEqual(4, len(entry.connect.mock_calls))

    def test_search_load_result(self):
        """Ensure we can load results into the search db."""
        searched = set()
        append = Mock()
        entry = Mock()
        entry.get_text.return_value = 'Regina'
        self.controller.load_results(entry, append, searched)
        # Exact match is there
        self.assertIn(
            call(('Regina, Saskatchewan, Canada', 50.45008, -104.6178)),
            append.mock_calls)
        # Substring match is there
        self.assertIn(
            call(('Villa Regina, Rio Negro, Argentina', -39.1, -67.06667)),
            append.mock_calls)
        # Anything with 'reg' is also there
        self.assertIn(
            call(('Waregem, Flemish, Belgium', 50.88898, 3.42756)),
            append.mock_calls)
        self.assertEqual(len(append.mock_calls), 265)
        self.assertEqual(searched, set(['reg']))

    def test_search_load_result_cache(self):
        """Ensure we can search against cached results."""
        searched = set(['reg'])
        append = Mock()
        entry = Mock()
        entry.get_text.return_value = 'Regina'
        self.controller.load_results(entry, append, searched)
        self.assertEqual(append.mock_calls, [])

    def test_search_search_completed(self):
        """Ensure we can jump to selected search results."""
        entry = Mock()
        model = Mock()
        model.get.return_value = [1, 2]
        itr = Mock()
        self.controller.search_completed(entry, model, itr)
        self.mod.MapView.emit.assert_called_once_with('realize')
        self.mod.Widgets.redraw_interface.assert_called_once_with()
        model.get.assert_called_once_with(
            itr, self.mod.LATITUDE, self.mod.LONGITUDE)
        self.mod.MapView.center_on.assert_called_once_with(1, 2)

    def test_search_repeat_last_search(self):
        """Ensure we can jump back to previous search results."""
        entry = Mock()
        model = Mock()
        self.controller.last_search = 'foo'
        self.controller.search_completed = Mock()
        self.controller.repeat_last_search(entry, model)
        self.controller.search_completed.assert_called_once_with(
            entry, model, 'foo')
