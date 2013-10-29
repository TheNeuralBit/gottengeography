# Author: Robert Park <robru@gottengeography.ca>, (C) 2013
# Copyright: See COPYING file included with this distribution.

from gottengeography_autopilot import GottenGeographyTestCase
from autopilot.matchers import Eventually
from testtools.matchers import Equals
from time import sleep


class UITests(GottenGeographyTestCase):
    def setUp(self):
        super(UITests, self).setUp()
        self.search_box = self.get_widget(
            'GtkEntry', BuilderName='search_box')

    def test_find_edmonton(self):
        self.search_for('Edmo')
        self.assertThat(
            self.main_window.get_properties()['title'],
            Eventually(Equals('Edmonton, Alberta, Canada')))

        self.search_for('Victoria, Bri')
        self.assertThat(
            self.main_window.get_properties()['title'],
            Eventually(Equals('Victoria, British Columbia, Canada')))

        self.search_for('Bost')
        self.assertThat(
            self.main_window.get_properties()['title'],
            Eventually(Equals('Sandbostel, Lower Saxony, Germany')))

    def search_for(self, string):
        # Triple click to select any existing text
        for i in range(3):
            self.pointer.click_object(self.search_box)
        self.keyboard.type(string)
        sleep(1)

        # Click the first result in the drop-down.
        x, y = self.pointer.position()
        self.pointer.move(x, y+20)
        self.pointer.click()
        sleep(1)
