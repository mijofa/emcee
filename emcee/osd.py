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

        ## Fonts
        # I'm only using these so I can set the font size of the text
        bigger_font = Pango.FontDescription()
        bigger_font.set_size(30 * Pango.SCALE)  # FIXME: Magic number, it looks good and takes up just over a 3rd of the OSD height
        big_font = Pango.FontDescription()
        big_font.set_size(25 * Pango.SCALE)  # FIXME: Magic number, it looks good and takes up just under a 3rd of the OSD height

        # Add a background image to the OSD, grid looks ugly otherwise.
        bg = Gtk.Image.new_from_file('osd_bg.png')
        bg.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))  # Set the background to black
        self.add(bg)

        # Set up the grid we add the OSD objects to.
        grid = Gtk.Grid()
        grid.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
        self.add_overlay(grid)
        grid.set_column_homogeneous(False)
        # The background image has a border around the edge to look nicer, don't let the widgets go over the border
        grid.set_margin_top(INNER_MARGIN)
        grid.set_margin_left(INNER_MARGIN)
        grid.set_margin_right(INNER_MARGIN)
        grid.set_margin_bottom(INNER_MARGIN)

        # Title of the currently playing media
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

        # Current status, this could be "volume: 10%", if nothing is happening it could be something useful to go with the title.
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

        # Current time.
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
#
#        style_provider = Gtk.CssProvider()
#        css = b"""
#        GtkProgressBar {
#            -GtkProgressBar-min-horizontal-bar-height: 40px;
#        }
#        """
#        style_provider.load_from_data(css)
#        Gtk.StyleContext.add_provider_for_screen(
#            Gdk.Screen.get_default(),
#            style_provider,
#            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
#        )

        # Current position, if we don't know the end time this should be hidden.
        position = Gtk.ProgressBar()
        position.set_fraction(0.5)
        position.set_size_request(0, 40)  # FIXME: This doesn't set the height of the bar, just moves it down a bit
        grid.attach(position, 0, 2, 2, 1)

        self.set_position = position.set_fraction

    def toggle(self):
        self.set_time(time.strftime('%X'))  # FIXME: Make a generic "update" function, trigger that whenever the time changes
        if self.get_visible():
            self.hide()
        else:
            self.show_all()
            GObject.timeout_add_seconds(3, self.hide)  # FIXME: Increase from 3s, only that low for testing

if __name__ == '__main__':
    win = Gtk.Window()
    win.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1))  # Set the background to black
    win.connect("delete-event", Gtk.main_quit)
    osd = OSD()
    win.add(osd)

    win.show_all()
    Gtk.main()
