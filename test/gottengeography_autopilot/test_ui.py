# Author: Robert Park <robru@gottengeography.ca>, (C) 2013
# Copyright: See COPYING file included with this distribution.

from autopilot.matchers import Eventually
from gottengeography_autopilot import GottenGeographyTestCase
from testtools.matchers import Equals, NotEquals


class UITests(GottenGeographyTestCase):

    def setUp(self):
        super(UITests, self).setUp()

    def test_search_bar(self):
        search_box = self.get_widget('GtkEntry', BuilderName='search_box')
        self.pointer.click_object(search_box)
        self.keyboard.type('Edmonton, Al')
