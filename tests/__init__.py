"""Define the base class for all GottenGeography tests."""

import os
import sys
import unittest
import importlib.machinery

from mock import Mock


class null:
    pass


class BaseTestCase(unittest.TestCase):
    root_dir = os.path.dirname(os.path.dirname(__file__))
    gg_dir = os.path.join(root_dir, 'gg')
    test_dir = os.path.join(root_dir, 'tests')
    data_dir = os.path.join(test_dir, 'data')
    demo_dir = os.path.join(root_dir, 'demo')

    filename = None
    mod = None

    def pyfile(self, modname):
        """Locate a python source file given the module name."""
        return os.path.join(self.gg_dir, modname + '.py')

    def setUp(self):
        """MOCK ALL THE THINGS!"""
        super().setUp()
        giMock = Mock()
        # When we define a class that inherits from a mocked class, our class
        # becomes a useless mock. Some classes need to be defined to be empty
        # so that we can inherit from them and then just mock specific methods.
        giMock.Champlain.Label = null
        giMock.Champlain.Label.destroy = Mock()
        giMock.Champlain.Label.get_property = Mock()
        giMock.Champlain.Label.raise_top = Mock()
        giMock.Champlain.Label.set_draggable = Mock()
        giMock.Champlain.Label.set_name = Mock()
        giMock.Champlain.Label.set_opacity = Mock()
        giMock.Champlain.Label.set_property = Mock()
        giMock.Champlain.Label.set_scale = Mock()
        giMock.Champlain.Label.set_selectable = Mock()
        giMock.Champlain.Label.set_selected = Mock()
        giMock.Champlain.Label.set_text = Mock()
        giMock.Champlain.Label.unmap = Mock()
        giMock.Champlain.PathLayer = null
        giMock.Champlain.PathLayer.set_stroke_width = Mock()
        giMock.Champlain.PathLayer.add_node = Mock()
        giMock.Gio.Settings = null
        giMock.Gio.Settings.__init__ = Mock()
        giMock.Gio.Settings.__getitem__ = Mock()
        giMock.Gio.Settings.bind = Mock()
        giMock.Gio.Settings.connect = Mock()
        giMock.Gio.Settings.get_int = Mock()
        giMock.Gio.Settings.get_string = Mock()
        giMock.Gio.Settings.get_value = Mock()
        giMock.Gio.Settings.set_value = Mock()
        giMock.GObject.Binding = null
        giMock.GObject.GObject = null
        giMock.Gtk.Builder = null
        giMock.Gtk.Builder.get_object = Mock()
        giMock.Gtk.RadioMenuItem = null
        giMock.Gtk.RadioMenuItem.__init__ = Mock()
        giMock.Gtk.RadioMenuItem.set_label = Mock()
        giMock.Gtk.RadioMenuItem.get_active = Mock()
        giMock.GtkChamplain.Embed = null
        giMock.GtkChamplain.Embed.get_view = Mock()
        sys.modules['gi.repository'] = giMock
        spMock = Mock()
        spMock.Popen.return_value.communicate.return_value.__getitem__ = Mock()
        sys.modules['subprocess'] = spMock
        self.mod = importlib.machinery.SourceFileLoader(
            'gg.' + self.filename, os.path.join(self.pyfile(self.filename))
        ).load_module()
