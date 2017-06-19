#!/usr/bin/python3

import time
from gi.repository import Gtk, Gdk, Pango, GObject

INNER_MARGIN = 5
OUTER_MARGIN = 10

## STOP! You can not make the overlay partially transparent, give up trying!
## FIXME: Either make the OSD variable size based on the window size, or set the minimum app window size to the size of the OSD.


class OSD(Gtk.VBox):
    def __init__(self):
        super(OSD, self).__init__()
        # Position self in top-right
        self.set_halign(Gtk.Align.END)
        self.set_valign(Gtk.Align.START)
        # But not the very far-right
        self.set_margin_top(OUTER_MARGIN)
        self.set_margin_right(OUTER_MARGIN)
        self.set_name("osd")  # Only used for CSS styling

        # FIXME: Move this stylesheet out into a CSS file and import that as a theme in the application
        style_provider = Gtk.CssProvider()
        css = b"""
            #osd {
                /* FIXME: Make the border act as padding, or add padding */

                border-color: white;
                border-style: solid;
                border-width: 2px;
                border-radius: 10px;
                box-shadow: 0 0 15px #333 inset;

                background-color: grey;
                color: white;
            }
            /* FIXME: Is there a "big" font option? Is it big enough for a 10-foot UI? */
            #osd #title {
                font-size: 30px
            }
            #osd #status, #osd #clock {
                font-size: 25px
            }

            /* FIXME: Only here for testing, remove them */
            #osd #clock {
                color: red;
            }
            #osd #status {
                color: blue;
            }
        """
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Title of the currently playing media
        title = Gtk.Label()
        title.set_name("title")
        title.set_single_line_mode(True)
        # NOTE: I believe the background is already transparent by default,
        #       but should never set one without the other or you might end up with white-on-white
        title.set_max_width_chars(25)
        title.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        title.set_halign(Gtk.Align.START)
        title.set_justify(Gtk.Justification.LEFT)
        title.set_text("Media title goes here but for now here's a long string for testing purposes")

        self.pack_start(title, expand=True, fill=True, padding=0)
        self.set_title = title.set_text

        status_line = Gtk.HBox()
        self.pack_start(status_line, expand=False, fill=False, padding=0)

        # Current status, this could be "volume: 10%", if nothing is happening it could be something useful to go with the title.
        status = Gtk.Label()  # FIXME: Should this perhaps be a Gtk.StatusBar?
        status.set_name("status")
        status.set_single_line_mode(True)
        status.set_max_width_chars(-1)
        status.set_ellipsize(Pango.EllipsizeMode.END)
        status.set_halign(Gtk.Align.START)
        status.set_justify(Gtk.Justification.LEFT)
        status.set_text("Status")
# FIXME: OSD starts sliding off to the right if status string is longer than the width of the window.
#        status.set_text("Super long stirng to see what happens when I put a super long string here.")

        status_line.pack_start(status, expand=True, fill=True, padding=0)
        self.set_status = status.set_text

        # Current time.
        clock = Gtk.Label()
        clock.set_name("clock")
        clock.set_single_line_mode(True)
        clock.set_max_width_chars(8)
        clock.set_ellipsize(Pango.EllipsizeMode.END)
        clock.set_halign(Gtk.Align.END)
        clock.set_justify(Gtk.Justification.RIGHT)
        clock.set_text(time.strftime('%X'))  # FIXME: Confirm that '%X' really does change with locale

        status_line.pack_start(clock, expand=False, fill=False, padding=0)
        self.set_time = clock.set_text  # FIXME: Make a generic "update" function, trigger that whenever the time changes

        # Current position, if we don't know the end time maybe this should be hidden.
        # FIXME: Was never able to make the progressbar thicker than 6px, that's not suitable for a 10-foot UI
        #        We decided to turn off the ProgressBar entirely because it's not necessary for streaming media, can be fixed later
#        position = Gtk.ProgressBar()
#        position.set_fraction(0.5)
#        position.set_vexpand(True)
#        position.set_valign(Gtk.Align.FILL)
#        self.pack_start(position, expand=True, fill=True, padding=0)
#
#        self.set_position = position.set_fraction

    def toggle(self):
        self.set_time(time.strftime('%X'))  # FIXME: Make a generic "update" function, trigger that whenever the time changes
        if self.get_visible():
            self.hide()
            # FIXME: Remove timeout added when showing the OSD
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
