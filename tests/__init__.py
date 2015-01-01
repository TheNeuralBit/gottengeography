"""Define the base class for all GottenGeography tests."""

import os
import sys
import glob
import unittest
import importlib.machinery

from mock import Mock


class null:
    pass


class BaseTestCase(unittest.TestCase):
    root_dir = os.path.dirname(os.path.dirname(__file__))
    gg_dir = os.path.join(root_dir, 'gg')

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
        giMock.Champlain.PathLayer = null
        sys.modules['gi.repository'] = giMock
        for fname in glob.glob(self.pyfile('*')):
            modname = os.path.basename(fname.replace('.py', ''))
            sys.modules['gg.' + modname] = Mock()
        self.mod = importlib.machinery.SourceFileLoader(
            'gg.' + self.filename, os.path.join(self.pyfile(self.filename))
        ).load_module()
