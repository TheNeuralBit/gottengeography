# GottenGeography - Automagically geotags photos by comparing timestamps to GPX data
# Copyright (C) 2010 Robert Park <rbpark@exolucere.ca>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division

from version import APPNAME, PACKAGE, VERSION

import gettext
gettext.bindtextdomain(PACKAGE)
gettext.textdomain(PACKAGE)

from gi.repository import GObject, GtkClutter, Clutter

GObject.threads_init()
GObject.set_prgname(PACKAGE)
GtkClutter.init([])

from gi.repository import Gtk, Gdk, GdkPixbuf
from gi.repository import GtkChamplain, Champlain
from re import compile as re_compile, IGNORECASE
from os.path import basename, abspath
from time import tzset, sleep, clock
from gettext import gettext as _
from urlparse import urlparse
from os import environ
from sys import argv

# "If I have seen a little further it is by standing on the shoulders of Giants."
#                                    --- Isaac Newton

from files import Photograph, GPXFile, KMLFile
from utils import format_list, format_coords, valid_coords
from utils import make_clutter_color, get_file, map_sources
from utils import GSettingsSetting, Coordinates, Polygon, Struct
from territories import tz_regions, get_timezone, get_state, get_country

# Handy names for GtkListStore column numbers.
PATH, SUMMARY, THUMB, TIMESTAMP = range(4)
LOCATION, LATITUDE, LONGITUDE = range(3)

builder = Gtk.Builder()
builder.set_translation_domain(PACKAGE)
builder.add_from_file(get_file(PACKAGE + '.ui'))
get_obj = builder.get_object

gsettings = GSettingsSetting('ca.exolucere.' + PACKAGE)
gst_get = gsettings.get_value
gst_set = gsettings.set_value
bind_with_convert = gsettings.bind_with_convert
bind = gsettings.bind

# This function embodies almost the entirety of my application's logic.
# The things that come after this method are just implementation details.
def auto_timestamp_comparison(photo, points, metadata):
    """Use GPX data to calculate photo coordinates and elevation.
    
    photo:    A Photograph object.
    points:   A dictionary mapping epoch seconds to ChamplainCoordinates.
    metadata: A Struct object defining clock offset and first/last points.
    """
    if photo.manual or len(points) < 2:
        return
    
    # Add the user-specified clock offset (metadata.delta) to the photo
    # timestamp, and then keep it within the range of available GPX points.
    # The result is in epoch seconds, just like the keys of the 'points' dict.
    stamp = min(max(
        metadata.delta + photo.timestamp,
        metadata.alpha),
        metadata.omega)
    
    try:
        point = points[stamp] # Try to use an exact match,
        lat   = point.lat     # if such a thing were to exist.
        lon   = point.lon     # It's more likely than you think. 50%
        ele   = point.ele     # of the included demo data matches here.
    
    except KeyError:
        # Find the two points that are nearest (in time) to the photo.
        hi = min([point for point in points if point > stamp])
        lo = max([point for point in points if point < stamp])
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


class CommonAttributes:
    """Define attributes required by all Controller classes.
    
    This class is never instantiated, it is only inherited by classes that
    need to manipulate the map, or the loaded photos.
    """
    champlain = GtkChamplain.Embed()
    map_view  = champlain.get_view()
    slide_to  = map_view.go_to
    metadata  = Struct()
    selected  = set()
    modified  = set()
    polygons  = []
    tracks    = {}
    photo     = {}


class NavigationController(CommonAttributes):
    """Controls how users navigate the map."""
    
    def __init__(self):
        """Start the map at the previous location, and connect signals."""
        perform_zoom    = lambda button, zoom: zoom()
        back_button     = get_obj("back_button")
        zoom_in_button  = get_obj("zoom_in_button")
        zoom_out_button = get_obj("zoom_out_button")
        zoom_out_button.connect("clicked", perform_zoom, self.map_view.zoom_out)
        zoom_in_button.connect("clicked", perform_zoom, self.map_view.zoom_in)
        back_button.connect("clicked", self.go_back, self.map_view)
        
        for key in ['latitude', 'longitude', 'zoom-level']:
            bind(key, self.map_view, key)
        
        accel = Gtk.AccelGroup()
        window = get_obj("main")
        window.add_accel_group(accel)
        for key in [ 'Left', 'Right', 'Up', 'Down' ]:
            accel.connect(Gdk.keyval_from_name(key),
                Gdk.ModifierType.MOD1_MASK, 0, self.move_by_arrow_keys)
        self.map_view.connect("notify::zoom-level", self.zoom_button_sensitivity,
            zoom_in_button, zoom_out_button)
        self.map_view.connect("realize", self.remember_location)
        self.map_view.connect("animation-completed", self.set_window_title,
            window.set_title, Coordinates())
        self.map_view.emit("animation-completed")
    
    def set_window_title(self, map_view, set_title, center):
        """Add the current location we are looking at into the titlebar."""
        center.latitude  = map_view.get_center_latitude()
        center.longitude = map_view.get_center_longitude()
        center.lookup_geoname()
        set_title("%s - %s" % (APPNAME, center.pretty_geoname(False)))
    
    def move_by_arrow_keys(self, accel_group, acceleratable, keyval, modifier):
        """Move the map view by 5% of its length in the given direction."""
        key, view = Gdk.keyval_name(keyval), self.map_view
        factor    = (0.45 if key in ("Up", "Left") else 0.55)
        if key in ("Up", "Down"):
            lat = view.y_to_latitude(view.get_height() * factor)
            lon = view.get_property('longitude')
        else:
            lat = view.get_property('latitude')
            lon = view.x_to_longitude(view.get_width() * factor)
        if valid_coords(lat, lon):
            view.center_on(lat, lon)
    
    def remember_location(self, view):
        """Add current location to history stack."""
        history = list(gst_get('history'))
        location = [view.get_property(x) for x in
            ('latitude', 'longitude', 'zoom-level')]
        if history[-1] != location:
            history.append(location)
        gst_set('history', history[-30:])
    
    def go_back(self, button, view):
        """Return the map view to where the user last set it."""
        history = list(gst_get('history'))
        lat, lon, zoom = history.pop()
        if valid_coords(lat, lon):
            view.set_zoom_level(zoom)
            view.center_on(lat, lon)
        if len(history) > 1:
            gst_set('history', history)
        else:
            gsettings.reset('history')
        self.map_view.emit("animation-completed")
    
    def zoom_button_sensitivity(self, view, signal, zoom_in, zoom_out):
        """Ensure zoom buttons are only sensitive when they need to be."""
        zoom = view.get_zoom_level()
        zoom_out.set_sensitive(view.get_min_zoom_level() != zoom)
        zoom_in.set_sensitive( view.get_max_zoom_level() != zoom)


class SearchController(CommonAttributes):
    """Controls the behavior for searching the map."""
    last_search = None
    
    def __init__(self):
        """Make the search box and insert it into the window."""
        self.results = get_obj("search_results")
        search = get_obj("search_completion")
        search.set_match_func(
            lambda c, s, itr, get: self.search(get(itr, LOCATION) or ""),
            self.results.get_value)
        search.connect("match-selected", self.search_completed, self.map_view)
        entry = get_obj("search_box")
        entry.connect("changed", self.load_results, self.results.append)
        entry.connect("icon-release", lambda entry, i, e: entry.set_text(''))
        entry.connect("activate", self.repeat_last_search, self.results, self.map_view)
    
    def load_results(self, entry, append, searched=set()):
        """Load a few search results based on what's been typed.
        
        Requires at least three letters typed, and is careful not to load
        duplicate results.
        
        The searched argument persists across calls to this method, and should
        not be passed as an argument unless your intention is to trigger the
        loading of duplicate results.
        """
        text  = entry.get_text().lower()
        three = text[0:3]
        self.search, search = [ re_compile('(^|\s)' + string,
            flags=IGNORECASE).search for string in (text, three) ]
        if len(three) == 3 and three not in searched:
            searched.add(three)
            with open(get_file("cities.txt")) as cities:
                for line in cities:
                    city, lat, lon, country, state, tz = line.split("\t")
                    if search(city):
                        state    = get_state(country, state)
                        country  = get_country(country)
                        location = format_list([city, state, country])
                        append([location, float(lat), float(lon)])
    
    def search_completed(self, entry, model, itr, view):
        """Go to the selected location."""
        self.last_search = itr.copy()
        self.map_view.emit("realize")
        view.set_zoom_level(11)
        self.slide_to(*model.get(itr, LATITUDE, LONGITUDE))
    
    def repeat_last_search(self, entry, model, view):
        """Snap back to the last-searched location when user hits enter key."""
        if self.last_search is not None:
            self.search_completed(entry, model, self.last_search, view)


class PreferencesController(CommonAttributes):
    """Controls the behavior of the preferences dialog."""
    gpx_timezone = ''
    
    def __init__(self):
        self.region = region = get_obj("timezone_region")
        self.cities = cities = get_obj("timezone_cities")
        pref_button = get_obj("pref_button")
        
        for name in tz_regions:
            region.append(name, name)
        region.connect("changed", self.region_handler, cities)
        cities.connect("changed", self.cities_handler, region)
        bind("timezone-region", region, 'active')
        bind("timezone-cities", cities, 'active')
        
        self.colorpicker = get_obj("colorselection")
        bind_with_convert("track-color", self.colorpicker, "current-color",
            lambda x: Gdk.Color(*x), lambda x: (x.red, x.green, x.blue))
        self.colorpicker.connect("color-changed", self.track_color_changed, self.polygons)
        
        radio_group = []
        map_menu = get_obj("map_source_menu")
        bind_with_convert("map-source-id", self.map_view, "map-source",
            map_sources.get, lambda x: x.get_id())
        last_source = self.map_view.get_map_source().get_id()
        for i, source_id in enumerate(sorted(map_sources.keys())):
            source = map_sources[source_id]
            menu_item = Gtk.RadioMenuItem.new_with_label(radio_group, source.get_name())
            radio_group.append(menu_item)
            if last_source == source_id:
                menu_item.set_active(True)
            menu_item.connect("activate", self.map_menu_clicked, source_id)
            map_menu.attach(menu_item, 0, 1, i, i+1)
        map_menu.show_all()
        
        pref_button.connect("clicked", self.preferences_dialog,
            get_obj("preferences"), region, cities, self.colorpicker)
        
        self.radios = {}
        for option in ["system", "lookup", "custom"]:
            option += "-timezone"
            radio = get_obj(option)
            radio.set_name(option)
            bind(option, radio, 'active')
            self.radios[option] = radio
            radio.connect("clicked", self.radio_handler)
        bind("custom-timezone", get_obj("custom_timezone_combos"), 'sensitive')
    
    def preferences_dialog(self, button, dialog, region, cities, colorpicker):
        """Allow the user to configure this application."""
        previous = Struct({
            'system': gsettings.get_boolean('system-timezone'),
            'lookup': gsettings.get_boolean('lookup-timezone'),
            'custom': gsettings.get_boolean('custom-timezone'),
            'region': region.get_active(),
            'city':   cities.get_active(),
            'color':  colorpicker.get_current_color()
        })
        if not dialog.run():
            colorpicker.set_current_color(previous.color)
            colorpicker.set_previous_color(previous.color)
            gsettings.set_boolean('system-timezone', previous.system)
            gsettings.set_boolean('lookup-timezone', previous.lookup)
            gsettings.set_boolean('custom-timezone', previous.custom)
            region.set_active(previous.region)
            cities.set_active(previous.city)
        dialog.hide()
    
    def set_timezone(self):
        """Set the timezone to the given zone and update all photos."""
        if "TZ" in environ:
            del environ["TZ"]
        if gsettings.get_boolean('lookup-timezone'):
            environ["TZ"] = self.gpx_timezone
        elif gsettings.get_boolean('custom-timezone'):
            region = self.region.get_active_id()
            city   = self.cities.get_active_id()
            if region is not None and city is not None:
                environ["TZ"] = "%s/%s" % (region, city)
        tzset()
        for photo in self.photo.values():
            photo.calculate_timestamp()
            auto_timestamp_comparison(photo, self.tracks, self.metadata)
    
    def radio_handler(self, radio):
        """Reposition photos depending on which timezone the user selected."""
        if radio.get_active():
            self.set_timezone()
    
    def region_handler(self, regions, cities):
        """Populate the list of cities when a continent is selected."""
        cities.remove_all()
        for city in get_timezone(regions.get_active_id(), []):
            cities.append(city, city)
    
    def cities_handler(self, cities, regions):
        """When a city is selected, update the chosen timezone."""
        if cities.get_active_id() is not None:
            self.set_timezone()
    
    def track_color_changed(self, selection, polygons):
        """Update the color of any loaded GPX tracks."""
        color = selection.get_current_color()
        one   = make_clutter_color(color)
        two   = one.lighten().lighten()
        for i, polygon in enumerate(polygons):
            polygon.set_stroke_color(two if i % 2 else one)
    
    def map_menu_clicked(self, menu_item, mapid):
        """Change the map source when the user selects a different one."""
        if menu_item.get_active():
            self.map_view.set_map_source(map_sources[mapid])


class LabelController(CommonAttributes):
    """Control the behavior and creation of ChamplainLabels."""
    
    def __init__(self):
        self.select_all = get_obj("select_all_button")
        self.selection  = get_obj("photos_view").get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.layer = Champlain.MarkerLayer()
        self.map_view.add_layer(self.layer)
        self.selection.connect("changed", self.update_highlights,
            self.map_view, self.selected, self.photo.viewvalues())
    
    def add(self, name):
        """Create a new ChamplainLabel and add it to the map."""
        label = Champlain.Label()
        label.set_name(name)
        label.set_text(basename(name))
        label.set_selectable(True)
        label.set_draggable(True)
        label.set_property('reactive', True)
        label.connect("enter-event", self.hover, 1.05)
        label.connect("leave-event", self.hover, 1/1.05)
        label.connect("drag-finish", self.drag_finish, self.photo)
        label.connect("button-press", self.clicked, self.selection,
            self.select_all, self.photo)
        self.layer.add_marker(label)
        return label
    
    def update_highlights(self, selection, view, selected, photos):
        """Ensure only the selected labels are highlighted."""
        selection_exists = selection.count_selected_rows() > 0
        selected.clear()
        for photo in photos:
            # Maintain the 'selected' set() for easier iterating later.
            if selection.iter_is_selected(photo.iter):
                selected.add(photo)
            photo.set_label_highlight(photo in selected, selection_exists)
    
    def clicked(self, label, event, selection, select_all, photos):
        """When a ChamplainLabel is clicked, select it in the GtkListStore.
        
        The interface defined by this method is consistent with the behavior of
        the GtkListStore itself in the sense that a normal click will select
        just one item, but Ctrl+clicking allows you to select multiple.
        """
        photo = photos[label.get_name()]
        assert photo.filename == label.get_name()
        if event.get_state() & Clutter.ModifierType.CONTROL_MASK:
            if label.get_selected(): selection.unselect_iter(photo.iter)
            else:                    selection.select_iter(photo.iter)
        else:
            select_all.set_active(False)
            selection.unselect_all()
            selection.select_iter(photo.iter)
    
    def drag_finish(self, label, event, photos):
        """Update photos with new locations after photos have been dragged."""
        photo = photos[label.get_name()]
        photo.set_location(label.get_latitude(), label.get_longitude())
        photo.manual = True
        self.map_view.emit("animation-completed")
    
    def hover(self, label, event, factor):
        """Scale a ChamplainLabel by the given factor."""
        label.set_scale(*[scale * factor for scale in label.get_scale()])


class ActorController(CommonAttributes):
    """Controls the behavior of the custom actors I have placed over the map."""
    
    def __init__(self):
        self.stage = self.map_view.get_stage()
        self.black = Clutter.Box.new(Clutter.BinLayout())
        self.black.set_color(Clutter.Color.new(0, 0, 0, 64))
        self.label = Clutter.Text()
        self.label.set_color(Clutter.Color.new(255, 255, 255, 255))
        self.xhair = Clutter.Rectangle.new_with_color(
            Clutter.Color.new(0, 0, 0, 64))
        for signal in [ 'latitude', 'longitude' ]:
            self.map_view.connect('notify::' + signal, self.display,
                get_obj("maps_link"), self.label)
        self.map_view.connect('notify::width',
            lambda view, param, black:
                black.set_size(view.get_width(), 30),
            self.black)
        
        scale = Champlain.Scale.new()
        scale.connect_view(self.map_view)
        self.map_view.bin_layout_add(scale,
            Clutter.BinAlignment.START, Clutter.BinAlignment.END)
        self.map_view.bin_layout_add(self.black,
            Clutter.BinAlignment.START, Clutter.BinAlignment.START)
        self.black.get_layout_manager().add(self.label,
            Clutter.BinAlignment.CENTER, Clutter.BinAlignment.CENTER)
    
    def display(self, view, param, mlink, label):
        """Display map center coordinates when they change."""
        lat, lon = [ view.get_property(x) for x in ('latitude', 'longitude') ]
        label.set_markup(format_coords(lat, lon))
        mlink.set_markup(
            '<a title="%s" href="http://maps.google.com/maps?ll=%s,%s&amp;spn=%s,%s">Google</a>'
            % (_("View in Google Maps"), lat, lon,
            lon - view.x_to_longitude(0), view.y_to_latitude(0) - lat))
    
    def animate_in(self, start=400):
        """Animate the crosshair."""
        self.map_view.bin_layout_add(self.xhair,
            Clutter.BinAlignment.CENTER, Clutter.BinAlignment.CENTER)
        self.xhair.set_z_rotation_from_gravity(45, Clutter.Gravity.CENTER)
        for i in xrange(start, 7, -1):
            self.xhair.set_size(i, i)
            opacity = 0.6407035175879398 * (400 - i) # don't ask
            for actor in [self.xhair, self.label, self.black]:
                actor.set_opacity(opacity)
            while Gtk.events_pending():
                Gtk.main_iteration()
            sleep(0.002)

class GottenGeography(CommonAttributes):
    """Provides a graphical interface to automagically geotag photos.
    
    Just load your photos, and load a GPX file, and GottenGeography will
    automatically cross-reference the timestamps on the photos to the timestamps
    in the GPX to determine the three-dimensional coordinates of each photo.
    """
    
################################################################################
# File data handling. These methods interact with files (loading, saving, etc)
################################################################################
    
    def file_dragged_in(self, widget, context, x, y, data, info, time):
        """Load files that have been dragged in."""
        self.open_files(data.get_uris())
    
    def open_files(self, files):
        """Attempt to load all of the specified files."""
        self.progressbar.show()
        invalid_files, total = [], len(files)
        # abspath is used to correct relative paths entered on the commandline,
        # urlparse is used to correct URIs given from drag&drop operations.
        for i, name in enumerate([abspath(urlparse(f).path) for f in files], 1):
            self.redraw_interface(i / total, basename(name))
            try:
                try:            self.load_img_from_file(name)
                except IOError: self.load_gpx_from_file(name)
            except IOError:
                invalid_files.append(basename(name))
        if len(invalid_files) > 0:
            self.status_message(_("Could not open: ") + format_list(invalid_files))
        self.progressbar.hide()
        self.labels.selection.emit("changed")
        self.map_view.emit("animation-completed")
    
    def load_img_from_file(self, filename):
        """Create or update a row in the ListStore.
        
        Checks if the file has already been loaded, and if not, creates a new
        row in the ListStore. Either way, it then populates that row with
        photo metadata as read from disk. Effectively, this is used both for
        loading new photos, and reverting old photos, discarding any changes.
        
        Raises IOError if filename refers to a file that is not a photograph.
        """
        photo = self.photo.get(filename) or Photograph(filename, self.modify_summary)
        photo.read()
        if filename not in self.photo:
            photo.iter           = self.liststore.append()
            photo.label          = self.labels.add(filename)
            self.photo[filename] = photo
        photo.position_label()
        self.modified.discard(photo)
        self.liststore.set_row(photo.iter,
            [filename, photo.long_summary(), photo.thumb, photo.timestamp])
        auto_timestamp_comparison(photo, self.tracks, self.metadata)
    
    def load_gpx_from_file(self, filename):
        """Parse GPX data, drawing each GPS track segment on the map."""
        start_time = clock()
        
        open_file = KMLFile if filename[-3:].lower() == 'kml' else GPXFile
        gpx = open_file(filename, self.gpx_pulse, self.create_polygon)
        
        self.status_message(_("%d points loaded in %.2fs.") %
            (len(gpx.tracks), clock() - start_time))
        
        if len(gpx.tracks) < 2:
            return
        
        self.tracks.update(gpx.tracks)
        self.metadata.alpha = min(self.metadata.alpha, gpx.alpha)
        self.metadata.omega = max(self.metadata.omega, gpx.omega)
        
        self.map_view.emit("realize")
        self.map_view.set_zoom_level(self.map_view.get_max_zoom_level())
        bounds = Champlain.BoundingBox.new()
        for poly in self.polygons:
            bounds.compose(poly.get_bounding_box())
        gpx.latitude, gpx.longitude = bounds.get_center()
        self.map_view.ensure_visible(bounds, False)
        
        self.prefs.gpx_timezone = gpx.lookup_geoname()
        self.prefs.set_timezone()
        self.gpx_sensitivity()
    
    def apply_selected_photos(self, button, selected, view):
        """Manually apply map center coordinates to all selected photos."""
        for photo in selected:
            photo.manual = True
            photo.set_location(
                view.get_property('latitude'),
                view.get_property('longitude'))
        self.labels.selection.emit("changed")
    
    def revert_selected_photos(self, button=None):
        """Discard any modifications to all selected photos."""
        self.open_files([photo.filename for photo in self.modified & self.selected])
    
    def close_selected_photos(self, button=None):
        """Discard all selected photos."""
        for photo in self.selected.copy():
            self.labels.layer.remove_marker(photo.label)
            del self.photo[photo.filename]
            self.modified.discard(photo)
            self.liststore.remove(photo.iter)
        self.labels.select_all.set_active(False)
    
    def clear_all_gpx(self, widget=None):
        """Forget all GPX data, start over with a clean slate."""
        assert self.polygons is CommonAttributes.polygons
        assert self.metadata is CommonAttributes.metadata
        for polygon in self.polygons:
            self.map_view.remove_layer(polygon)
        
        del self.polygons[:]
        self.tracks.clear()
        self.metadata.omega = float('-inf')   # Final GPX track point
        self.metadata.alpha = float('inf')    # Initial GPX track point
        self.gpx_sensitivity()
    
    def save_all_files(self, widget=None):
        """Ensure all loaded files are saved."""
        self.progressbar.show()
        photos, total = list(self.modified), len(self.modified)
        for i, photo in enumerate(photos, 1):
            self.redraw_interface(i / total, basename(photo.filename))
            try:
                photo.write()
            except Exception as inst:
                self.status_message(str(inst))
            else:
                self.modified.discard(photo)
                self.liststore.set_value(photo.iter, SUMMARY,
                    photo.long_summary())
        self.progressbar.hide()
        self.labels.selection.emit("changed")
    
################################################################################
# Data manipulation. These methods modify the loaded files in some way.
################################################################################
    
    def photo_drag_start(self, widget, drag_context, data, info, time):
        """Acknowledge that a drag has initiated."""
        for photo in self.selected:
            data.set_text(photo.filename, -1)
    
    def photo_drag_end(self, widget, drag_context, x, y, data, info, time):
        """Accept photo drops on the map and set the location accordingly."""
        lat = self.map_view.y_to_latitude(y)
        lon = self.map_view.x_to_longitude(x)
        for photo in self.selected:
            photo.set_location(lat, lon)
        self.map_view.emit("animation-completed")
    
    def time_offset_changed(self, widget):
        """Update all photos each time the camera's clock is corrected."""
        seconds = self.secbutton.get_value()
        minutes = self.minbutton.get_value()
        offset  = int((minutes * 60) + seconds)
        if offset != self.metadata.delta:
            self.metadata.delta = offset
            if abs(seconds) == 60 and abs(minutes) != 60:
                minutes += seconds / 60
                self.secbutton.set_value(0)
                self.minbutton.set_value(minutes)
            for photo in self.photo.values():
                auto_timestamp_comparison(photo, self.tracks, self.metadata)
    
    def modify_summary(self, photo):
        """Insert the current photo summary into the liststore."""
        self.modified.add(photo)
        self.liststore.set_value(photo.iter, SUMMARY,
            ('<b>%s</b>' % photo.long_summary()))
    
    def toggle_selected_photos(self, button, selection):
        """Toggle the selection of photos."""
        if button.get_active(): selection.select_all()
        else:                   selection.unselect_all()
    
    def gpx_pulse(self, gpx):
        """Update the display during GPX parsing.
        
        This is called by GPXLoader every 0.2s during parsing so that we
        can prevent the display from looking hung.
        """
        self.progressbar.pulse()
        while Gtk.events_pending():
            Gtk.main_iteration()
    
    def create_polygon(self):
        """Get a newly created Champlain.MarkerLayer and decorate it."""
        polygon = Polygon()
        self.polygons.append(polygon)
        # Emitting this signal ensures the new polygon gets the correct color.
        self.prefs.colorpicker.emit("color-changed")
        self.map_view.add_layer(polygon)
        return polygon.append_point
    
################################################################################
# Dialogs. Various dialog-related methods for user interaction.
################################################################################
    
    def update_preview(self, chooser, label, image):
        """Display photo thumbnail and geotag data in file chooser."""
        label.set_label(self.strings.preview)
        image.set_from_stock(Gtk.STOCK_FILE, Gtk.IconSize.DIALOG)
        try:
            photo = Photograph(chooser.get_preview_filename(), lambda x: None, 300)
            photo.read()
        except IOError:
            return
        image.set_from_pixbuf(photo.thumb)
        label.set_label(format_list([photo.short_summary(), photo.maps_link()], "\n"))
    
    def add_files_dialog(self, button, chooser):
        """Display a file chooser, and attempt to load chosen files."""
        response = chooser.run()
        chooser.hide()
        if response == Gtk.ResponseType.OK:
            self.open_files(chooser.get_filenames())
    
    def confirm_quit_dialog(self, *args):
        """Teardown method, inform user of unsaved files, if any."""
        if len(self.modified) == 0:
            Gtk.main_quit()
            return True
        dialog = get_obj("quit")
        dialog.format_secondary_markup(self.strings.quit % len(self.modified))
        response = dialog.run()
        dialog.hide()
        self.redraw_interface()
        if response == Gtk.ResponseType.ACCEPT: self.save_all_files()
        if response != Gtk.ResponseType.CANCEL: Gtk.main_quit()
        return True
    
    def about_dialog(self, button, dialog):
        """Describe this application to the user."""
        # you can
        dialog.run()
        # but you can't
        dialog.hide()
        # ahahahhahahah!
    
################################################################################
# Initialization and Gtk boilerplate/housekeeping type stuff and such.
################################################################################
    
    def __init__(self):
        get_obj("toolbar").get_style_context().add_class(
            Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
        
        self.progressbar = get_obj("progressbar")
        self.status      = get_obj("status")
        
        self.strings = Struct({
            "quit":    get_obj("quit").get_property('secondary-text'),
            "preview": get_obj("preview_label").get_text()
        })
        
        self.liststore = get_obj("loaded_photos")
        self.liststore.set_sort_column_id(TIMESTAMP, Gtk.SortType.ASCENDING)
        
        cell_string = Gtk.CellRendererText()
        cell_thumb  = Gtk.CellRendererPixbuf()
        cell_thumb.set_property('stock-id', Gtk.STOCK_MISSING_IMAGE)
        cell_thumb.set_property('ypad', 6)
        cell_thumb.set_property('xpad', 6)
        
        column = Gtk.TreeViewColumn('Photos')
        column.pack_start(cell_thumb, False)
        column.add_attribute(cell_thumb, 'pixbuf', THUMB)
        column.pack_start(cell_string, False)
        column.add_attribute(cell_string, 'markup', SUMMARY)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        
        photos_view = get_obj("photos_view")
        photos_view.append_column(column)
        photos_view.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
            [], Gdk.DragAction.COPY)
        photos_view.connect("drag-data-get", self.photo_drag_start)
        photos_view.drag_source_add_text_targets()
        
        map_container = get_obj("map_container")
        map_container.add_with_viewport(self.champlain)
        map_container.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        map_container.connect("drag-data-received", self.photo_drag_end)
        map_container.drag_dest_add_text_targets()
        
        self.navigator = NavigationController()
        self.search    = SearchController()
        self.prefs     = PreferencesController()
        self.labels    = LabelController()
        self.actors    = ActorController()
        
        self.labels.selection.connect("changed", self.selection_sensitivity,
            *[get_obj(name) for name in ("apply_button", "close_button",
                "save_button", "revert_button", "photos_with_buttons")])
        
        about_dialog = get_obj("about")
        about_dialog.set_version(VERSION)
        about_dialog.set_program_name(APPNAME)
        
        click_handlers = {
            "open_button":       [self.add_files_dialog, get_obj("open")],
            "save_button":       [self.save_all_files],
            "clear_button":      [self.clear_all_gpx],
            "close_button":      [self.close_selected_photos],
            "revert_button":     [self.revert_selected_photos],
            "about_button":      [self.about_dialog, about_dialog],
            "apply_button":      [self.apply_selected_photos, self.selected, self.map_view],
            "select_all_button": [self.toggle_selected_photos, self.labels.selection]
        }
        for button, handler in click_handlers.items():
            get_obj(button).connect("clicked", *handler)
        
        accel  = Gtk.AccelGroup()
        window = get_obj("main")
        window.resize(*gst_get('window-size'))
        window.connect("delete_event", self.confirm_quit_dialog)
        window.add_accel_group(accel)
        window.show_all()
        
        save_size = lambda v,s,size: gst_set('window-size', size())
        for prop in ['width', 'height']:
            self.map_view.connect('notify::' + prop, save_size, window.get_size)
        
        map_source_button = get_obj("map_source_label").get_parent()
        if map_source_button:
            map_source_button.set_property("visible", False)
        
        accel.connect(Gdk.keyval_from_name("q"),
            Gdk.ModifierType.CONTROL_MASK, 0, self.confirm_quit_dialog)
        
        self.labels.selection.emit("changed")
        self.clear_all_gpx()
        
        self.metadata.delta = 0
        self.secbutton, self.minbutton = get_obj("seconds"), get_obj("minutes")
        bind("offset-minutes", self.minbutton, "value")
        bind("offset-seconds", self.secbutton, "value")
        for spinbutton in [ self.secbutton, self.minbutton ]:
            spinbutton.connect("value-changed", self.time_offset_changed)
        
        get_obj("open").connect("update-preview", self.update_preview,
            get_obj("preview_label"), get_obj("preview_image"))
        
        drop_target = get_obj("photos_and_map")
        drop_target.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.MOVE)
        drop_target.connect("drag-data-received", self.file_dragged_in)
        drop_target.drag_dest_add_uri_targets()
    
    def gpx_sensitivity(self):
        """Control the sensitivity of GPX-related widgets."""
        gpx_sensitive = len(self.tracks) > 0
        for widget in [ "minutes", "seconds", "offset_label", "clear_button" ]:
            get_obj(widget).set_sensitive(gpx_sensitive)
    
    def selection_sensitivity(self, selection, aply, close, save, revert, left):
        """Control the sensitivity of various widgets."""
        assert self.selected is CommonAttributes.selected
        assert self.modified is CommonAttributes.modified
        sensitive = selection.count_selected_rows() > 0
        close.set_sensitive(sensitive)
        aply.set_sensitive(sensitive)
        save.set_sensitive(  len(self.modified) > 0)
        revert.set_sensitive(len(self.modified & self.selected) > 0)
        if len(self.photo) > 0: left.show()
        else:                   left.hide()
    
    def redraw_interface(self, fraction=None, text=None):
        """Tell Gtk to redraw the user interface, so it doesn't look hung.
        
        Primarily used to update the progressbar, but also for disappearing
        some dialogs while things are processing in the background. Won't
        modify the progressbar if called with no arguments.
        """
        if fraction is not None: self.progressbar.set_fraction(fraction)
        if text is not None:     self.progressbar.set_text(str(text))
        while Gtk.events_pending(): Gtk.main_iteration()
    
    def status_message(self, message):
        """Display a message on the GtkStatusBar."""
        self.status.push(self.status.get_context_id("msg"), message)
    
    def main(self, anim_start=400):
        """Animate the crosshair and begin user interaction."""
        if argv[1:]:
            self.open_files(argv[1:])
            anim_start = 10
        self.actors.animate_in(anim_start)
        Gtk.main()

