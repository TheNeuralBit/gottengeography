import sys
from gi.repository import Gtk
from gg.xmlfiles import TrackFile

if __name__ == "__main__":
    TrackFile.load_from_file(sys.argv[1])
