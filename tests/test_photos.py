"""Test the classes and functions defined by gg/photos.py"""

from mock import Mock

from tests import BaseTestCase


class point:
    def __init__(self, lat, lon, ele):
        self.lat = lat
        self.lon = lon
        self.ele = ele


class PhotosTestCase(BaseTestCase):
    filename = 'photos'

    def setUp(self):
        super().setUp()
        self.mod.TrackFile = Mock()

    def test_auto_timestamp_comparison_exact(self):
        self.mod.points = {
            1: point(0, 0, 0),
            2: point(1, 1, 1),
            3: point(2, 2, 2),
        }
        self.mod.TrackFile.range = [1, 3]
        photo = Mock()
        photo.manual = False
        photo.timestamp = 3
        self.mod.auto_timestamp_comparison(photo)
        photo.set_location.assert_called_once_with(2, 2, 2)

    def test_auto_timestamp_comparison_interpolate(self):
        self.mod.points = {
            1: point(0, 0, 0),
            4: point(1, 10, 100),
        }
        self.mod.TrackFile.range = [1, 4]
        photo = Mock()
        photo.manual = False
        photo.timestamp = 3
        self.mod.auto_timestamp_comparison(photo)
        self.assertAlmostEqual(photo.set_location.mock_calls[0][1][0], 2/3, 7)
        self.assertAlmostEqual(photo.set_location.mock_calls[0][1][1], 20/3, 7)
        self.assertAlmostEqual(photo.set_location.mock_calls[0][1][2], 200/3, 7)

    def test_auto_timestamp_comparison_interpolate_2(self):
        self.mod.points = {
            1420254516: point(0, 0, 0),
            1420254518: point(100, 50, 800),
        }
        self.mod.TrackFile.range = [1420254516, 1420254518]
        photo = Mock()
        photo.manual = False
        photo.timestamp = 1420254517
        self.mod.auto_timestamp_comparison(photo)
        photo.set_location.assert_called_once_with(50, 25, 400)

    def test_auto_timestamp_comparison_manual(self):
        self.mod.TrackFile.range = [1, 4]
        photo = Mock()
        photo.manual = True
        photo.timestamp = 3
        self.mod.auto_timestamp_comparison(photo)
        self.assertEqual(photo.set_location.mock_calls, [])
