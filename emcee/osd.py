#!/usr/bin/python3

import time
import logging
logger = logging.getLogger(__name__)
from gi.repository import Gtk, Gdk, Pango, GObject, GLib

TIME_FORMAT = '%X'  # FIXME: Confirm that '%X' really does change with locale

OUTER_MARGIN = 10

## There were many attempts to make the OSD partially transparent over the top of the video display.
## While it is possible to make an overlay transparent on whatever is underneath it, this can not work with the VLC widget.
## I believe this is because of VLC & GTK not interacting well together.

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
        font-size: 2em;
    }
    #osd #status, #osd #clock {
        font-size: 2em;
    }

    #osd #clock {
        /* I want to keep the clock from detracting focus away from the other (more important) text */
        opacity: 0.65;  /* FIXME: Magic number, fairly arbitrary, it looks nice. */
    }
"""
style_provider.load_from_data(css)
Gtk.StyleContext.add_provider_for_screen(
    Gdk.Screen.get_default(),
    style_provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)


class OSD(Gtk.Frame):
    _hide_timer = None

    def __init__(self):
        logger.debug('Setting up OSD')
        super().__init__(
            margin=OUTER_MARGIN,  # Keep it slightly away from the edge
            name="osd",  # Used for CSS styling
            border_width=2,
            # Anchor it to the top-left
            # FIXME: Doesn't work in top-right. If the label strings get long the entire OSD moves away from the right edge.
            #        Like it's allocating space, but then not using it because the ellipsizing is doing it's job
            halign=Gtk.Align.START,
            valign=Gtk.Align.START,
        )

        # Title of the currently playing media
        title = Gtk.Label(
            name="title",
            single_line_mode=True,
            max_width_chars=-1,
            ellipsize=Pango.EllipsizeMode.MIDDLE,
            halign=Gtk.Align.START,
        )
        title.set_size_request(300, -1)  # This defines the minimum length of the OSD.

        # Current status, this could be "volume: 10%", if nothing is happening it could be something useful to go with the title.
        #
        # NOTE: I wanted to call this "subtitle" as it's probably more often going to be used for station name or similar,
        #       being a secondary title. Decided against that to avoid confusion with the video subtitles
        self._status = Gtk.Statusbar(  # FIXME: Should this perhaps be a Gtk.StatusBar?
            name="status",
            halign=Gtk.Align.START,
        )

        # Current time.
        clock = Gtk.Label(
            name="clock",
            single_line_mode=True,
            # Not setting max_width_chars or ellipsize here as I want the clock to take up all the space it needs
            halign=Gtk.Align.END,
            justify=Gtk.Justification.RIGHT,
        )

        # Convenience functions for updating the labels
        self.set_title = title.set_text
        self._set_time = clock.set_text  # Should never actually be called externally
        # Set up GLib to update the clock whenever it has a free moment
        GObject.idle_add(self._update_time, priority=GLib.PRIORITY_LOW)

        vbox = Gtk.VBox()
        self.add(vbox)
        vbox.pack_start(title, expand=True, fill=True, padding=0)
        status_line = Gtk.HBox()
        status_line.pack_start(self._status, expand=True, fill=True, padding=0)
        status_line.pack_start(clock, expand=False, fill=False, padding=0)
        vbox.pack_start(status_line, expand=True, fill=True, padding=0)

        vbox.show_all()  # This shows all widgets inside the Frame, allowing me to use show/hide to toggle the frame itself

        # Current position, if we don't know the end time maybe this should be hidden.
        # FIXME: Was never able to make the progressbar thicker than 6px, that's not suitable for a 10-foot UI
        #        We decided to turn off the ProgressBar entirely because it's not necessary for streaming media, can be fixed later
        def f():
            pass

        self.set_position = f
        self.vbox = vbox  # Only here for the temporary set_has_position function

    def set_has_position(self, has_position):
        logger.debug('Adding progress bar to OSD')
        # FIXME: This is not suitable for the end result, I've only put this here for use at home when not 10-feet away.
        assert type(has_position) == bool
        if not has_position:
            raise NotImplementedError("Haven't actually implemented removing the progress bar")
        position = Gtk.ProgressBar(
            vexpand=True,
            valign=Gtk.Align.FILL,
        )
        self.vbox.pack_end(position, expand=True, fill=True, padding=0)

        self.set_position = position.set_fraction

    def _update_time(self):
        # This function runs *very* often uncommenting this could fill the debug screen in less than a second
        #logger.debug('Updating clock')
        self._set_time(time.strftime(TIME_FORMAT))
        return True  # Gotta return True to tell GObject to keep the timer running and keep running this every second

    ## OSD visibility functions
    def show(self, timeout=5):  # FIXME: What should the timeout be? UPMC defaulted to 3s
        logger.debug('Showing OSD')

        # Remove any pre-existing hide timer before displaying the OSD.
        # This ensures that no previous timer hides the OSD before the new timeout triggers
        if self._hide_timer is not None:  # It's possible (although unlikely) that self._hide_timer will be 0
            GObject.source_remove(self._hide_timer)
            self._hide_timer = None

        super().show()
        if timeout:
            self._hide_timer = GObject.timeout_add_seconds(timeout, self.hide)

    def hide(self):
        logger.debug('Hiding OSD')

        return super().hide()

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show()

    ## Status line updating
    def set_default_status(self, default_status=''):
        logger.debug('Updating default status "%s"', default_status)
        self._status.remove_all(self._status.get_context_id('default'))
        self._status.push(self._status.get_context_id('default'), default_status)

    def push_status(self, status_string, context_string='', timeout=3):
        # Thin wrapper around _status.push that gives every message a timeout before automatically removing it from the stack
        logger.debug('Adding status string "%s"', status_string)
        # FIXME: Do something with the context string?
        #        Perhaps prioritise certain contexts, and choose timeouts accordingly.
        context_id = self._status.get_context_id(context_string)
        message_id = self._status.push(context_id, status_string)
        if timeout != 0:
            # FIXME: Should this trigger self.show()?
            # FIXME: Should the status removal be moved to self.hide()?
            GObject.timeout_add_seconds(timeout, lambda: self._status.remove(context_id, message_id))

        # FIXME: Remove *all* status messages when hiding?
        self.show(timeout=timeout)
        return message_id


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG)

    win = Gtk.Window()
    win.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1))  # Set the background to black
    win.connect("delete-event", Gtk.main_quit)
    osd = OSD()
    osd.set_title(sys.argv[1])
    osd.set_default_status(sys.argv[2])
    print(osd.push_status('-1 Temp status', timeout=6))
    print(osd.push_status('0 Temp status', context_string='volume', timeout=4))
    print(osd.push_status('1 Temp status', context_string='subtitle', timeout=3))
    print(osd.push_status('-2 Temp status', timeout=2.5))
    print(osd.push_status('2 Temp status', context_string='volume', timeout=2))
    print(osd.push_status('3 Temp status', context_string='subtitle', timeout=1))
    win.add(osd)

    win.connect('key-press-event', lambda _, e: osd.show())

    win.show_all()
    Gtk.main()
