# Author: Robert Park <robru@gottengeography.ca>, (C) 2010
# Copyright: See COPYING file included with this distribution.

"""Class for loading and saving photographs."""


from gi.repository import GtkClutter
GtkClutter.init([])

from gi.repository import Gdk, GdkPixbuf, GExiv2
from gi.repository import Gio, GObject
from datetime import datetime
from os.path import basename
from time import mktime
from os import stat, utime

from gg.label import Label
from gg.widgets import Widgets
from gg.xmlfiles import TrackFile
from gg.gpsmath import Coordinates
from gg.camera import Camera, CameraView
from gg.common import Gst, memoize, staticmethod, ignored, points, modified


# Prefixes for common EXIF keys.
IPTC = 'Iptc.Application2.'


# This defines the transformations used by the Exif.Image.Orientation tag.
ROTATIONS = {
    2: lambda thumb:
        GdkPixbuf.Pixbuf.flip(thumb, False),

    3: lambda thumb:
        GdkPixbuf.Pixbuf.rotate_simple(thumb,
            GdkPixbuf.PixbufRotation.UPSIDEDOWN),

    4: lambda thumb:
        GdkPixbuf.Pixbuf.flip(thumb, True),

    5: lambda thumb:
        GdkPixbuf.Pixbuf.flip(
            GdkPixbuf.Pixbuf.rotate_simple(thumb,
                GdkPixbuf.PixbufRotation.CLOCKWISE), True),

    6: lambda thumb:
        GdkPixbuf.Pixbuf.rotate_simple(thumb,
            GdkPixbuf.PixbufRotation.CLOCKWISE),

    7: lambda thumb:
        GdkPixbuf.Pixbuf.flip(
            GdkPixbuf.Pixbuf.rotate_simple(thumb,
                GdkPixbuf.PixbufRotation.CLOCKWISE), False),

    8: lambda thumb:
        GdkPixbuf.Pixbuf.rotate_simple(thumb,
            GdkPixbuf.PixbufRotation.COUNTERCLOCKWISE),
}


# This function is the embodiment of my applications core logic.
# Everything else is just implementation details.
def auto_timestamp_comparison(photo):
    """Use GPX data to calculate photo coordinates and elevation."""
    if photo.manual or len(TrackFile.range) < 2:
        return

    # Clamp the timestamp within the range of available GPX points.
    # The result is in epoch seconds, just like the keys of the 'points' dict.
    stamp = sorted(TrackFile.range + [photo.timestamp])[1]

    try:
        point = points[stamp] # Try to use an exact match,
        lat   = point.lat     # if such a thing were to exist.
        lon   = point.lon     # It's more likely than you think. 50%
        ele   = point.ele     # of the included demo data matches here.

    except KeyError:
        # Find the two points that are nearest (in time) to the photo.
        hi = min([p for p in points if p > stamp])
        lo = max([p for p in points if p < stamp])
        hi_point = points[hi]
        lo_point = points[lo]
        hi_ratio = (stamp - lo) / (hi - lo)  # Proportional amount of time
        lo_ratio = (hi - stamp) / (hi - lo)  # between each point & the photo.

        # Find intermediate values using the proportional ratios.
        lat = ((lo_point.lat * lo_ratio)  +
               (hi_point.lat * hi_ratio))
        lon = ((lo_point.lon * lo_ratio)  +
               (hi_point.lon * hi_ratio))
        ele = ((lo_point.ele * lo_ratio)  +
               (hi_point.ele * hi_ratio))

    photo.set_location(lat, lon, ele)

def fetch_thumbnail(filename, size=Gst.get_int('thumbnail-size'), orient=1):
    """Load a photo's thumbnail from disk

    >>> fetch_thumbnail('gg/widgets.py')
    Traceback (most recent call last):
    OSError: gg/widgets.py: No thumbnail found.
    >>> type(fetch_thumbnail('demo/IMG_2411.JPG'))
    <class 'gi.repository.GdkPixbuf.Pixbuf'>
    """
    try:
        exif = GExiv2.Metadata(filename)
    except GObject.GError:
        raise OSError('{}: No thumbnail found.'.format(filename))

    with ignored(KeyError, ValueError):
        orient = int(exif['Exif.Image.Orientation'])

    try:
        thumb = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, size, size)
    except GObject.GError:
        try:
            preview = exif.get_preview_properties()
            data = exif.get_preview_image(preview[0]).get_data()
        except (IndexError, GObject.GError):
            raise OSError('{}: No thumbnail found.'.format(filename))

        return GdkPixbuf.Pixbuf.new_from_stream_at_scale(
            Gio.MemoryInputStream.new_from_data(data, None),
            size, size, True, None)

    return ROTATIONS.get(orient, lambda x: x)(thumb)


@memoize
class Photograph(Coordinates):
    """Represents a single photograph and it's location in space and time.

    >>> import os, time
    >>> os.environ['TZ'] = 'America/Winnipeg'
    >>> time.tzset()
    >>> photo = Photograph('demo/IMG_2411.JPG')
    >>> photo.latitude  = -10.0
    >>> photo.longitude = -10.0
    >>> photo.altitude = -10.20005
    >>> photo.timestamp = 999999999
    >>> photo.lookup_geodata()
    'Atlantic/St_Helena'
    >>> print(photo)
    <span size="larger">IMG_2411.JPG</span>
    <span style="italic" size="smaller">Georgetown, Ascension, Saint Helena
    2001-09-08 08:46:39 PM
    S 10.00000, W 10.00000
    10.2m below sea level</span>
    >>> modified.add(photo)
    >>> print(photo)
    <b><span size="larger">IMG_2411.JPG</span>
    <span style="italic" size="smaller">Georgetown, Ascension, Saint Helena
    2001-09-08 08:46:39 PM
    S 10.00000, W 10.00000
    10.2m below sea level</span></b>
    """
    camera_info = None
    orig_time = None
    manual = False
    camera = None
    label = None
    exif = None
    iter = None

    @staticmethod
    def resize_all_photos(gst, key):
        """Reload all the thumbnails when the GSetting changes."""
        # TODO: There's probably a more GObjecty way to do this with properties
        # TODO: Is it necessary to reload every time? Probably could just load
        # the max size to start and then scale it down to the requested size on
        # the fly. But this works for now.
        size = gst.get_int(key)
        for photo in Photograph.instances:
            photo.thumb = fetch_thumbnail(photo.filename, size)
            Widgets.loaded_photos.set_value(photo.iter, 2, photo.thumb)

    @staticmethod
    def load_from_file(uri):
        """Coordinates instantiation of various classes.

        Ensures that related Photograph, Camera, CameraView, and Label are all
        instantiated together.
        """
        photo = Photograph(uri)

        Label(photo)

        photo.read()

        Widgets.empty_camera_list.hide()

        camera_id, camera_name = Camera.generate_id(photo.camera_info)
        camera = Camera(camera_id)
        camera.add_photo(photo)

        CameraView(camera, camera_name)

        # If the user has selected the lookup method, then the timestamp
        # was probably calculated incorrectly the first time (before the
        # timezone was discovered). So call it again to get the correct value.
        if camera.timezone_method == 'lookup':
            photo.calculate_timestamp(camera.offset)

        Widgets.button_sensitivity()

        return photo

    def __init__(self, filename):
        """Raises OSError for invalid file types.

        This MUST be the case in order to avoid the @memoize cache getting
        filled up with invalid Photograph instances.
        """
        Coordinates.__init__(self)
        self.thumb = fetch_thumbnail(filename)
        self.filename = filename

        self.connect('notify::geoname', self.update_liststore_summary)
        self.connect('notify::positioned', Widgets.button_sensitivity)

    def __str__(self):
        """Long summary of photo metadata with Pango markup."""
        summary = '<span {}>{}</span>\n<span {}>{}</span>'.format(
            'size="larger"', basename(self.filename),
            'style="italic" size="smaller"', Coordinates.__str__(self))
        return '<b>{}</b>'.format(summary) if self in modified else summary

    def read(self):
        """Discard all state and (re)initialize from disk."""
        self.exif = GExiv2.Metadata(self.filename)
        self.manual = False
        self.modified_timeout = None
        self.latitude = 0.0
        self.longitude = 0.0
        self.altitude = 0.0
        self.timestamp = 0

        self.names = (None, None, None)
        self.geotimezone = ''

        for tag in ('Exif.Photo.DateTimeOriginal',
                    'Exif.Image.DateTimeOriginal',
                    'Exif.Photo.DateTime',
                    'Exif.Image.DateTime'):
            with ignored(TypeError, AttributeError, ValueError):
                self.orig_time = datetime.strptime(
                    self.exif.get(tag),
                    '%Y:%m:%d %H:%M:%S').timetuple()
                break

        self.longitude, self.latitude, self.altitude = self.exif.get_gps_info()

        modified.discard(self)
        self.calculate_timestamp()

        if self.iter is None:
            self.iter = Widgets.loaded_photos.append()
        Widgets.loaded_photos.set_row(self.iter, [self.filename,
                                                  str(self),
                                                  self.thumb,
                                                  self.timestamp])

        # Get the camera info
        self.camera_info = {'Make': '', 'Model': ''}
        keys = ['Exif.Image.' + key for key in list(self.camera_info.keys())
                    + ['CameraSerialNumber']] + ['Exif.Photo.BodySerialNumber']
        for key in keys:
            with ignored(KeyError):
                self.camera_info.update(
                    {key.split('.')[-1]: self.exif[key]})

    def calculate_timestamp(self, offset=0):
        """Determine the timestamp based on the currently selected timezone.

        This method relies on the TZ environment variable to be set before
        it is called. If you don't set TZ before calling this method, then it
        implicitely assumes that the camera and the computer are set to the
        same timezone.
        """
        try:
            self.timestamp = int(mktime(self.orig_time))
        except TypeError:
            self.timestamp = int(stat(self.filename).st_mtime)
        self.timestamp += offset
        auto_timestamp_comparison(self)

    def write(self):
        """Save exif data to photo file on disk."""
        times = stat(self.filename)
        self.exif.set_gps_info(self.longitude, self.latitude, self.altitude)
        self.exif[IPTC + 'City']          = self.names[0] or ''
        self.exif[IPTC + 'ProvinceState'] = self.names[1] or ''
        self.exif[IPTC + 'CountryName']   = self.names[2] or ''
        self.exif['Iptc.Envelope.CharacterSet'] = '\x1b%G'
        self.exif.save_file()
        utime(self.filename, (times.st_atime, times.st_mtime))
        modified.discard(self)
        Widgets.loaded_photos.set_value(self.iter, 1, str(self))

    def disable_auto_position(self):
        """Indicate that the user has manually positioned the photo.

        This prevents it from snapping to any available GPS data automatically.
        """
        self.manual = True

    def set_location(self, lat, lon, ele=None):
        """Alter the coordinates of this photo."""
        modified.add(self)
        if ele is not None:
            self.altitude = ele
        self.latitude  = lat
        self.longitude = lon

    def get_large_preview(self):
        """Return a GdkPixbuf that is 80% of the screen's shortest dimension."""
        screen = Gdk.Screen.get_default()
        return fetch_thumbnail(self.filename,
            int(min(screen.get_width(), screen.get_height()) * 0.8))

    def update_liststore_summary(self, *ignore):
        """Update the text displayed in the GtkListStore."""
        if self.iter is not None:
            Widgets.loaded_photos.set_value(self.iter, 1, str(self))
        if self.camera and self.camera.found_timezone is not self.geotimezone:
            self.camera.found_timezone = self.geotimezone

    def destroy(self):
        """Agony!"""
        self.update_derived_properties() # To clear any callback...
        # TODO: Disconnect this from here
        if self in Label.cache:
            Label(self).destroy()
        if self.camera is not None:
            self.camera.remove_photo(self)
        modified.discard(self)
        if self.iter:
            Widgets.loaded_photos.remove(self.iter)
        del Photograph.cache[self.filename]
