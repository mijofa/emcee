#!/usr/bin/python3

from gi.repository import Gtk, Gdk, GdkPixbuf, GdkX11, GLib

## You can not make the overlay partially transparent, give up trying!

class OSD(Gtk.Fixed):
    def __init__(self):
        super(OSD, self).__init__()
        self.set_halign(Gtk.Align.END)
        self.set_valign(Gtk.Align.START)

        bg = Gtk.Image.new_from_file('osd_bg.png')
        # FIXME: Setting background here doesn't seem to work, just go fix the PNG.
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1))  # Set the background to black
        self.put(bg, 0,0)

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show_all()

if __name__ == '__main__':
    win = Gtk.Window()
    osd = OSD()
    win.add(osd)
    textview = Gtk.TextView()
    ##textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    textbuffer = textview.get_buffer()
    textbuffer.set_text("Welcome to the PyGObject Tutorial\n\nThis guide aims to provide an introduction to using Python and GTK+.\n\nIt includes many sample code files and exercises for building your knowledge of the language.", -1)
    textview.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0)) # Set the background to transparent
    textview.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1)) # Set the foreground to white
    osd.add(textview)

    win.show_all()
    Gtk.main()