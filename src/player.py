#!/usr/bin/python3
import pprint

from gi.repository import Gtk, Gdk, GObject
from gi.repository import GdkX11 # needed for get_xid()

# Make VLC's threading play nicely with GObject's
GObject.threads_init()

import sys
import vlc

vid_states = vlc.State

class PlayerException(Exception):
    """Generic exception for VLC's errors"""
    def __init__(self, player, *args):
        self.player = player
        super(PlayerException, self).__init__(*args)

class VLCWidget(Gtk.DrawingArea):
    __gsignals__ = {
                    'end_reached': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                    'time_changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                    'position_changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                   }
    time = 0
    position = 0

    def __init__(self, *args):

        # Initialise the DrawingArea
        super(VLCWidget, self).__init__(*args)
        self.override_background_color(0, Gdk.RGBA(red=0,green=0,blue=0)) # Fill it with black

        # Create the VLC instance, and tell it how to inject itself into the DrawingArea widget.
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.connect("map", lambda _: self.player.set_xwindow(self.get_property('window').get_xid()))

        # Connect some of VLC's events to GTK events
        ## FIXME: Should these all be changed to emit GObject signals?
        #
        # ['MediaDiscovererEnded', 'MediaDiscovererStarted', 'MediaDurationChanged', 'MediaFreed', 'MediaListEndReached', 'MediaListItemAdded', 'MediaListItemDeleted', 'MediaListPlayerNextItemSet', 'MediaListPlayerPlayed', 'MediaListPlayerStopped', 'MediaListViewItemAdded', 'MediaListViewItemDeleted', 'MediaListViewWillAddItem', 'MediaListViewWillDeleteItem', 'MediaListWillAddItem', 'MediaListWillDeleteItem', 'MediaMetaChanged', 'MediaParsedChanged', 'MediaPlayerAudioDevice', 'MediaPlayerAudioVolume', 'MediaPlayerBackward', 'MediaPlayerBuffering', 'MediaPlayerChapterChanged', 'MediaPlayerCorked', 'MediaPlayerESAdded', 'MediaPlayerESDeleted', 'MediaPlayerESSelected', 'MediaPlayerEncounteredError', 'MediaPlayerEndReached', 'MediaPlayerForward', 'MediaPlayerLengthChanged', 'MediaPlayerMediaChanged', 'MediaPlayerMuted', 'MediaPlayerNothingSpecial', 'MediaPlayerOpening', 'MediaPlayerPausableChanged', 'MediaPlayerPaused', 'MediaPlayerPlaying', 'MediaPlayerPositionChanged', 'MediaPlayerScrambledChanged', 'MediaPlayerSeekableChanged', 'MediaPlayerSnapshotTaken', 'MediaPlayerStopped', 'MediaPlayerTimeChanged', 'MediaPlayerTitleChanged', 'MediaPlayerUncorked', 'MediaPlayerUnmuted', 'MediaPlayerVout', 'MediaStateChanged', 'MediaSubItemAdded', 'MediaSubItemTreeAdded', 'VlmMediaAdded', 'VlmMediaChanged', 'VlmMediaInstanceStarted', 'VlmMediaInstanceStatusEnd', 'VlmMediaInstanceStatusError', 'VlmMediaInstanceStatusInit', 'VlmMediaInstanceStatusOpening', 'VlmMediaInstanceStatusPause', 'VlmMediaInstanceStatusPlaying', 'VlmMediaInstanceStopped', 'VlmMediaRemoved']

        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self.on_paused)                    #
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self.on_playing)                  #
        self.event_manager.event_attach(vlc.EventType.MediaPlayerTimeChanged, self.on_time_changed)         # Current position in milliseconds
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, self.on_position_changed) # Current position in percentage of total
        #self.event_manager.event_attach(vlc.EventType.MediaPlayerTitleChanged, self.on_title_changed)      # FIXME: Doesn't trigger, might be that my test file is insufficient
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, lambda _:self.emit('end_reached'))

        self.event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self.on_error)

    def on_error(self, event):
        raise PlayerException(self.player, 'foobar')

    def on_paused(self, *args):
        print('paused', args)
    def on_playing(self, *args):
        print('playing', args)
    def on_time_changed(self, event):
        self.time = event.u.new_time/1000
        self.emit('time_changed')
    def on_position_changed(self, event):
        self.position = event.u.new_position
        self.emit('position_changed')

    def _load_media(self, uri):
        """Load a new media file/stream, and whatever else is involved therein"""

        ##FIXME: Handle loading of subtitles as well
        ##       If a .srt or similar is placed with the media file, load that and turn them on by default. (I think VLC does this automatically)
        ##       Otherwise turn them off by default, but search for them automatically at http://thesubdb.com/
        ##       TV stream telx & similar should be turned off by default as well.
        self.media = self.instance.media_new(uri)
        self.player.set_media(self.media)

    def play(self, uri=None):
        """Unpause if currently paused, or load new media if uri is set"""

        if uri:
            self._load_media(uri)

        self.show_all()
        return self.player.play()

    def stop(self):
        """Stop all playback, and hide the player"""

        self.hide()
        return self.player.stop()

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

if __name__ == '__main__':
    window = Gtk.Window(title='Emcee')
    window.connect("destroy", lambda q: Gtk.main_quit())
    window.show()
    window.set_size_request(1, 3)

    vid = VLCWidget()
    window.add(vid)
    vid.show()
    vid.play(sys.argv[1])

    keybindings = {
        'space': vid.toggle_pause,
        'Left':  lambda: vid.seek(-20), # 20 seconds back
        'Right': lambda: vid.seek(+30), # 30 seconds forward
        'F':     window.fullscreen,
        'f':     window.unfullscreen,
        's':     vid.stop,
        'i':     lambda: print(vid.player.get_time()),
        'p':     lambda: vid.play(sys.argv[1]),
        'Escape':Gtk.main_quit,
    }

    def on_key_press(window, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname in keybindings.keys():
            print(keyname, keybindings[keyname]())
        else:
            print('no keybinding found for %s' % keyname)

    window.connect("key_press_event", on_key_press)
    vid.connect('end_reached', lambda _:Gtk.main_quit())
    #vid.connect('position_changed', lambda a: print(a.position)) # Use this for a progress bar
    #vid.connect('time_changed', lambda a: print(a.time))         # Use this for setting the actual number next to said progress bar

    Gtk.main()
