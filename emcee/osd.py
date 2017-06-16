#!/usr/bin/python3

import time
from gi.repository import Gtk, Gdk, Pango, GObject

INNER_MARGIN = 5
OUTER_MARGIN = 10

## STOP! You can not make the overlay partially transparent, give up trying!
## FIXME: Either make the OSD variable size based on the window size, or set the minimum app window size to the size of the OSD.


class OSD(Gtk.Overlay):
    def __init__(self):
        # FIXME: The Grid is only as wide as whichever widget has the most text in it. This makes right-aligning things difficult.

        super(OSD, self).__init__()
        # Position self in top-right
        self.set_halign(Gtk.Align.END)
        self.set_valign(Gtk.Align.START)
        # But not the very far-right
        self.set_margin_top(OUTER_MARGIN)
        self.set_margin_right(OUTER_MARGIN)

        bigger_font = Pango.FontDescription()
        bigger_font.set_size(30 * Pango.SCALE)  # FIXME: Magic number, it looks good and takes up just over a 3rd of the OSD height
        big_font = Pango.FontDescription()
        big_font.set_size(25 * Pango.SCALE)  # FIXME: Magic number, it looks good and takes up just under a 3rd of the OSD height

        bg = Gtk.Image.new_from_file('osd_bg.png')
        bg.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))  # Set the background to black
        self.add(bg)

        grid = Gtk.Grid()
        grid.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0))  # Set the background to black
        self.add_overlay(grid)
        grid.set_column_homogeneous(False)

        grid.set_margin_top(INNER_MARGIN)
        grid.set_margin_left(INNER_MARGIN)
        grid.set_margin_right(INNER_MARGIN)
        grid.set_margin_bottom(INNER_MARGIN)

        title = Gtk.Label()
        title.set_single_line_mode(True)
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))  # Set the foreground to white
        title.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))  # Set the background to transparent
        # NOTE: I believe the background is already transparent by default,
        #       but should never set one without the other or you might end up with white-on-white
        title.set_max_width_chars(-1)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.modify_font(bigger_font)
        title.set_text("Media title goes here but for now here's a long string for testing purposes")

        grid.attach(title, 0, 0, 2, 1)

        self.set_title = title.set_text

        status = Gtk.Label()
        status.set_single_line_mode(True)
        status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0, 0, 1))  # Set the foreground to white
        status.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))  # Set the background to transparent
        status.set_max_width_chars(-1)
        status.set_ellipsize(Pango.EllipsizeMode.END)
        status.modify_font(big_font)

        grid.attach(status, 0, 1, 1, 1)

        self.set_status = status.set_text

        # FIXME: Status & time should not be taking up half the width each, time is much smaller.
        #        Can I make status resize to fill and keep time as small as possible?
        #
        #        Might be able to do this by messing with max_width_chars, but there seems to be some minimum there as well.

        time_wid = Gtk.Label()
        time_wid.set_single_line_mode(True)
        time_wid.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 1, 0, 1))  # Set the foreground to white
        time_wid.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))  # Set the background to transparent
        time_wid.set_max_width_chars(8)  # FIXME: Magic number, if format changes based on locale, this could be completely wrong
        time_wid.set_ellipsize(Pango.EllipsizeMode.END)
        time_wid.modify_font(big_font)
        time_wid.set_halign(Gtk.Align.END)
        time_wid.set_justify(Gtk.Justification.RIGHT)
        time_wid.set_text(time.strftime('%X'))  # FIXME: Confirm that '%X' really does change with locale

        grid.attach_next_to(time_wid, status, Gtk.PositionType.RIGHT, 1, 1)

        self.set_time = time_wid.set_text  # FIXME: Make a generic "update" function, trigger that whenever the time changes

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show_all()
            GObject.timeout_add_seconds(3, self.hide)  # FIXME: Increase from 3s, only that low for testing

if __name__ == '__main__':
    win = Gtk.Window()
    win.connect("delete-event", Gtk.main_quit)
    osd = OSD()
    win.add(osd)
    textview = Gtk.TextView()
    ##textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    textbuffer = textview.get_buffer()
    textbuffer.set_text("Test string", -1)
    textview.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))  # Set the background to transparent
    textview.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))  # Set the foreground to white
    osd.add(textview)

    win.show_all()
    Gtk.main()
