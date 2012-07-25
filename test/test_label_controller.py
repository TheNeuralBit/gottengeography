
"""Test that the ChamplainLabels are behaving."""

from gi.repository import Clutter, Champlain

from gg.common import selected
from gg.widgets import Widgets
from gg.photos import Photograph
from gg.label import Label

from test import IMGFILES, DEMOFILES, gui, random_coord

def test_creatability():
    """ChamplainLabels should exist"""
    lat = random_coord(90)
    lon = random_coord(180)
    
    label = Label(Photograph('demo/IMG_2411.JPG'))
    label.set_location(lat, lon)
    assert isinstance(label, Champlain.Label)
    assert label.get_name() == 'demo/IMG_2411.JPG'
    assert label.get_text() == 'IMG_2411.JPG'
    
    assert label.get_latitude() == lat
    assert label.get_longitude() == lon
    label.photo.destroy()

def test_hoverability():
    """Labels should grow when hovered"""
    gui.open_files(DEMOFILES)
    assert Photograph.instances
    assert Label.instances
    for label in Label.instances:
        assert label.get_scale() == (1, 1)
        label.emit('enter-event', Clutter.Event())
        assert label.get_scale() == (1.05, 1.05)
        label.emit('leave-event', Clutter.Event())
        assert label.get_scale() == (1, 1)

def test_clickability():
    """Labels become selected when clicked"""
    gui.open_files(DEMOFILES)
    assert Photograph.instances
    assert Label.instances
    for label in Label.instances:
        label.emit('button-press', Clutter.Event())
        for button in ('save', 'revert', 'close'):
            assert Widgets[button + '_button'].get_sensitive()
        
        assert Widgets.photos_selection.iter_is_selected(label.photo.iter)
        assert Widgets.photos_selection.count_selected_rows() == 1
        assert label.photo in selected
        assert len(selected) == 1
        assert label.get_scale() == (1.1, 1.1)
        assert label.get_selected()
        assert label.get_property('opacity') == 255
        
        # Make sure the Labels that we didn't click on are deselected.
        for other in Label.instances:
            if other.get_name() == label.get_name():
                continue
            assert not Widgets.photos_selection.iter_is_selected(other.photo.iter)
            assert other.photo not in selected
            assert other.get_scale() == (1, 1)
            assert not other.get_selected()
            assert other.get_property('opacity') == 64

def test_visible_at_launch():
    """Pre-tagged photos should have visible labels right off the bat."""
    # Open, save, and close the combined jpg/gpx data
    gui.open_files(DEMOFILES)
    Widgets.save_button.emit('clicked')
    Widgets.photos_selection.select_all()
    Widgets.close_button.emit('clicked')
    assert not Label.instances
    assert not Photograph.instances
    
    # Reopen just the JPEGs and confirm labels are visible
    for uri in IMGFILES:
        Photograph.load_from_file(uri)
    assert Label.instances
    for label in Label.instances:
        assert label.photo.positioned
        assert label.get_property('visible')

