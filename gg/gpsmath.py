# Author: Robert Park <rbpark@exolucere.ca>, (C) 2010
# Copyright: See COPYING file included with this distribution.

"""Reverse geocoding and other mathematical calculations."""


from gi.repository import GLib, GObject
from time import strftime, localtime
from math import modf as split_float
from gettext import gettext as _
from os.path import join
import fractions

from .territories import get_state, get_country
from .build_info import PKG_DATA_DIR
from .common import memoize


def valid_coords(lat, lon):
    """Determine the validity of coordinates.
    
    >>> valid_coords(200, 300)
    False
    >>> valid_coords(40.689167, -74.044678)
    True
    >>> valid_coords(50, [])
    False
    """
    if type(lat) not in (float, int): return False
    if type(lon) not in (float, int): return False
    return abs(lat) <= 90 and abs(lon) <= 180


@memoize
def do_cached_lookup(key):
    """Scan cities.txt for the nearest town.
    
    >>> do_cached_lookup(GeoCacheKey(43.646424, -79.333426))
    ('Toronto', '08', 'CA', 'America/Toronto\\n')
    >>> do_cached_lookup(GeoCacheKey(48.440257, -89.204443))
    ('Thunder Bay', '08', 'CA', 'America/Thunder_Bay\\n')
    """
    near, dist = None, float('inf')
    lat1, lon1 = key.lat, key.lon
    with open(join(PKG_DATA_DIR, 'cities.txt')) as cities:
        for city in cities:
            name, lat2, lon2, country, state, tz = city.split('\t')
            x = (float(lon2) - lon1)
            y = (float(lat2) - lat1)
            delta = x * x + y * y
            if delta < dist:
                dist = delta
                near = (name, state, country, tz)
    return near


class GeoCacheKey:
    """This class allows fuzzy geodata cache lookups."""
    
    def __init__(self, lat, lon):
        self.key = '%.2f,%.2f' % (lat, lon)
        self.lat = lat
        self.lon = lon
    
    def __str__(self):
        """Show the key being used.
        
        >>> print(GeoCacheKey(53.564, -113.564))
        53.56,-113.56
        """
        return self.key
    
    def __hash__(self):
        """Different instances can be used to fetch dictionary values.
        
        >>> cache = { GeoCacheKey(53.564, -113.564): 'example' }
        >>> cache.get(GeoCacheKey(53.559, -113.560))
        'example'
        >>> cache.get(GeoCacheKey(0, 0), 'Missing')
        'Missing'
        """
        return hash(self.key)
    
    def __cmp__(self, other):
        """Different instances can compare equally.
        
        >>> GeoCacheKey(10.004, 10.004) == GeoCacheKey(9.996, 9.996)
        True
        >>> GeoCacheKey(10.004, 10.004) == GeoCacheKey(0, 0)
        False
        """
        return cmp(self.key, other.key)


class Coordinates(GObject.GObject):
    """A generic object containing latitude and longitude coordinates.
    
    >>> import os, time
    >>> os.environ['TZ'] = 'America/Winnipeg'
    >>> time.tzset()
    >>> coord = Coordinates()
    
    >>> coord.date
    >>> coord.timestamp = 60 * 60 * 24 * 365 * 50
    >>> coord.date
    '2019-12-19 06:00:00 PM'
    
    >>> coord.height
    >>> coord.altitude = 600
    >>> coord.height
    '600.0m above sea level'
    >>> coord.altitude = -100
    >>> coord.height
    '100.0m below sea level'
    
    >>> coord.positioned
    False
    >>> coord.coords
    >>> coord.latitude = -51.688687
    >>> coord.longitude = -57.804152
    >>> coord.coords
    'S 51.68869, W 57.80415'
    >>> coord.positioned
    True
    
    >>> coord.lookup_geodata()
    'Atlantic/Stanley'
    >>> coord.geoname
    'Stanley, Falkland Islands'
    """
    modified_timeout = None
    timeout_seconds = 0
    geotimezone = ''
    names = (None, None, None)
    
    timestamp = GObject.property(type=int)
    altitude  = GObject.property(type=float)
    latitude  = GObject.property(type=float, minimum=-90.0,  maximum=90.0)
    longitude = GObject.property(type=float, minimum=-180.0, maximum=180.0)
    
    @GObject.property(type=bool, default=False)
    def positioned(self):
        """Identify if this instance occupies a valid point on the map.
        
        Returns False at 0,0 because it's actually remarkably difficult to
        achieve that exact point in a natural way (not to mention it's in the
        middle of the Atlantic), which means the photo hasn't been placed yet.
        """
        return bool(self.latitude or self.longitude)
    
    @GObject.property(type=str)
    def geoname(self):
        """Report the city, state, and country in a pretty list."""
        return ', '.join([name for name in self.names if name])
    
    @GObject.property(type=str)
    def date(self):
        """Convert epoch seconds to a human-readable date."""
        if self.timestamp:
            return strftime('%Y-%m-%d %X', localtime(self.timestamp))
    
    @GObject.property(type=str)
    def coords(self):
        """Report a nicely formatted latitude and longitude pair."""
        if self.positioned:
            lat, lon = self.latitude, self.longitude
            return '%s %.5f, %s %.5f' % (
                _('N') if lat >= 0 else _('S'), abs(lat),
                _('E') if lon >= 0 else _('W'), abs(lon)
            )
    
    @GObject.property(type=str)
    def height(self):
        """Convert elevation into a human readable format."""
        if self.altitude:
            return '%.1f%s' % (abs(self.altitude), _('m above sea level')
                        if self.altitude >= 0 else _('m below sea level'))
    
    def __init__(self, **props):
        self.filename = ''
        
        GObject.GObject.__init__(self, **props)
        
        for prop in ('latitude', 'longitude', 'altitude', 'timestamp'):
            self.connect('notify::' + prop, self.do_modified)
    
    def __str__(self):
        """Plaintext summary of metadata.
        
        >>> coord = Coordinates()
        >>> print(coord)
        <BLANKLINE>
        >>> coord.altitude = 456.7
        >>> coord.latitude = 10
        >>> coord.lookup_geodata()
        'Africa/Accra'
        >>> print(coord)
        Yendi, Ghana
        N 10.00000, E 0.00000
        456.7m above sea level
        """
        return '\n'.join([s for s in
            (self.geoname, self.date, self.coords, self.height) if s])
    
    def lookup_geodata(self):
        """Check the cache for geonames, and notify of any changes.
        
        >>> coord = Coordinates()
        >>> coord.lookup_geodata()
        >>> coord.latitude = 47.56494
        >>> coord.longitude = -52.70931
        >>> coord.lookup_geodata()
        'America/St_Johns'
        >>> coord.geoname
        "St. John's, Newfoundland and Labrador, Canada"
        """
        if not self.positioned:
            return
        
        old_geoname = self.geoname
        city, state, code, tz = do_cached_lookup(
            GeoCacheKey(self.latitude, self.longitude))
        self.names = (city, get_state(code, state), get_country(code))
        self.geotimezone = tz.strip()
        if self.geoname != old_geoname:
            self.notify('geoname')
        
        return self.geotimezone
    
    def do_modified(self, *ignore):
        """Set timer to update the geoname after all modifications are done.
        
        >>> coord = Coordinates()
        >>> type(coord.modified_timeout)
        <class 'NoneType'>
        >>> coord.latitude = 10
        >>> type(coord.modified_timeout)
        <class 'int'>
        """
        self.notify('positioned')
        self.notify('coords')
        if not self.modified_timeout:
            self.modified_timeout = GLib.timeout_add_seconds(
                self.timeout_seconds, self.update_derived_properties)
    
    def update_derived_properties(self):
        """Do expensive geodata lookups after the timeout.
        
        >>> coord = Coordinates()
        >>> coord.latitude = 10
        >>> type(coord.modified_timeout)
        <class 'int'>
        >>> coord.update_derived_properties()
        False
        >>> type(coord.modified_timeout)
        <class 'NoneType'>
        >>> coord.geoname
        'Yendi, Ghana'
        """
        if self.modified_timeout:
            self.notify('positioned')
            GLib.source_remove(self.modified_timeout)
            self.lookup_geodata()
            self.modified_timeout = None
        return False

