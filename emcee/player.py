#!/usr/bin/python3
import sys

# This must be done *before* importing GTK, otherwise it will cause some unexpected segfaults
# GTK doesn't enable X11's (Un)LockDisplay functions which allow multiple threads to safely draw to the same X window.
# VLC needs this functionality to do accelarated rendering.
#
# NOTE: This must be the first thing done with X11, as such it probably needs to be called before even importing this widget.
import ctypes
x11 = ctypes.cdll.LoadLibrary('libX11.so.6')
ret = x11.XInitThreads()
if ret == 0:
    print('WARNING: X11 could not be initialised for threading, VLC performance will be signifcantly reduced', file=sys.stderr)

from gi.repository import Gtk, Gdk, GObject
# Without GdkX11 being imported GTK widgets don't get the get_xid() function,
# so even though this widget is never directly called we still need to import it.
from gi.repository import GdkX11  # noqa: F401

# Make VLC's threading play nicely with GObject's
# Must be done before importing VLC
GObject.threads_init()

# Make sure you get the right version of python-vlc to match your installed version of VLC, acquired from here
# https://www.olivieraubert.net/vlc/python-ctypes/
import vlc

import osd

# FIXME: Make this triggerable via a command-line flag
debugging_enabled = False  # Avoid committing this as True


def debug(*args):
    if debugging_enabled:
        print('DEBUGING:', *args,
              file=sys.stderr)


class VLCWidget(Gtk.DrawingArea):
    # These are the event signals that can be triggered by this widget
    # FIXME: I suspect I'm using GTK's signals wrongly, and am supposed to use them to call things interal to the widget,
    #        not just to signal when the widget has done things.
    #    eg, load_thing() should not emit('loaded') but rather emit('load_thing') should trigger do_load_thing()
    __gsignals__ = {
        'end_reached': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'time_changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'position_changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'paused': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'playing': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'media_state': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'error': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'loaded': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'initialised': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
    }

    # Initialise state variables
    time = 0
    position = 0
    length = 0
    paused = True
    state = 'NothingSpecial'  # This string is copied from VLC's default state
    instance = None

    def emit(self, *args, **kwargs):
        debug('VLCWidget emitting', *args)
        super(VLCWidget, self).emit(*args, **kwargs)

    def __init__(self, *args):

        # Initialise the DrawingArea
        super(VLCWidget, self).__init__(*args)
        self.override_background_color(0, Gdk.RGBA(red=0, green=0, blue=0))  # Fill it with black

        # Create the VLC instance, and tell it how to inject itself into the DrawingArea widget.
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        # Set up hooks to the VLC event manager to trigger some Python functions
        ## FIXME: Should these all be changed to emit GObject signals?

        self.event_manager = self.player.event_manager()
        # Should really only trigger when loading new media
        self.event_manager.event_attach(vlc.EventType.MediaPlayerLengthChanged, self._on_length)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self._on_paused)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_playing)
        # Current position in milliseconds
        self.event_manager.event_attach(vlc.EventType.MediaPlayerTimeChanged, self._on_time_changed)
        # Current position in percentage of total length
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, self._on_position_changed)
        #self.event_manager.event_attach(vlc.EventType.MediaPlayerTitleChanged, self._on_title_changed)  # FIXME: Hasn't triggered
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, lambda _: self.emit('end_reached'))
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, lambda _: self.emit('error'))

        self.connect("destroy", self._destroy)

        # Some of the required initialisation doesn't actually work until the GTK widget has been realised,
        # so we split that into a separate function.
        self.connect("realize", self._realize)

    def _realize(self, widget, data=None):
        debug('VLCWidget realizing')
        win_id = widget.get_window().get_xid()
        self.player.set_xwindow(win_id)

        self.emit('initialised')

    def _destroy(self, *args):
        debug("VLCWidget Destroying")
        # Stop playback and release the VLC objects for garbage collecting.
        self.player.stop()
        self.player.release()
        self.instance.release()

    ## event_manager hooks ##
    def _on_length(self, event):
        self.length = event.u.new_length / 1000

    def _on_paused(self, event):
        self.paused = True
        self.emit('paused')

    def _on_playing(self, event):
        self.paused = False
        self.emit('playing')

    def _on_time_changed(self, event):
        self.time = event.u.new_time / 1000
        self.emit('time_changed')

    def _on_position_changed(self, event):
        self.position = event.u.new_position
        self.emit('position_changed')

    ## Internally used functions ##
    def _load_media(self, uri, local=True):
        """Load a new media file/stream, and whatever else is involved therein"""

        debug('VLDWidget loading media')
        if not self.instance:
            debug('    deffered')
            # VLC not yet initialised so can't actually load the media yet.
            # Rerun ourselves when VLC has been initialised.
            self.connect('initialised', lambda _: self._load_media(uri=uri, local=local))
            return

        ##FIXME: Handle loading of subtitles as well
        ##       If a .srt or similar is placed with the media file, load that and turn them on by default.
        ##       Does VLC do that automatically?
        ##
        ##       Otherwise turn them off by default, but search for them automatically at http://thesubdb.com/
        ##       TV stream telx & similar should be turned off by default as well.

        # VLC detects local vs. remote URIs by simply checking if there is a ':' character in it, this is insufficient.
        ## FIXME: Actually automate this using better heuristics rather than just passing that test off to the user
        ##        Used urlparse.urlparse for this test in UPMC
        if local:
            ## FIXME: bytes() conversion here not necessary for python-vlc 2.2.*
            ##        Should I instead check version at import time and just error out completely if < 2.2?
            if not vlc.libvlc_get_version().startswith(b'2.2.'):
                uri = bytes(uri, sys.getfilesystemencoding())
            media = self.instance.media_new_path(uri)
        else:
            media = self.instance.media_new(uri)

        media_em = media.event_manager()
        media_em.event_attach(vlc.EventType.MediaStateChanged, self._on_state_change)
        media_em.event_attach(vlc.EventType.MediaParsedChanged, self._on_parsed)

        self.player.set_media(media)
        self.player.play()

    def _on_state_change(self, event):
        # All possible states at time of writing --Mike June 2016
        #
        # ['Buffering', 'Ended', 'Error', 'NothingSpecial', 'Opening', 'Paused', 'Playing', 'Stopped']

        ## Reverse VLC's enum to get the name from the value.
        ## This is not at all intuitive, but I'm at the mercy of the VLC library here.
        self.state = vlc.State._enum_names_[event.u.new_state]

        self.emit('media_state')

    def _on_parsed(self, event):
        """Handle once-off reading of media metadata"""
        # This function triggers when parsed state changes not just when it's parsed, so check that it is currently parsed
        if self.player.get_media().is_parsed():
            if 0 == self.player.video_get_spu_count():
                self.subtitles = {-1: 'No subtitles found'}
            else:
                self.subtitles = dict(self.player.video_get_spu_description())
                self.subtitles[-1] = 'Disabled'  # FIXME: Are things other than '-1' used to disable subtitles? Normalise it all?
                # FIXME: Might need to do some ugly teletext handling stuff

            if 0 == self.player.audio_get_track_count():
                self.audio_tracks = {-1: 'No audio tracks found'}
            else:
                self.audio_tracks = dict(self.player.audio_get_track_description())
                self.audio_tracks[-1] = 'Disabled'  # FIXME: Should this "track" be removed in favour of mute/unmute

            # FIXME: Is there more things to process here? Multiple video tracks?
            self.emit('loaded')

    ## Playback control functions ##
    def play(self, uri=None, local=True):
        """Unpause if currently paused, or load new media if uri is set"""

        if uri:
            self._load_media(uri, local=local)
        else:
            return self.player.play()

    def stop(self):
        """Stop all playback, and hide the player"""

        self.hide()
        return self.player.stop()

    def toggle_pause(self):
        """Toggle current pause state. Return final state"""

        if self.player.can_pause():
            self.player.pause()
            return self.player.is_playing() == 1
        else:
            return False

    def set_time(self, seconds):
        """Jump to certain point in the media, unlike seek() this deals with absolute time."""

        milliseconds = int(seconds * 1000)  # VLC's logic deals with milliseconds

        ##FIXME: Add logic to avoid going past the beginning or end of the media?
        if self.player.is_seekable():
            self.player.set_time(milliseconds)

        return int(self.player.get_time() / 1000)

    def seek(self, seconds):
        """Jump forward or back in the media, unlike set_time() this deals with relative time.."""

        return self.set_time(self.time + seconds)

    def get_current_subtitles(self):
        """Get name of current subtitles track"""
        return self.subtitles[self.player.video_get_spu()]

    def get_subtitles(self):
        """Get name of all subtitles tracks"""
        return list(self.subtitles.values())

    def set_subtitles(self, index):
        """Set current subtitles track, index is based on the order from get_subtitles()"""
        if index == -1:
            # Just turn them off
            self.player.video_set_spu(-1)
            return 'Disabled'

        if len(self.subtitles) == 1 and -1 in self.subtitles:
            return 'No subtitles found'
        elif len(self.subtitles) > index:
            # VLC needs the track ID, but I just want to deal with an index from a list of just the subtitles tracks.
            # Python3 dict.keys() doesn't support indexing, so converting it to a standard list.
            self.player.video_set_spu(list(self.subtitles.keys())[index])
            return self.get_current_subtitles()
        else:
            return 'Subtitles track {} not found'.format(index)

    def increment_subtitles(self, inc=1):
        """Increment through subsitles in the order they come from get_subtitles()"""
        if len(self.subtitles) == 1 and -1 in self.subtitles:
            return 'No subtitles found'

        # Find the current index and compare with the increment.
        index = list(self.subtitles.keys()).index(self.player.video_get_spu())
        index += inc
        index = index % len(self.subtitles)  # In case it's above the max or below 0

        return self.set_subtitles(index)

    def get_current_audio_track(self):
        """Get name of current audio track"""
        return self.audio_tracks[self.player.audio_get_track()]

    def get_audio_tracks(self):
        """Get name of all audio tracks"""
        debug(self.audio_tracks)
        return list(self.audio_tracks.values())

    def set_audio_track(self, index):
        """Set current audio track, index is based on the order from get_audio_tracks()"""
        if index == -1:
            # Just turn audio off
            ## FIXME: should be done with mute/unmute instead
            self.player.audio_set_track(-1)
            return 'Disabled'

        if len(self.audio_tracks) == 1 and -1 in self.audio_tracks:
            return 'No audio tracks found'
        elif len(self.audio_tracks) > index:
            # VLC needs the track ID, but I just want to deal with an index from a list of just the audio tracks.
            # Python3 dict.keys() doesn't support indexing, so converting it to a standard list.
            self.player.audio_set_track(list(self.audio_tracks.keys())[index])
            return self.get_current_audio_track()
        else:
            return 'Audio track {} not found'.format(index)

    def increment_audio_track(self, inc=1):
        """Increment through audio tracks in the order they come from get_audio_tracks()"""
        if len(self.audio_tracks) == 1 and -1 in self.audio_tracks:
            return 'No audio_tracks found'

        # Find the current index and compare with the increment.
        index = list(self.audio_tracks.keys()).index(self.player.audio_get_track())
        index += inc
        index = index % len(self.audio_tracks)  # In case it's above the max or below 0

        return self.set_audio_track(index)

    def get_volume(self):
        """Get the current volume as a percentage"""
        ## FIXME: It is possible to go above 100%, how should we handle that?
        ## FIXME: I wanted this to be queried as a variable (self.volume) that updates only when changed,
        ##        similar to self.time and self.position, but there's no VLC event to hook for volume changes
        return self.player.audio_get_volume() / 100

    def set_volume(self, value):
        """Set the volume to a specific percentage"""
        self.player.audio_set_volume(int(value * 100))
        return self.get_volume()

    def increment_volume(self, inc):
        """Increment volume by a percentage of the total"""
        value = self.get_volume() + inc
        self.set_volume(value)

        return self.get_volume()


def main(*args):  # noqa: C901
    media_uri = args[0]

    window = Gtk.Window(title='Emcee')
    window.connect("destroy", lambda q: Gtk.main_quit())  # Quit & cleanup when closed
    window.show()

    overlay = Gtk.Overlay()

    vid = VLCWidget()
    debug('vid created')
    overlay.add(vid)
    debug('vid added to overlay')
    vid.play(media_uri)
    debug('vid.play', media_uri)

    ## OSD
    osd_widget = osd.OSD()

    overlay.add_overlay(osd_widget)

#    play_image = Gtk.Image.new_from_icon_name(
#        "gtk-media-play",
#        Gtk.IconSize.MENU
#    )
#    pause_image = Gtk.Image.new_from_icon_name(
#        "gtk-media-pause",
#        Gtk.IconSize.MENU
#    )
#    playpause_button = Gtk.Button()
#    playpause_button.set_image(play_image)
#    playpause_button.connect('clicked', lambda _: vid.toggle_pause())
#
#    def f(new_image):
#        GObject.idle_add(lambda: playpause_button.set_image(new_image))
#
#    vid.connect('paused', lambda _: f(play_image))
#    vid.connect('playing', lambda _: f(pause_image))
#    # FIXME: Make the button partially transparent
#    playpause_button.set_valign(Gtk.Align.CENTER)
#    playpause_button.set_halign(Gtk.Align.CENTER)
#    overlay.add_overlay(playpause_button)

    window.add(overlay)
    overlay.show_all()
    window.show_all()
    debug('shown all')

    ## Keyboard input setup
    keybindings = {
        # Volume
        'Up': lambda: vid.increment_volume(+0.02),
        'Down': lambda: vid.increment_volume(-0.02),

        # Time manipulation
        'space': vid.toggle_pause,
        'Left': lambda: vid.seek(-20),  # 20 seconds back
        'Right': lambda: vid.seek(+30),  # 30 seconds forward
        'Page_Up': lambda: vid.seek(-300),  # 5 minutes back
        'Page_Down': lambda: vid.seek(+300),  # 5 minutes forward
        'Home': lambda: vid.set_time(0),  # Jump to beginning
        'End': lambda: vid.set_time(999999999),  # Jump to end, for testing only

        'p': lambda: vid.play(media_uri),
        'BackSpace': vid.stop,

        'F': window.fullscreen,
        'f': window.unfullscreen,

        'i': osd_widget.toggle,

        's': lambda: print(vid.increment_subtitles()),
        'S': lambda: print(vid.get_subtitles()),
        'a': lambda: print(vid.increment_audio_track()),
        'A': lambda: print(vid.get_audio_tracks()),

        'Escape': Gtk.main_quit,
    }

    def on_key_press(window, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname in keybindings.keys():
            # Run the function or lambda stored in the keybindings dict
            keybindings[keyname]()
        else:
            debug('no keybinding found for %s' % keyname)

    window.connect("key_press_event", on_key_press)

    ## CLI output, showing current position and state
    bar_length = 40  # FIXME: Somehow detect width of terminal and set this accordingly

    def update_status(vid_widget):
        """Make a fancy looking progressbar with numbers for how far into the current movie you are"""
        if vid_widget.state == 'Opening':
            print('Loading ', vid_widget.player.get_media().get_mrl())
        elif vid_widget.state not in ('Playing', 'Paused', 'Ended'):
            debug('Unknown state:', vid_widget.state)
            return
        current_min = int(vid_widget.time / 60)
        current_sec = int(vid_widget.time % 60)
        bar = ''
        for i in range(0, int(bar_length * vid_widget.position) - 1):
            bar += '='
        bar += '||' if vid_widget.paused else '|>'
        for i in range(len(bar) - 1, bar_length):
            bar += '-'
        length_min = int(vid_widget.length / 60)
        length_sec = int(vid_widget.length % 60)
        # This does space padding for 4 characters (4) removes any decimal points (.0) and displays it as a percentage (%):
        #     {p:4.0%}
        print(
            "\r{cm:02}:{cs:02} [{bar}] {p:4.0%} {lm:02}:{ls:02} V: {v:4.0%} ".format(
                cm=current_min, cs=current_sec,
                bar=bar,
                p=vid_widget.position,
                lm=length_min, ls=length_sec,
                v=vid_widget.get_volume()),
            end='')

    # FIXME: Should I hook this to other events?
    vid.connect('paused', update_status)
    #vid.connect('position_changed', update_status) # Only really need either time or position, not both
    vid.connect('time_changed', update_status)
    vid.connect('media_state', update_status)

    ## Resize when media is finished loading (don't know the resolution before that)
    def resize(vid_widget):
        media_title = vid_widget.player.get_media().get_meta(vlc.Meta.Title)
        window.set_title('Emcee - {}'.format(media_title.rpartition('.')[0]))
        size = vid_widget.player.video_get_size()
        if size != (0, 0):
            # FIXME: Sometimes crashes with this error, if this resize line is
            # removed it just segfaults without error. I suspect the resize
            # isn't adding to the crash at all, and this output is just the
            # resize failing after it crashes, but I don't understand the crash
            # yet
            #
            # (player.py:14508): Pango-CRITICAL **: pango_context_get_matrix: assertion 'PANGO_IS_CONTEXT (context)' failed
            # src/player.py:403: Warning: g_object_get_qdata: assertion 'G_IS_OBJECT (object)' failed
            #   Gtk.main()
            # (player.py:14508): Pango-CRITICAL **: pango_context_get_matrix: assertion 'PANGO_IS_CONTEXT (context)' failed
            # src/player.py:403: Warning: g_object_replace_qdata: assertion 'G_IS_OBJECT (object)' failed
            #   Gtk.main()
            #
            # UPDATE: Adding idle_add here & to the playpause_button.set_image calls above seems to have reduced this crash.
            #    Do I need to use idle_add for all GTK calls?
            GObject.idle_add(lambda: window.resize(*size))

    vid.connect('loaded', resize)

    # FIXME: This doesn't cleanup VLC
    #        Ideally GTK would have a on_quit hook of some sort where I can tell it to destroy the VLC instance and such.
    #        My Google-fu seems to indicate that is not the case so I may need a custom emcee.quit() function that does all of that
    vid.connect('error', lambda _: Gtk.main_quit())  # Quit & cleanup when VLC has an error
    vid.connect('end_reached', lambda _: Gtk.main_quit())  # Quit & cleanup when finished media file
    Gtk.main()

if __name__ == '__main__':
    main(*sys.argv[1:])
