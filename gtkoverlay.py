#!/usr/bin/python3

from gi.repository import Gtk, Gdk, GdkPixbuf, GdkX11, GLib

import vlc

osd_margin = 10

instance = vlc.Instance()

class VLCWidget(Gtk.DrawingArea):
  def __init__(self, *p):
    Gtk.DrawingArea.__init__(self)
    self.set_size_request(1024,768)
    self.player = instance.media_player_new()
    def handle_embed(*args):
      self.player.set_xwindow(self.get_property('window').get_xid())
      return True
    self.connect("map", handle_embed)

window = Gtk.Window()
window.connect("destroy", lambda q: Gtk.main_quit())
window.show()

vid = VLCWidget()
vid.player.set_media(instance.media_new('/home/mike/Videos/tv/Internal/P1.ogv'))
vid.set_halign(Gtk.Align.START)
vid.set_valign(Gtk.Align.START)
window.add(vid)
vid.show()
vid.player.play()

class osd_window(Gtk.Window):
    def __init__(self):
        super(osd_window, self).__init__(title='OSD',role='OSD',resizable=False,decorated=False,accept_focus=False)
        self.set_keep_above(True)
        self.set_border_width(0)
        self.connect('show', self.reposition)

    def reposition(self, *args, **kwargs):
        # Set OSD position based on the position of the main window
        osd_size = self.get_size()
        main_win_pos = window.get_position()
        main_win_size = window.get_size()
        size_offset = (main_win_size[0]-osd_size[0], main_win_size[1]-osd_size[1])
        self.move(main_win_pos[0]+size_offset[0]-osd_margin, main_win_pos[1]+osd_margin)

osd = osd_window()
window.connect('configure-event', osd.reposition)
overlay = Gtk.Overlay()
osd.add(overlay)
osd_bg = Gtk.Image.new_from_file('osd_bg.png')
osd_bg.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1)) # Set the background to black
overlay.add(osd_bg)
textview = Gtk.TextView()
##textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
textbuffer = textview.get_buffer()
textbuffer.set_text("Welcome to the PyGObject Tutorial\n\nThis guide aims to provide an introduction to using Python and GTK+.\n\nIt includes many sample code files and exercises for building your knowledge of the language.", -1)
textview.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0)) # Set the background to transparent
textview.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1)) # Set the foreground to white
overlay.add_overlay(textview)

osd.show_all()

if __name__ == '__main__':
    Gtk.main()
