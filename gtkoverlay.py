#!/usr/bin/python3

from gi.repository import Gtk, Gdk, GdkPixbuf, GdkX11, GLib

import sys
import vlc

osd_margin = 10

instance = vlc.Instance()

class VLCWidget(Gtk.DrawingArea):
  def __init__(self, *p):
    Gtk.DrawingArea.__init__(self)
#    self.set_size_request(1024,768)
    self.player = instance.media_player_new()
    def handle_embed(*args):
      self.player.set_xwindow(self.get_property('window').get_xid())
      return True
    self.connect("map", handle_embed)
  def resize(self, *args):
    self.set_size_request(*self.get_parent().get_size())

window = Gtk.Window(title='Emcee')
window.connect("destroy", lambda q: Gtk.main_quit())
window.show()

vid = VLCWidget()
vid.player.set_media(instance.media_new(sys.argv[1]))
vid.set_halign(Gtk.Align.START)
vid.set_valign(Gtk.Align.START)
window.add(vid)
vid.get_parent().connect('configure-event', vid.resize)
vid.show()
vid.player.play()

class osd_window(Gtk.Window):
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
        if self.is_visible():
            self.hide()
        else:
            self.show_all()
            self.reposition(window)

osd = osd_window(window)
textview = Gtk.TextView()
##textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
textbuffer = textview.get_buffer()
textbuffer.set_text("Welcome to the PyGObject Tutorial\n\nThis guide aims to provide an introduction to using Python and GTK+.\n\nIt includes many sample code files and exercises for building your knowledge of the language.", -1)
textview.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0)) # Set the background to transparent
textview.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1)) # Set the foreground to white
osd.add(textview)

#osd.show_all()

keybindings = {
    'space': vid.player.pause,
    'Left':  lambda: vid.player.set_time(vid.player.get_time()-20000L),
    'Right': lambda: vid.player.set_time(vid.player.get_time()+30000L),
    'F':     window.fullscreen,
    'f':     window.unfullscreen,
    'i':     osd.toggle,
}

def on_key_press(window, event):
    keyname = Gdk.keyval_name(event.keyval)
    if keyname in keybindings.keys():
        print keybindings[keyname]()
    else:
        print('no keybinding found for %s' % keyname)

window.connect("key_press_event", on_key_press)

if __name__ == '__main__':
    Gtk.main()
