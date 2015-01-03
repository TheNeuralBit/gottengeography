"""Test the classes and functions defined by gg/photos.py"""

from mock import Mock

from tests import BaseTestCase


class point:
    def __init__(self, lat, lon, ele):
        self.lat = lat
        self.lon = lon
        self.ele = ele


class GError(Exception):
    pass


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
        mock_call = photo.set_location.mock_calls[0][1]
        self.assertAlmostEqual(mock_call[0], 2/3, 7)
        self.assertAlmostEqual(mock_call[1], 20/3, 7)
        self.assertAlmostEqual(mock_call[2], 200/3, 7)

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

    def test_fetch_thumbnail(self, orient=1, pixbuf=None, args=None):
        new = self.mod.GdkPixbuf.Pixbuf.new_from_file_at_size
        new_args = ['foo.jpg', 100, 100]
        pixbuf = pixbuf or new
        args = [new.return_value] + args if args else new_args
        self.mod.GExiv2.Metadata.return_value.__getitem__ = Mock(
            return_value=orient)
        thumb = self.mod.fetch_thumbnail('foo.jpg', size=100)
        self.mod.GExiv2.Metadata.assert_called_once_with('foo.jpg')
        new.assert_called_once_with(*new_args)
        self.assertEqual(thumb, pixbuf.return_value)
        pixbuf.assert_called_once_with(*args)

    def test_fetch_thumbnail_orient_2(self):
        self.test_fetch_thumbnail(
            orient=2,
            args=[False],
            pixbuf=self.mod.GdkPixbuf.Pixbuf.flip)

    def test_fetch_thumbnail_orient_3(self):
        self.test_fetch_thumbnail(
            orient=3,
            args=[self.mod.GdkPixbuf.PixbufRotation.UPSIDEDOWN],
            pixbuf=self.mod.GdkPixbuf.Pixbuf.rotate_simple)

    def test_fetch_thumbnail_orient_4(self):
        self.test_fetch_thumbnail(
            orient=4,
            args=[True],
            pixbuf=self.mod.GdkPixbuf.Pixbuf.flip)

    def test_fetch_thumbnail_orient_6(self):
        self.test_fetch_thumbnail(
            orient=6,
            args=[self.mod.GdkPixbuf.PixbufRotation.CLOCKWISE],
            pixbuf=self.mod.GdkPixbuf.Pixbuf.rotate_simple)

    def test_fetch_thumbnail_orient_8(self):
        self.test_fetch_thumbnail(
            orient=8,
            args=[self.mod.GdkPixbuf.PixbufRotation.COUNTERCLOCKWISE],
            pixbuf=self.mod.GdkPixbuf.Pixbuf.rotate_simple)

    def test_fetch_thumbnail_gerror(self):
        self.mod.GExiv2.Metadata.side_effect = self.mod.GObject.GError = GError
        with self.assertRaisesRegexp(OSError, 'No thumbnail found.'):
            self.mod.fetch_thumbnail('foo.jpg', size=100)

    def test_fetch_thumbnail_gerror2(self):
        m = self.mod.GExiv2.Metadata.return_value
        m.__getitem__ = Mock(return_value=1)
        m.get_preview_properties.return_value.__getitem__ = Mock()
        m.get_preview_image.side_effect = GError
        self.mod.GdkPixbuf.Pixbuf.new_from_file_at_size.side_effect = GError
        self.mod.GObject.GError = GError
        with self.assertRaisesRegexp(OSError, 'No thumbnail found.'):
            self.mod.fetch_thumbnail('foo.jpg', size=100)

    def test_fetch_thumbnail_gerror3(self):
        m = self.mod.GExiv2.Metadata.return_value
        m.__getitem__ = Mock(return_value=1)
        m.get_preview_properties.return_value.__getitem__ = Mock()
        self.mod.GdkPixbuf.Pixbuf.new_from_file_at_size.side_effect = GError
        self.mod.GObject.GError = GError
        thumb = self.mod.fetch_thumbnail('foo.jpg', size=100)
        stream = self.mod.GdkPixbuf.Pixbuf.new_from_stream_at_scale
        self.assertEqual(thumb, stream.return_value)
        stream.assert_called_once_with(
            self.mod.Gio.MemoryInputStream.new_from_data.return_value,
            100, 100, True, None)

    def test_photograph_resize_all_photos(self):
        gst = Mock()
        gst.get_int.return_value = 150
        p = Mock()
        self.mod.Photograph.instances = [p]
        self.mod.fetch_thumbnail = Mock()
        self.mod.Photograph.resize_all_photos(gst, 'size')
        gst.get_int.assert_called_once_with('size')
        self.assertEqual(p.thumb, self.mod.fetch_thumbnail.return_value)
        self.mod.fetch_thumbnail.assert_called_once_with(p.filename, 150)
        self.mod.Widgets.loaded_photos.set_value.assert_called_once_with(
            p.iter, 2, p.thumb)

    def test_photograph_load_from_file(self):
        load = self.mod.Photograph.load_from_file
        self.mod.Photograph = Mock()
        p = self.mod.Photograph.return_value
        self.mod.Label = Mock()
        self.mod.Camera = Mock()
        self.mod.Camera.generate_id.return_value = ('Nikon', 'Nikonos')
        c = self.mod.Camera.return_value
        self.mod.CameraView = Mock()
        c.timezone_method = 'lookup'
        self.mod.Widgets = Mock()
        self.assertEqual(load('zing.jpg'), p)
        self.mod.Photograph.assert_called_once_with('zing.jpg')
        self.mod.Label.assert_called_once_with(p)
        p.read.assert_called_once_with()
        self.mod.Widgets.empty_camera_list.hide.assert_called_once_with()
        self.mod.Camera.generate_id.assert_called_once_with(p.camera_info)
        self.mod.Camera.assert_called_once_with('Nikon')
        c.add_photo.assert_called_once_with(p)
        self.mod.CameraView.assert_called_once_with(c, 'Nikonos')
        p.calculate_timestamp.assert_called_once_with(c.offset)
        self.mod.Widgets.button_sensitivity.assert_called_once_with()
