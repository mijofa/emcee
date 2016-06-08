#!/usr/bin/python3

from gi.repository import Gtk, Gdk, GObject
from gi.repository import GdkX11 # needed for get_xid() even though it's never actually mentioned

# Make VLC's threading play nicely with GObject's
GObject.threads_init()

import sys
# Make sure you get the right version of python-vlc to match your installed version of VLC, acquired from here
# https://www.olivieraubert.net/vlc/python-ctypes/
import vlc

class VLCWidget(Gtk.DrawingArea):
    # These are the event signals that can be triggered by this widget
    __gsignals__ = {
                    'end_reached':      (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                    'time_changed':     (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                    'position_changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                    'paused':           (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                    'playing':          (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                    'media_state':      (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                    'error':            (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                   }

    # Initialise state variables
    time = 0
    position = 0
    length = 0
    paused = True
    state = 'NothingSpecial' # This string is copied from VLC's default state

    def __init__(self, *args):

        # Initialise the DrawingArea
        super(VLCWidget, self).__init__(*args)
        self.override_background_color(0, Gdk.RGBA(red=0,green=0,blue=0)) # Fill it with black

        # Create the VLC instance, and tell it how to inject itself into the DrawingArea widget.
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        ## FIXME: Can self.player.video_set_callbacks be used to inject frames into the widget instead of this?
        self.connect("map", lambda _: self.player.set_xwindow(self.get_property('window').get_xid()))

        # Set up hooks to the VLC event manager to trigger some Python functions
        ## FIXME: Should these all be changed to emit GObject signals?
        #
        # This is all the possible EventType's that can be triggered on, they aren't all from the MediaPlayer object, some come from other VLC objects only
        #
        # ['MediaDiscovererEnded', 'MediaDiscovererStarted', 'MediaDurationChanged', 'MediaFreed', 'MediaListEndReached', 'MediaListItemAdded', 'MediaListItemDeleted', 'MediaListPlayerNextItemSet', 'MediaListPlayerPlayed', 'MediaListPlayerStopped', 'MediaListViewItemAdded', 'MediaListViewItemDeleted', 'MediaListViewWillAddItem', 'MediaListViewWillDeleteItem', 'MediaListWillAddItem', 'MediaListWillDeleteItem', 'MediaMetaChanged', 'MediaParsedChanged', 'MediaPlayerAudioDevice', 'MediaPlayerAudioVolume', 'MediaPlayerBackward', 'MediaPlayerBuffering', 'MediaPlayerChapterChanged', 'MediaPlayerCorked', 'MediaPlayerESAdded', 'MediaPlayerESDeleted', 'MediaPlayerESSelected', 'MediaPlayerEncounteredError', 'MediaPlayerEndReached', 'MediaPlayerForward', 'MediaPlayerLengthChanged', 'MediaPlayerMediaChanged', 'MediaPlayerMuted', 'MediaPlayerNothingSpecial', 'MediaPlayerOpening', 'MediaPlayerPausableChanged', 'MediaPlayerPaused', 'MediaPlayerPlaying', 'MediaPlayerPositionChanged', 'MediaPlayerScrambledChanged', 'MediaPlayerSeekableChanged', 'MediaPlayerSnapshotTaken', 'MediaPlayerStopped', 'MediaPlayerTimeChanged', 'MediaPlayerTitleChanged', 'MediaPlayerUncorked', 'MediaPlayerUnmuted', 'MediaPlayerVout', 'MediaStateChanged', 'MediaSubItemAdded', 'MediaSubItemTreeAdded', 'VlmMediaAdded', 'VlmMediaChanged', 'VlmMediaInstanceStarted', 'VlmMediaInstanceStatusEnd', 'VlmMediaInstanceStatusError', 'VlmMediaInstanceStatusInit', 'VlmMediaInstanceStatusOpening', 'VlmMediaInstanceStatusPause', 'VlmMediaInstanceStatusPlaying', 'VlmMediaInstanceStopped', 'VlmMediaRemoved']

        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerLengthChanged, self._on_length)             # Should really only trigger when loading new media
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self._on_paused)                    #
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_playing)                  #
        self.event_manager.event_attach(vlc.EventType.MediaPlayerTimeChanged, self._on_time_changed)         # Current position in milliseconds
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, self._on_position_changed) # Current position in percentage of total
        #self.event_manager.event_attach(vlc.EventType.MediaPlayerTitleChanged, self._on_title_changed)      # FIXME: Doesn't trigger, might be that my test file is insufficient
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, lambda _:self.emit('end_reached'))

        self.event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, lambda _:self.emit('error'))

    def _on_length(self, event):
        self.length = event.u.new_length/1000
    def _on_paused(self, event):
        self.paused = True
        self.emit('paused')
    def _on_playing(self, event):
        self.paused = False
        self.emit('playing')
    def _on_time_changed(self, event):
        self.time = event.u.new_time/1000
        self.emit('time_changed')
    def _on_position_changed(self, event):
        self.position = event.u.new_position
        self.emit('position_changed')

    def _load_media(self, uri, local=True):
        """Load a new media file/stream, and whatever else is involved therein"""

        ##FIXME: Handle loading of subtitles as well
        ##       If a .srt or similar is placed with the media file, load that and turn them on by default. (I think VLC does this automatically)
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
#        media_em.event_attach(vlc.EventType.MediaMetaChanged,  self._on_meta_change)

        self.player.set_media(media)
        ## FIXME: SPU tracks is unknown here, has to have played the media a bit first.
        print(self.player.video_get_spu_description())

    def _on_state_change(self, event):
        # All possible states at time of writing --Mike June 2016
        #
        # ['Buffering', 'Ended', 'Error', 'NothingSpecial', 'Opening', 'Paused', 'Playing', 'Stopped']

        ## Reverse VLC's enum to get the name from the value.
        ## This is not at all intuitive, but I'm at the mercy of the VLC library here.
        self.state = vlc.State._enum_names_[event.u.new_state]

        self.emit('media_state')

    def _on_meta_change(self, event):
        """Handle title changes and such here, mainly for streaming media"""
        ## FIXME: Not actually sure if useful
        pass

    def play(self, uri=None, local=True):
        """Unpause if currently paused, or load new media if uri is set"""

        if uri:
            self._load_media(uri, local=local)
            self.show_all()

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

        milliseconds = int(seconds*1000) # VLC's logic deals with milliseconds

        ##FIXME: Add logic to avoid going past the beginning or end of the media?
        if self.player.is_seekable():
            self.player.set_time(milliseconds)

        return int(self.player.get_time()/1000)

    def seek(self, seconds):
        """Jump forward or back in the media, unlike set_time() this deals with relative time.."""

        return self.set_time(self.time+seconds)


if __name__ == '__main__':
    window = Gtk.Window(title='Emcee')
    window.connect("destroy", lambda q: Gtk.main_quit()) # Quit & cleanup when closed
    window.show()

    vid = VLCWidget()
    window.add(vid)
    vid.play(sys.argv[1])

    ## Keyboard input setup
    keybindings = {
        'space':        vid.toggle_pause,
        'Left':         lambda: vid.seek(-20), # 20 seconds back
        'Right':        lambda: vid.seek(+30), # 30 seconds forward
        'F':            window.fullscreen,
        'f':            window.unfullscreen,
        'BackSpace':    vid.stop,
        'i':            lambda: print(vid.get_subtitles()),
        'p':            lambda: vid.play(sys.argv[1]),
        'Escape':       Gtk.main_quit,
        's':            lambda: print(vid.increment_subtitles()),
    }

    def on_key_press(window, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname in keybindings.keys():
            keybindings[keyname]()
        else:
            print('no keybinding found for %s' % keyname)

    window.connect("key_press_event", on_key_press)

    ## CLI output, showing current position and state
    bar_length = 40 # FIXME: Somehow detect width of terminal and set this accordingly
    def update_status(vid_widget):
        """Make a fancy looking progressbar with numbers for how far into the current movie you are"""
        if vid_widget.state not in ('Playing', 'Paused', 'Ended'):
            print('Unknown state:', vid_widget.state)
            return
        current_min = int(vid_widget.time/60)
        current_sec = int(vid_widget.time%60)
        current_progress = vid_widget.position
        bar = ''
        for i in range(0, int(bar_length*vid_widget.position)-1):
            bar += '='
        bar += '||' if vid_widget.paused else '|>'
        for i in range(len(bar)-1, bar_length):
            bar += '-'
        length_min = int(vid_widget.length/60)
        length_sec = int(vid_widget.length%60)
        # This does space padding for 4 characters ( 4) removes any decimal points (.0) and displays it as a percentage (%): "{p: 4.0%}"
        print("\r{cm:02}:{cs:02} [{bar}] {p: 4.0%} {lm:02}:{ls:02} ".format(
                cm=current_min, cs=current_sec,
                bar=bar, p=current_progress,
                lm=length_min, ls=length_sec),
            end='')

    # FIXME: Should I hook this to other events?
    vid.connect('paused',           update_status)
    #vid.connect('position_changed', update_status) # Only really need either time or position, not both
    vid.connect('time_changed',     update_status)
    vid.connect('media_state',      update_status)

    ## Once off resize when loading media
    def resize(vid_widget):
        size = vid_widget.player.video_get_size()
        if size != (0,0):
            window.resize(*size)
            vid.disconnect(resize_event)

    # FIXME: Not actually resizing every time
    resize_event = vid.connect('position_changed', resize) # Gets cleared from inside the resize function

    vid.connect('error',        lambda _:Gtk.main_quit()) # Quit & cleanup when VLC has an error
    vid.connect('end_reached',  lambda _:Gtk.main_quit()) # Quit & cleanup when finished media file
    Gtk.main()
