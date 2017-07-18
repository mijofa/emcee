#!/usr/bin/python3
# NOTE: Consider running this with the GDK_SCALE environment variable set to force all elements to be bigger,
#       This might be an easier way to implement the 10-foot UI.
import os
import sys
import logging
import warnings
logging_level = os.environ.get('EMCEEDEBUG')
if logging_level:
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

from gi.repository import Gtk, Gdk, GObject
import emcee.osd
import emcee.player

media_uri = sys.argv[1]

window = Gtk.Window(title='Emcee')
window.connect("destroy", lambda q: Gtk.main_quit())  # Quit & cleanup when closed
window.show()

overlay = Gtk.Overlay()
window.add(overlay)

vid = emcee.player.VLCWidget()
overlay.add(vid)

## OSD
osd = emcee.osd.OSD()
overlay.add_overlay(osd)

# Can't just use overlay.show_all() because I want to use the OSD's show with smaller timeout than default
vid.show_all()
overlay.show()
osd.show(3)

## Keyboard input setup
# FIXME: Make this configurable via a config file
keybindings = {
    # Volume
    'Up': lambda: vid.emit('increment_volume', +0.02),
    'Down': lambda: vid.emit('increment_volume', -0.02),

    # Time manipulation
    'space': lambda: vid.emit('toggle_pause'),
    'Left': lambda: vid.emit('seek', -20),  # 20 seconds back
    'Right': lambda: vid.emit('seek', +30),  # 30 seconds forward
    'Page_Up': lambda: vid.emit('seek', -300),  # 5 minutes back
    'Page_Down': lambda: vid.emit('seek', +300),  # 5 minutes forward
    'Home': lambda: vid.emit('set_time', 0),  # Jump to beginning
    'End': lambda: vid.emit('set_time', -5),  # Jump to end (almost), for testing only

    'p': lambda: vid.emit('play'),
    'BackSpace': lambda: vid.emit('stop'),

    'F': window.fullscreen,
    'f': window.unfullscreen,

    'i': osd.toggle,

    's': lambda: print(vid.increment_subtitles()),
    'S': lambda: print(vid.get_subtitles()),
    'a': lambda: print(vid.increment_audio_track()),
    'A': lambda: print(vid.get_audio_tracks()),

    'Escape': Gtk.main_quit,
}


def on_key_press(window, event):
    keyname = Gdk.keyval_name(event.keyval)
    if keyname in keybindings.keys():
        logger.debug('Key pressed: %s', keyname)
        if keybindings[keyname].__name__ == '<lambda>':
            # Magic to try and pull some useful info from the lambda's code
            logger.debug('Running lambda: %s %s',
                         keybindings[keyname].__code__.co_names,
                         keybindings[keyname].__code__.co_consts,
                         )
        else:
            logger.debug('Running functon: %s', keybindings[keyname].__name__)
        # Run the function or lambda stored in the keybindings dict
        keybindings[keyname]()
    else:
        logger.debug('No keybinding found for %s', keyname)

window.connect("key_press_event", on_key_press)

## This was written before the OSD was implemented, when I wanted some form of status info on the terminal.
## Unnecessary now, but perhaps useful for reference.
#
# ## CLI output, showing current position and state
# bar_length = 40  # FIXME: Somehow detect width of terminal and set this accordingly
#
#
# def update_status(vid_widget):
#     """Make a fancy looking progressbar with numbers for how far into the current movie you are"""
#     if vid_widget.state == 'Opening':
#         print('Loading', vid_widget.player.get_media().get_mrl())
#     elif vid_widget.state not in ('Playing', 'Paused', 'Ended'):
#         logger.info('VLC in unknown state: %s', vid_widget.state)
#         return
#     current_min = int(vid_widget.time / 60)
#     current_sec = int(vid_widget.time % 60)
#     bar = ''
#     for i in range(0, int(bar_length * vid_widget.position) - 1):
#         bar += '='
#     bar += '||' if vid_widget.paused else '|>'
#     for i in range(len(bar) - 1, bar_length):
#         bar += '-'
#     length_min = int(vid_widget.length / 60)
#     length_sec = int(vid_widget.length % 60)
#     # This does space padding for 4 characters (4) removes any decimal points (.0) and displays it as a percentage (%):
#     #     {p:4.0%}
#     print(
#         "\r{cm:02}:{cs:02} [{bar}] {p:4.0%} {lm:02}:{ls:02} V: {v:4.0%} ".format(
#             cm=current_min, cs=current_sec,
#             bar=bar,
#             p=vid_widget.position,
#             lm=length_min, ls=length_sec,
#             v=vid_widget.volume),
#         end='')
#
# # FIXME: Should I hook this to other events?
# vid.connect('paused', update_status)
# #vid.connect('position_changed', update_status)  # Only really need either time or position, not both
# vid.connect('time_changed', update_status)
# vid.connect('volume_changed', update_status)
# vid.connect('media_state', update_status)


# FIXME: This also triggers when the media is first loaded, I don't want that.
#        Perhaps I can set an event hook to trigger *after* media loads, which then sets up this hook?
vid.connect('volume_changed', lambda _: osd.push_status("Volume: {v:4.0%}".format(v=vid.volume)))


## Resize when media is finished loading (don't know the resolution before that)
def on_load(vid_widget):
    media_title = vid_widget.get_title()
    media_title = media_title.rpartition('.')[0]  # FIXME: Will there always be an extension?
    window.set_title('Emcee - {}'.format(media_title))
    # NOTE: Without using idle_add here an intermittent issue will occur with Gtk getting stuck.
    GObject.idle_add(osd.set_title, media_title)
    size = vid_widget.player.video_get_size()
    if size != (0, 0):
        # NOTE: Without using idle_add here an intermittent issue will occur with Gtk getting stuck.
        GObject.idle_add(window.resize, *size)

vid.connect('loaded', on_load)

# FIXME: This doesn't cleanup VLC
#        Ideally GTK would have a on_quit hook of some sort where I can tell it to destroy the VLC instance and such.
#        My Google-fu seems to indicate that is not the case so I may need a custom emcee.quit() function that does all of that
vid.connect('error', lambda _: Gtk.main_quit())  # Quit & cleanup when VLC has an error
vid.connect('end_reached', lambda _: Gtk.main_quit())  # Quit & cleanup when finished media file

vid.load_media(media_uri)
vid.emit('play')
Gtk.main()
