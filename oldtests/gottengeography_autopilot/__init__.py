# Author: Robert Park <robru@gottengeography.ca>, (C) 2013
# Copyright: See COPYING file included with this distribution.

from autopilot.input import Pointer, Touch
from autopilot.testcase import AutopilotTestCase


class GottenGeographyTestCase(AutopilotTestCase):
    """A base class for interacting with GottenGeography."""

    def setUp(self):
        super(GottenGeographyTestCase, self).setUp()
        self.pointer = Pointer(Touch.create())
        self.app = self.launch_gg()
        self.main_window = self.get_widget('GtkApplicationWindow')

    def get_widget(self, *args, **kwargs):
        return self.app.select_single(*args, **kwargs)

    def launch_gg(self):
        """Launch from source tree if possible, or system otherwise."""
        for path in ('../gottengeography', 'gottengeography'):
            try:
                print('Launching app as ' + path)
                return self.launch_test_application(path, app_type='gtk')
            except:
                continue
        self.fail('Could not launch GottenGeography.')
