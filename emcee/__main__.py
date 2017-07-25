#!/usr/bin/python3
# NOTE: Consider running this with the GDK_SCALE environment variable set to force all elements to be bigger,
#       This might be an easier way to implement the 10-foot UI.
import os
import sys
import logging
import warnings
logging_level = os.environ.get('EMCEEDEBUG')
if logging_level:
    # Unintuitively the lower the number in logging_level, the more logging you'll get.
    logging.basicConfig(level=int(logging_level))
logger = logging.getLogger(__name__)

# This must be done *before* importing GTK, otherwise it will cause some unexpected segfaults
# GTK doesn't enable X11's (Un)LockDisplay functions which allow multiple threads to safely draw to the same X window.
# VLC needs this functionality to do accelarated rendering.
import ctypes
x11 = ctypes.cdll.LoadLibrary('libX11.so.6')
ret = x11.XInitThreads()
if ret == 0:
    warnings.warn('WARNING: X11 could not be initialised for threading, VLC performance will be signifcantly reduced')

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GObject', '2.0')
from gi.repository import Gtk, Gdk, GObject
import emcee.selector
import emcee.osd
import emcee.player


# FIXME: I'm seeing a few places online saying not to use keynames but the keyvals themselves instead.
#        Gdk has a bunch of constants for name -> keyval mapping I think
# FIXME: Use -gtk-key-bindings in CSS for configuring this. Can't be done in Jessie's version of Gtk.
#   https://developer.gnome.org/gtk3/stable/gtk3-Bindings.html
#   I think it comes in ~3.16 although the property name is "gtk-key-bindings" until a later version when the - is prefixed
# FIXME: Use Keybinder or similar to steal the media keys while Emcee is running even if not in focus?
#   https://lazka.github.io/pgi-docs/Keybinder-3.0/index.html
keybindings = {
    'general': {
        'i': 'toggle_osd',
        'f': 'fullscreen',
        'F': 'unfullscreen',
        'Escape': 'back',
    },
    'player': {
        # Volume
        'Up': ('increment_volume', +0.02),
        'Down': ('increment_volume', -0.02),

        # Time manipulation
        'space': ('toggle_pause'),
        'Left': ('seek', -20),  # 20 seconds back
        'Right': ('seek', +30),  # 30 seconds forward
        'Page_Up': ('seek', -300),  # 5 minutes back
        'Page_Down': ('seek', +300),  # 5 minutes forward
        'Home': ('set_time', 0),  # Jump to beginning
        'End': ('set_time', -5),  # Jump to end (almost), mostly just for testing

        'p': 'play',
        'Escape': 'stop',

        's': ('increment_subtitles', +1),
        'a': ('increment_audio_track', +1),
    },
    'selector': {
        'Up': 'prev_station',
        'Down': 'next_station',
        'Left': 'prev_channel',
        'Right': 'next_channel',

        'space': 'select_channel',
        'Return': 'select_channel',
        'KP_Enter': 'select_channel',
    },
}


class Main(Gtk.Window):
    __gsignals__ = {
        'toggle_osd': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'back': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'fullscreen': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'unfullscreen': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.overlay = Gtk.Overlay()
        self.add(self.overlay)
        self.overlay.show()

        self.osd = emcee.osd.OSD()
        self.overlay.add_overlay(self.osd)
        # Not showing this yet as I want it hidden by default

        self.selector = emcee.selector.StreamSelector()
        self.selector.show_all()

        self.overlay.add(self.selector)
        self.mode = 'selector'
        self.selector.connect('selected', self.on_selected)

        self._init_player()

    def _init_player(self):
        self.player = emcee.player.VLCWidget()
        self.player.load_media(sys.argv[1])  # FIXME: Early testing only, remove this!
        self.player.show_all()

        # FIXME: Do we need to hook into vlc.EventType.VlmMediaInstanceStopped as well?
        self.player.connect('error', self.on_stop_playback)
        self.player.connect('end_reached', self.on_stop_playback)
        self.player.connect('media_state', self.on_media_state)

        # FIXME: This also triggers when the media is first loaded, I don't want that.
        # FIXME: This is also triggering when the media stops.
        self.player.connect('volume_changed', lambda _, v: self.osd.push_status("Volume: {v:4.0%}".format(v=v)))

    def on_media_state(self, player, state):
        ## player is the player widget as given by the event, this is the same as self.player
        logger.debug('State changed to %s', state)
        if state == 'Playing':
            # Rename the window
            media_title = player.get_title()
            media_title = media_title.rpartition('.')[0]  # FIXME: Will there always be an extension?
            self.orig_title = self.get_title()
            self.set_title('{} - {}'.format(self.orig_title, media_title))
            # NOTE: Without using idle_add here an intermittent issue will occur with Gtk getting stuck.
            # FIXME: Not reproducing it now, but keep that in mind.
            self.osd.set_title(media_title)
        elif state == 'Stopped':
            # FIXME: Is there a better VLC event to hook for this?
            self.on_stop_playback(self.player)

    def on_selected(self, selector, item):
        ## selector is the selector widget as given by the event, this is the same as self.selector
        # Activate any loading screen as early as possible before actually loading the media.
        self.mode = "player"
        self.get_style_context().add_class("loading")
        self.overlay.remove(selector)

        # Set up the player
        logger.debug("self.player.load_media(%s)", item.uri)  # FIXME: Enable this when actually giving it a real uri
        # Is it worth actually running load_media when changing focus in the selector?
        # Or perhaps when the user stops changing focus for a second?
        # We can't put the playback in the background of the menu, but maybe at least start buffering without the user knowing

        self.overlay.add(self.player)
        self.player.show()
        # Make sure to play *after* showing, or VLC could end up creating it's own window.
        # UPDATE: I think this is no longer entirely valid and play can be run before show,
        #         but must be after adding the widget to window object (or child thereof)
        self.player.emit('play')
        self.osd.show(5)

    def on_stop_playback(self, player):
        ## player is the player widget as given by the event, this is the same as self.player
        self.mode = 'selector'
        self.osd.set_title('')

        self.overlay.remove(player)
        self.set_title(self.orig_title)
        self.overlay.add(self.selector)

        self.get_style_context().remove_class("loading")
        # FIXME: Doesn't actually hide because the volume_changed signal triggers as the media stops
        self.osd.hide()

    def do_key_press_event(self, EventKey):
        keyname = Gdk.keyval_name(EventKey.keyval)
        keybind = keybindings[self.mode].get(keyname, None)
        fallback = keybindings['general'].get(keyname, None)

        if not keybind and not fallback:
            logger.debug('No keybinding found for %s', keyname)
        elif keybind:
            logger.debug('User pressed %s, performing %s action: %s', keyname, self.mode, keybind)
            args = keybind if type(keybind) == tuple else (keybind,)
            if self.mode == 'selector':
                self.selector.emit(*args)
            elif self.mode == 'player':
                self.player.emit(*args)
        elif fallback:
            logger.debug('User pressed %s, performing action: %s', keyname, fallback)
            args = fallback if type(fallback) == tuple else (fallback,)
            self.emit(*args)

    def do_back(self):
        Gtk.main_quit()

    def do_toggle_osd(self):
        self.osd.toggle()

    def do_fullscreen(self):
        self.fullscreen()

    def do_unfullscreen(self):
        self.unfullscreen()

if __name__ == '__main__':
    style_provider = Gtk.CssProvider()
    style_provider.load_from_path("main.css")
    Gtk.StyleContext.add_provider_for_screen(
        screen=Gdk.Screen.get_default(),
        provider=style_provider,
        priority=Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    # #gtk+ on irc.gnome.org
    # 15:34 < mijofa> Can anyone point me at what version number of Gtk included radial-gradient in the CSS? (as opposed to
    #                 -gtk-gradient(radial, which doesn't give me the same control I need)
    # 15:46 < hergertme> mijofa, based on a quick look through the git log, i'd expect 3.20
    if Gtk.MAJOR_VERSION >= 3 and Gtk.MINOR_VERSION >= 20 and Gtk.MICRO_VERSION >= 0:
        # Radial-gradient doesn't work in Debian Jessie's version of Gtk3
        # FIXME: This is quick-and-dirty, create a separate stretch.css that includes main.css
        stretch_style_provider = Gtk.CssProvider()
        stretch_style_provider.load_from_path("main.css")
        stretch_style_provider.load_from_data(b"""window { background:
            /* FIXME: Magic number. 165px is selector.py:OFFSET_UPPER + (selector.py:BUTTON_HEIGHT / 2)
             *        which gets a point in the center of the currently selected button */
            radial-gradient(farthest-corner at 165px 165px,
                            @TangoAluminium3,
                            @TangoSkyBlue1 90px,
                            @TangoSkyBlue3 150px,
                            @TangoPlum3)}""")
        Gtk.StyleContext.add_provider_for_screen(
            screen=Gdk.Screen.get_default(),
            provider=stretch_style_provider,
            priority=Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    win = Main(title='Emcee')
    win.show()
    win.connect('destroy', Gtk.main_quit)
    Gtk.main()
