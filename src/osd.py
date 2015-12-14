#!/usr/bin/python3

import datetime
from gi.repository import Gtk, Gdk, GdkPixbuf, GdkX11

margin = 10

osd = Gtk.Window(title='OSD',role='OSD',resizable=False,decorated=False,accept_focus=False)

def on_show(self, *args, **kwargs):
    # Set window position
    ## I couldn't wrap my head around how gravity worked etc, but I'm doing this how the documentation says to do it and it works.
    ##
    ## https://developer.gnome.org/gtk3/stable/GtkWindow.html#gtk-window-move
    osd.set_gravity(Gdk.Gravity.NORTH_EAST)
    screen = osd.get_screen()
    win_size = osd.get_size()
    x_pos = screen.width()-margin-win_size[0]
    y_pos = margin
    osd.move(x_pos,y_pos)

osd.set_keep_above(True)
osd.set_border_width(0)
osd.connect('show', on_show)

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

overlay = Gtk.Overlay()
osd.add(overlay)

osd_bg = Gtk.Image.new_from_file('osd_bg.png')
osd_bg.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1)) # Set the background to black

overlay.add(box)

overlay.add_overlay(osd_bg)

label = Gtk.Label('foo')
label.set_justify(Gtk.Justification.LEFT)
label.set_markup('<span size="450000">foobar</span>')
#overlay.add_overlay(label)
box.add(label)
label2 = Gtk.Label('bar')
box.add(label2)

def show():
    osd.show_all()
def hide():
    osd.hide()


if __name__ == '__main__':
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--progress', '-p', action='store', nargs='?', default=0, type=int)
    parser.add_argument('text', action='store', type=str)
    args = parser.parse_args(sys.argv[1:])
    print args.progress, args.text
    show()
    Gtk.main()
