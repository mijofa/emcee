#!/usr/bin/python3
import sys
import logging

## This is done in the first emcee scripts to run, but leaving it commented
## here for documentation as this is the file that actually depends on it
#
# This must be done *before* importing GTK, otherwise it will cause some unexpected segfaults
# GTK doesn't enable X11's (Un)LockDisplay functions which allow multiple threads to safely draw to the same X window.
# VLC needs this functionality to do accelarated rendering.
#
# NOTE: This must be the first thing done with X11, as such it needs to be called before even importing this part of Emcee.
#       I don't know how to check if it has been done, and warn the user accordingly. However VLC does this when initialised
#import ctypes
#x11 = ctypes.cdll.LoadLibrary('libX11.so.6')
#ret = x11.XInitThreads()
#if ret == 0:
#    print('WARNING: X11 could not be initialised for threading, VLC performance will be signifcantly reduced', file=sys.stderr)

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


class VLCWidget(Gtk.DrawingArea):
    # These are the event signals that can be triggered by this widget
    # FIXME: I suspect I'm using GTK's signals wrongly, and am supposed to use them to call things interal to the widget,
    #        not just to signal when the widget has done things.
    #    eg, load_thing() should not emit('loaded') but rather emit('load_thing') should trigger do_load_thing()
    __gsignals__ = {
        'end_reached': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'time_changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'position_changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'volume_changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
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
    volume = 0
    length = 0
    paused = True
    state = 'NothingSpecial'  # This string is copied from VLC's default state
    instance = None

    def emit(self, ev_name, *args, **kwargs):
        logging.debug('VLCWidget emitting %s', ev_name)
        super(VLCWidget, self).emit(ev_name, *args, **kwargs)

    def __init__(self, *args):

        # Initialise the DrawingArea
        super(VLCWidget, self).__init__(*args)
        self.set_size_request(640, 360)  # FIXME: Magic number, is a small 16:9 ratio for the default window size
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
        # Perhaps "Title" actually refers to DVD Title, not the name of the current media
        self.event_manager.event_attach(vlc.EventType.MediaPlayerAudioVolume, self._on_volume_changed)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, lambda _: self.emit('end_reached'))
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, lambda _: self.emit('error'))

        self.connect("destroy", self._destroy)

        # Some of the required initialisation doesn't actually work until the GTK widget has been realised,
        # so we split that into a separate function.
        self.connect("realize", self._realize)

    def _realize(self, widget, data=None):
        logging.debug('VLCWidget realizing')
        win_id = widget.get_window().get_xid()
        self.player.set_xwindow(win_id)

        self.emit('initialised')

    def _destroy(self, *args):
        logging.debug("VLCWidget Destroying")
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

    def _on_volume_changed(self, event):
        # Surprisingly, the VLC event object doesn't include the new volume.
        # So Need to query that here
        self.volume = self.player.audio_get_volume() / 100
        self.emit('volume_changed')

    def _on_time_changed(self, event):
        self.time = event.u.new_time / 1000
        self.emit('time_changed')

    def _on_position_changed(self, event):
        self.position = event.u.new_position
        self.emit('position_changed')

    ## Internally used functions ##
    def _load_media(self, uri, local=True):
        """Load a new media file/stream, and whatever else is involved therein"""

        logging.debug('VLDWidget loading media')
        if not self.instance:
            logging.debug('    deffered')
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

    ## Querying media info ##
    def get_title(self):
        return self.player.get_media().get_meta(vlc.Meta.Title)

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
        """Jump forward or back in the media, unlike set_time() this deals with relative time.

           Suggest when using this to call it with inc=+10 rather than just inc=10
           While they are effectively the same thing,
           conceptually the former makes more sense and avoids confusion between increment_ and set_
        """

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
        logging.debug(self.audio_tracks)
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
        """Increment through audio tracks in the order they come from get_audio_tracks()

           Suggest when using this to call it with inc=+10 rather than just inc=10
           While they are effectively the same thing,
           conceptually the former makes more sense and avoids confusion between increment_ and set_
        """
        if len(self.audio_tracks) == 1 and -1 in self.audio_tracks:
            return 'No audio_tracks found'

        # Find the current index and compare with the increment.
        index = list(self.audio_tracks.keys()).index(self.player.audio_get_track())
        index += inc
        index = index % len(self.audio_tracks)  # In case it's above the max or below 0

        return self.set_audio_track(index)

    def set_volume(self, value):
        """Set the volume to a specific percentage"""
        self.player.audio_set_volume(int(value * 100))
        return value  # FIXME: This blindly assumes the volume change worked

    def increment_volume(self, inc):
        """Increment volume by a percentage of the total

           Suggest when using this to call it with inc=+10 rather than just inc=10
           While they are effectively the same thing,
           conceptually the former makes more sense and avoids confusion between increment_ and set_
        """
        value = self.volume + inc
        return self.set_volume(value)
