"""Test the classes and functions defined by gg/common.py"""

from mock import Mock

from tests import BaseTestCase

print_ = Mock()


class CommonTestCase(BaseTestCase):
    filename = 'common'

    def setUp(self):
        super().setUp()
        print_.reset_mock()

    def test_singleton(self):
        """Ensure we can define classes that have only one instance."""
        @self.mod.singleton
        class Highlander:
            pass
        self.assertEqual(Highlander(), Highlander)
        self.assertIs(Highlander(), Highlander)
        self.assertEqual(id(Highlander()), id(Highlander))

    def test_memoize_function(self):
        """Ensure we can define functions that cache return values."""
        @self.mod.memoize
        def doubler(foo):
            print_('Expensive calculation!')
            return foo * 2
        self.assertEqual(doubler(50), 100)
        self.assertEqual(doubler(50), 100)
        print_.assert_called_once_with('Expensive calculation!')  # Once!

    def test_memoize_class(self):
        """Ensure we can define classes that cache instances."""
        @self.mod.memoize
        class Memorable:
            def __init__(self, foo):
                print_('Expensive calculation!')
        self.assertIs(Memorable('alpha'), Memorable('alpha'))
        self.assertIsNot(Memorable('alpha'), Memorable('beta'))
        self.assertEqual(len(Memorable.instances), 2)
        self.assertEqual(print_.call_count, 2)

    def test_binding(self):
        """Ensure we can bind GObject properties to GSettings keys."""
        m = self.mod.GObject.Binding.__init__ = Mock()
        b = self.mod.Binding('foo', 'bar', 'grill')
        m.assert_called_once_with(
            b, source='foo', source_property='bar', target='grill',
            target_property='bar', flags=self.mod.GObject.BindingFlags.DEFAULT)
