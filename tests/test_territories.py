"""Test the classes and functions defined by gg/territories.py"""

from tests import BaseTestCase


class TerritoriesTestCase(BaseTestCase):
    filename = 'territories'

    def setUp(self):
        super().setUp()

    def test_countries(self):
        self.assertEqual(self.mod.countries['CA'], 'Canada')
        self.assertEqual(self.mod.get_country('MT'), 'Malta')
        self.assertIsNone(self.mod.get_country('Narnia'))

    def test_territories(self):
        self.assertEqual(self.mod.territories['CA.02'], 'British Columbia')
        self.assertEqual(self.mod.get_state('CA', '01'), 'Alberta')
        self.assertEqual(self.mod.get_state('US', 'WI'), 'Wisconsin')
        self.assertIsNone(self.mod.get_state('US', 'Fakerson'))

    def test_zones(self):
        self.assertIn('Atlantic', self.mod.zones)
        self.assertIn('Pacific', self.mod.zones)
        self.assertIn('America', self.mod.tz_regions)
