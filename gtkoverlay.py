#!/usr/bin/python3
import pprint

from gi.repository import Gtk, Gdk, GdkPixbuf, GdkX11, GLib

import sys
import vlc

osd_margin = 10

vid_states = vlc.State

class VLCWidget(Gtk.DrawingArea):
    def __init__(self, *args):

        # Initialise the DrawingArea
        super(VLCWidget, self).__init__(*args)
        self.override_background_color(0, Gdk.RGBA(red=0,green=0,blue=0)) # Fill it with black

        # Create the VLC instance, and tell it how to inject itself into the DrawingArea widget.
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.connect("map", lambda _: self.player.set_xwindow(self.get_property('window').get_xid()))

    def _load_media(self, uri):
        """Load a new media file/stream, and whatever else is involved therein"""

        ##FIXME: Handle loading of subtitles as well
        ##       If a .srt or similar is placed with the media file, load that and turn them on by default.
        ##       Otherwise turn them off by default, but search for them automatically at http://thesubdb.com/
        ##       TV stream telx & similar should be turned off by default as well.
        self.media = self.instance.media_new(uri)
        self.player.set_media(self.media)

    def play(self, uri=None):
        """Unpause if currently paused, or load new media if uri is set"""

        if uri:
            self._load_media(uri)
        return self.player.play()

    def toggle_pause(self):
        """Toggle current pause state. Return True if paused, False if unpaused"""

        if self.player.can_pause():
            self.player.pause()
            return self.player.is_playing() == 1
        else:
            return False

    def seek(self, seconds, relative=True):
        """Jump forward or back in the stream, if relative is false then it will go to the specified time rather than jumping that far."""

        ##FIXME: Add logic to avoid going past the beginning or end of the media
        if self.player.is_seekable():
            milliseconds = seconds*1000 # VLC's logic deals with milliseconds

            if relative:
                self.player.set_time(self.player.get_time()+milliseconds)
            else:
                self.player.set_time(milliseconds)

        return int(self.player.get_time()/1000)

window = Gtk.Window(title='Emcee')
window.connect("destroy", lambda q: Gtk.main_quit())
window.show()
window.set_size_request(1, 3)

vid = VLCWidget()
window.add(vid)
vid.show()
vid.play(sys.argv[1])

class osd_window(Gtk.Window):
    ##FIXME: This should have a show() and hide() function that show and hide the OSD, currently it has hide() and show_all()
    def __init__(self, parent):
        super(osd_window, self).__init__(
            title='OSD',
            role='OSD',
            border_width=0,
            resizable=False,
            decorated=False,
            accept_focus=False,
            skip_pager_hint=True,
            skip_taskbar_hint=True,
        )
        self.connect('show', self.reposition)
        parent.connect('configure-event', self.reposition)
        self.set_transient_for(parent) # Force the OSD to stay above the main window

        overlay = Gtk.Overlay()
        self.add(overlay)
        bg = Gtk.Image.new_from_file('osd_bg.png')
        bg.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1)) # Set the background to black
        overlay.add(bg)
        self.add = overlay.add_overlay

    def reposition(self, parent, *args, **kwargs):
        # Set OSD position based on the position of the main window
        osd_size = self.get_size()
        parent_pos = parent.get_position()
        parent_size = parent.get_size()
        pos_offset = parent_size[0]-osd_size[0]
        self.move(parent_pos[0]+pos_offset-osd_margin, parent_pos[1]+osd_margin)

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show_all()
            self.reposition(window)

osd = osd_window(window)
textview = Gtk.TextView()
textbuffer = textview.get_buffer()
textbuffer.set_text("Welcome to the PyGObject Tutorial\n\nThis guide aims to provide an introduction to using Python and GTK+.\n\nIt includes many sample code files and exercises for building your knowledge of the language.", -1)
textview.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0)) # Set the background to transparent
textview.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1)) # Set the foreground to white
osd.add(textview)

keybindings = {
    'space': vid.toggle_pause,
    'Left':  lambda: vid.seek(-20), # 20 seconds back
    'Right': lambda: vid.seek(+30), # 30 seconds forward
    'F':     window.fullscreen,
    'f':     window.unfullscreen,
    'i':     osd.toggle,
    'Escape':Gtk.main_quit,
}

def on_key_press(window, event):
    keyname = Gdk.keyval_name(event.keyval)
    if keyname in keybindings.keys():
        print(keyname, keybindings[keyname]())
    else:
        print('no keybinding found for %s' % keyname)

window.connect("key_press_event", on_key_press)

if __name__ == '__main__':
    Gtk.main()
