#!/usr/bin/python3
import sys
import logging
logger = logging.getLogger(__name__)

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

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GObject', '2.0')
gi.require_version('GdkX11', '3.0')
from gi.repository import Gtk, GObject
# Without GdkX11 being imported GTK widgets don't get the get_xid() function,
# so even though this widget is never directly called we still need to import it.
from gi.repository import GdkX11  # noqa: F401

# Make VLC's threading play nicely with GObject's
# Must be done before importing VLC
GObject.threads_init()

# Make sure you get the right version of python-vlc to match your installed version of VLC, acquired from here
# https://www.olivieraubert.net/vlc/python-ctypes/
import vlc


# I've tried a whole bunch of widgets other than DrawingArea, but nothing seems to allow the VLC window to sit below th OSD overlay
class VLCWidget(Gtk.DrawingArea):
    # These are the event signals that can be triggered by this widget
    # FIXME: I suspect I'm using GTK's signals wrongly, and am supposed to use them to call things interal to the widget,
    #        not just to signal when the widget has done things.
    #    eg, load_thing() should not emit('loaded') but rather emit('load_thing') should trigger do_load_thing()
    #
    # Despite common-sense, the SIGNAL_ACTION is is for things that don't have an associated internal action.
    # I think they are meant only to indicate an action has happened, and to trigger an external reaction.
    __gsignals__ = {
        # Signals emitted internally for status updates to be collected externally
        'end_reached': (GObject.SIGNAL_ACTION, None, ()),
        'time_changed': (GObject.SIGNAL_ACTION, None, (int,)),
        'position_changed': (GObject.SIGNAL_ACTION, None, (int,)),
        'volume_changed': (GObject.SIGNAL_ACTION, None, (int,)),
        'paused': (GObject.SIGNAL_ACTION, None, ()),
        'playing': (GObject.SIGNAL_ACTION, None, ()),
        'media_state': (GObject.SIGNAL_ACTION, None, (str,)),
        'error': (GObject.SIGNAL_ACTION, None, ()),
        'loaded': (GObject.SIGNAL_ACTION, None, ()),
        # Signals emitted externally to trigger an action internally
        'play': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'pause': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'toggle_pause': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'stop': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'seek': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'set_time': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'set_volume': (GObject.SIGNAL_RUN_FIRST, None, (float,)),
        'increment_volume': (GObject.SIGNAL_RUN_FIRST, None, (float,)),
        'set_subtitles': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'increment_subtitles': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'set_audio_track': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'increment_audio_track': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
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
        logger.debug('VLCWidget emitting %s', ev_name)
        super().emit(ev_name, *args, **kwargs)

    def do_draw(self, context):
        """Since VLC doesn't add the black borders around media of different aspect ratios,
           we have to draw that ourselves.
           This can't be done in CSS, or using (deprecated) override_background_color()
           because Gtk.DrawingArea is intentionally too dumb to do that.
        """
        # FIXME: Can we do this just when resizing?
        #        Seems inneficient to redraw every frame when it never changes.
        # NOTE: This requires the cairo gi libraries be installed, although not imported
        context.set_source_rgb(0, 0, 0)
        context.paint()

    def __init__(self, *args):

        # Initialise the DrawingArea
        super(VLCWidget, self).__init__(*args)
        self.set_size_request(640, 360)  # FIXME: Magic number, is a small 16:9 ratio for the default window size

        # Create the VLC instance, and tell it how to inject itself into the DrawingArea widget.
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        # Set up hooks to the VLC event manager to trigger some Python functions
        ## FIXME: Should these all be changed to emit GObject signals?

        # FIXME: Use Gtk.Builder.connect_signals() to do all of this in one call?
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

        # ['Buffering', 'Ended', 'Error', 'NothingSpecial', 'Opening', 'Paused', 'Playing', 'Stopped']
        self.event_manager.event_attach(vlc.EventType.MediaPlayerNothingSpecial, self._on_state_change, 'NothingSpecial')
        self.event_manager.event_attach(vlc.EventType.MediaPlayerOpening, self._on_state_change, 'Opening')
        self.event_manager.event_attach(vlc.EventType.MediaPlayerBuffering, self._on_state_change, 'Buffering')
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_state_change, 'Playing')
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self._on_state_change, 'Paused')
        self.event_manager.event_attach(vlc.EventType.MediaPlayerStopped, self._on_state_change, 'Stopped')
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_state_change, 'Ended')
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_state_change, 'Error')

        # VLC has a MediaPlayerCorked (and associated uncorked) event that confused me.
        # This event is triggered by PulseAudio "corking" and muting the application's audio output,
        # which it will sometimes do if it believes a phone app or similar has started playing audio.
        # For now I'm ignoring this event, in future might be worth at least telling the user why the audio cut out,
        # or perhaps automatically pausing if not watching a live stream.

        self.connect("destroy", self._destroy)

        # Some of the required initialisation doesn't actually work until the GTK widget has been realised,
        # so we split that into a separate function.
        self.connect("realize", self._realize)

    def _realize(self, widget, data=None):
        logger.debug('VLCWidget realizing')
        win_id = widget.get_window().get_xid()
        self.player.set_xwindow(win_id)

    def _destroy(self, *args):
        logger.debug("VLCWidget Destroying")
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
        self.emit('volume_changed', self.volume)

    def _on_time_changed(self, event):
        if self.state == 'Buffering':
            # The media state doesn't get updated when we finish buffering
            # If the time/position is changing, then clearly we've finished buffering
            self._on_state_change(None, 'Playing')
        self.time = event.u.new_time / 1000
        self.emit('time_changed', self.time)

    def _on_position_changed(self, event):
        if self.state == 'Buffering':
            # The media state doesn't get updated when we finish buffering
            # If the time/position is changing, then clearly we've finished buffering
            self._on_state_change(None, 'Playing')
        self.position = event.u.new_position
        self.emit('position_changed', self.position)

    ## Internally used functions ##
    def _on_state_change(self, vlc_event, state):
        if state == 'Playing':
            # Multicast streams don't really trigger the buffering callback very reliably.
            # So we check if the demuxer has processed any data yet before marking it as 'Playing'
            mstats = vlc.MediaStats()
            self.player.get_media().get_stats(mstats)
            if mstats.demux_read_bytes == 0:
                state = 'Buffering'

        self.state = state
        self.emit('media_state', self.state)

    def do_media_state(self, state):
        self.state = state

    def _on_parsed(self, event):
        """Handle once-off reading of media metadata"""
        # This function triggers when parsed state changes not just when it's parsed, so check that it is currently parsed
        if self.player.get_media().is_parsed():
            if 0 == self.player.audio_get_track_count():
                self.audio_tracks = {-1: 'No audio tracks found'}
            else:
                self.audio_tracks = dict(self.player.audio_get_track_description())
                self.audio_tracks[-1] = 'Disabled'  # FIXME: Should this "track" be removed in favour of mute/unmute

            # FIXME: Is there more things to process here? Multiple video tracks?
            self.emit('loaded')

    ## Querying media info ##
    def get_title(self):
        # FIXME: This doesn't reliably get the current track title.
        #        NowPlaying is sometimes the current track, sometimes None.
        #        Title is almost always the URL of the current stream.
        media = self.player.get_media()
        title = media.get_meta(vlc.Meta.Title)
        if '://' in title: # FIXME: use urlparse or something
            title = ""
        nowplaying = media.get_meta(vlc.Meta.NowPlaying)
        print("New title:", nowplaying, title)
        return nowplaying or title

    ## Playback control functions ##
    def load_media(self, uri, local=True):
        """Load a new media file/stream, and whatever else is involved therein"""

        logger.debug('VLDWidget loading media')

        ##FIXME: Handle loading of subtitles as well
        ##       If a .srt or similar is placed with the media file, load that and turn them on by default.
        ##       Does VLC do that automatically?
        ##
        ##       Otherwise turn them off by default, but search for them automatically at http://thesubdb.com/
        ##       TV stream telx & similar should be turned off by default as well.

        # VLC detects local vs. remote URIs by simply checking if there is a ':' character in it, this is insufficient.
        ## FIXME: Actually automate this using better heuristics rather than just passing that test off to the user
        ##        Used urlparse.urlparse for this test in UPMC
        logger.debug('VLCWidget actually loading media')
        if local:
            ## FIXME: bytes() conversion here not necessary for python-vlc 2.2.*
            ##        Should I instead check version at import time and just error out completely if < 2.2?
            if not vlc.libvlc_get_version().startswith(b'2.2.'):
                uri = bytes(uri, sys.getfilesystemencoding())
            media = self.instance.media_new_path(uri)
        else:
            media = self.instance.media_new(uri)

        media_em = media.event_manager()
        # I now do this in the __init__
        #media_em.event_attach(vlc.EventType.MediaStateChanged, self._on_state_change)
        # FIXME: Move ParsedChanged into __init__?
        media_em.event_attach(vlc.EventType.MediaParsedChanged, self._on_parsed)
        # FIXME: Have a self.metadata dictionary that gets updated when this event triggers.
        # FIXME: The meta keeps changing without this event being triggered!
        #media_em.event_attach(vlc.EventType.MediaMetaChanged, lambda _: print('meta_changed'))

        self.player.set_media(media)

    def do_play(self):
        """Play if currently paused or stopped"""

        return self.player.play()

    def do_stop(self):
        """Stop all playback, and hide the player"""

        return self.player.stop()

    def do_toggle_pause(self):
        """Toggle current pause state. Return final state"""

        if self.player.can_pause():
            self.player.pause()
            return self.player.is_playing() == 1
        else:
            return False

    def do_set_time(self, seconds):
        """Jump to certain point in the media, unlike seek() this deals with absolute time."""

        # if trying to set to a negative time, count from the end of the media.
        # FIXME: Is this worthwhile at all?
        if seconds < 0:
            seconds = self.length + seconds

        milliseconds = int(seconds * 1000)  # VLC's logic deals with milliseconds

        ##FIXME: Add logic to avoid going past the beginning or end of the media?
        if self.player.is_seekable():
            self.player.set_time(milliseconds)

        return int(self.player.get_time() / 1000)

    def do_seek(self, seconds):
        """Jump forward or back in the media, unlike set_time() this deals with relative time.

           Suggest when using this to call it with inc=+10 rather than just inc=10
           While they are effectively the same thing,
           conceptually the former makes more sense and avoids confusion between increment_ and set_
        """

        return self.do_set_time(max(0, self.time + seconds))

    def get_current_subtitles(self):
        """Get name of current subtitles track"""
        cur_subs = self._get_subtitles()[self.player.video_get_spu()].decode()
        if cur_subs.startswith('Teletext subtitles - [') and cur_subs.endswith(']'):
            # VLC's identifier for teletext is so long and unnecessary
            cur_subs = cur_subs[22:-1] + ' teletext'
        # FIXME: UPMC had: if cur_subs == "Disable": cur_subs = "Disabled"
        #        I think I effectively solved that problem in _get_subtitles() but I'm not sure
        return cur_subs

    def _get_subtitles(self):
        # FIXME: I needed to do a lot of magic in UPMC to make Teletext work
        #        This seems to have just worked in Emcee and I'm a little concerned there's some missed edge cases
        if 0 == self.player.video_get_spu_count():
            subtitles = {-1: b'No subtitles found'}
        else:
            subtitles = dict(self.player.video_get_spu_description())
            subtitles[-1] = b'Disabled'  # FIXME: Are things other than '-1' used to disable subtitles? Normalise it all
            # FIXME: Might need to do some ugly teletext handling stuff

        return subtitles

    def do_set_subtitles(self, index):
        """Set current subtitles track, index is based on the order from _get_subtitles()"""
        if index == -1:
            # Just turn them off
            self.player.video_set_spu(-1)
            new_subs = 'Disabled'

        subtitles = self._get_subtitles()

        if len(subtitles) == 1:
            new_subs = subtitles[-1]
        elif len(subtitles) > index:  # len() should always include -1 so don't need >=
            # VLC needs the track ID, but I just want to deal with an index from a list of just the subtitles tracks.
            # dict.keys() is a generator and doesn't support indexing, so converting it to a standard list.
            self.player.video_set_spu(list(subtitles.keys())[index])
            new_subs = self.get_current_subtitles()
        else:
            new_subs = 'Subtitles track {} not found'.format(index)

        logger.info("Set subtitle track %s", new_subs)

    def do_increment_subtitles(self, inc=1):
        """Increment through subsitles in the order they come from get_subtitles()"""

        subtitles = self._get_subtitles()

        if len(subtitles) == 1:
            return subtitles[-1]

        # Find the current index and compare with the increment.
        index = list(subtitles.keys()).index(self.player.video_get_spu())
        index += inc
        index = index % len(subtitles)  # In case it's above the max or below 0

        return self.emit('set_subtitles', index)

    def get_current_audio_track(self):
        """Get name of current audio track"""
        return self.audio_tracks[self.player.audio_get_track()]

    def get_audio_tracks(self):
        """Get name of all audio tracks"""
        # FIXME: Subtitles tracks in streaming media got updated as the stream
        #        continued without any event trigger notifying me they'd changed.
        #        Audio tracks are probably the same and need to change a lot of
        #        it into get/set functions and stop relying on
        #        self.audio_tracks.
        return list(self.audio_tracks.values())

    def do_set_audio_track(self, index):
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

    def do_increment_audio_track(self, inc=1):
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

        return self.do_set_audio_track(index)

    def do_set_volume(self, value):
        """Set the volume to a specific percentage"""
        self.player.audio_set_volume(int(value * 100))
        return value  # FIXME: This blindly assumes the volume change worked

    def do_increment_volume(self, inc):
        """Increment volume by a percentage of the total

           Suggest when using this to call it with inc=+10 rather than just inc=10
           While they are effectively the same thing,
           conceptually the former makes more sense and avoids confusion between increment_ and set_
        """
        value = self.volume + inc
        return self.do_set_volume(value)
