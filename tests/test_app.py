"""Test the classes and functions defined by gg/app.py"""

from mock import Mock
from os.path import abspath

from tests import BaseTestCase


class AppTestCase(BaseTestCase):
    filename = 'app'

    def setUp(self):
        super().setUp()

    def test_constants(self):
        self.assertEqual(self.mod.PATH, 0)
        self.assertEqual(self.mod.SUMMARY, 1)
        self.assertEqual(self.mod.THUMB, 2)
        self.assertEqual(self.mod.TIMESTAMP, 3)

    def test_command_line_blank(self):
        app, commands = Mock(), Mock()
        commands.get_arguments.return_value = ['appname']
        self.assertEqual(self.mod.command_line(app, commands), 0)
        self.assertEqual(app.activate.mock_calls, [])
        self.assertEqual(app.open_files.mock_calls, [])

    def test_command_line_files(self):
        app, commands = Mock(), Mock()
        args = commands.get_arguments.return_value = [
            'appname', 'pic.jpg', 'gps.xml']
        self.assertEqual(self.mod.command_line(app, commands), 0)
        app.activate.assert_called_once_with()
        app.open_files.assert_called_once_with([abspath(f) for f in args[1:]])
