#!/usr/bin/python3

import time
from gi.repository import Gtk, Gdk, Pango, GObject

TIME_FORMAT = '%X'  # FIXME: Confirm that '%X' really does change with locale

OUTER_MARGIN = 10

## STOP! You can not make the overlay partially transparent, give up trying!
## FIXME: Either make the OSD variable size based on the window size, or set the minimum app window size to the size of the OSD.

# FIXME: Move this stylesheet out into a CSS file and import that as a theme in the application
style_provider = Gtk.CssProvider()
css = b"""
    #osd {
        padding: 2px;
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


class OSD(Gtk.Frame):
    def __init__(self):
        super(OSD, self).__init__(
            margin=OUTER_MARGIN,  # Keep it slightly away from the edge
            name="osd",  # Used for CSS styling
            border_width=2,
            # Anchor it to the top-left
            # FIXME: Doesn't work in top-right. If the label strings get long the entire OSD moves away from the right edge.
            #        Like it's allocating space, but then not using it because the ellipsizing is doing it's job
            halign=Gtk.Align.START,
            valign=Gtk.Align.START,
        )

        box = Gtk.VBox()
        self.add(box)

        # Title of the currently playing media
        title = Gtk.Label()
        title.set_name("title")
        title.set_single_line_mode(True)
        title.set_max_width_chars(-1)
        title.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        title.set_halign(Gtk.Align.START)
        title.set_text("Media title goes here but for now here's a long string for testing purposes")

        box.pack_start(title, expand=True, fill=True, padding=0)
        self.set_title = title.set_text

        status_line = Gtk.HBox()
        box.pack_start(status_line, expand=True, fill=True, padding=0)

        # Current status, this could be "volume: 10%", if nothing is happening it could be something useful to go with the title.
        status = Gtk.Label()  # FIXME: Should this perhaps be a Gtk.StatusBar?
        status.set_name("status")
        status.set_single_line_mode(True)
        status.set_max_width_chars(-1)
        status.set_ellipsize(Pango.EllipsizeMode.END)
        status.set_halign(Gtk.Align.START)
        status.set_justify(Gtk.Justification.LEFT)
        status.set_text("Status line goes here, but I need a long string for testing so this should do just fine")

        status_line.pack_start(status, expand=True, fill=True, padding=0)
        self.set_status = status.set_text

        # Current time.
        clock = Gtk.Label()
        clock.set_name("clock")
        clock.set_single_line_mode(True)
        # Not setting max_width_chars or ellipsize here as I want the clock to take up all the space it needs
        clock.set_halign(Gtk.Align.END)
        clock.set_justify(Gtk.Justification.RIGHT)
        clock.set_text(time.strftime(TIME_FORMAT))

        status_line.pack_start(clock, expand=False, fill=False, padding=0)
        self.set_time = clock.set_text  # FIXME: Make a generic "update" function, trigger that whenever the time changes

        # Current position, if we don't know the end time maybe this should be hidden.
        # FIXME: Was never able to make the progressbar thicker than 6px, that's not suitable for a 10-foot UI
        #        We decided to turn off the ProgressBar entirely because it's not necessary for streaming media, can be fixed later
        def f():
            pass

        self.set_position = f
        self.box = box  # Only here for the temporary set_has_position function

    def set_has_position(self, has_position):
        # FIXME: This is not suitable for the end result, I've only put this here for use at home when not 10-feet away.
        assert type(has_position) == bool
        if not has_position:
            raise NotImplementedError("Haven't actually implemented removing the progress bar")
        position = Gtk.ProgressBar()
        position.set_vexpand(True)
        position.set_valign(Gtk.Align.FILL)
        self.box.pack_end(position, expand=True, fill=True, padding=0)

        self.set_position = position.set_fraction

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
