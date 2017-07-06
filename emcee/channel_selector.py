from gi.repository import Gtk, GObject, Gdk
import emcee.vfs

# Note, BUTTON_SIZE should be slightly larger than the icon images themselves.
# I'm not really sure how much larger as I never bothered to look for the numbers,
# but the Button has it's own border that it puts around the icons that needs to be accounted for.
BUTTON_SIZE = (150, 150)  # FIXME: This is based on the current size of the channel gifs

# FIXME: Move this stylesheet out into a CSS file and import that as a theme in the application
style_provider = Gtk.CssProvider()
css = b"""
GtkWindow {
   background-color: darkblue;
}
GtkButton {
   border-radius: 15px;
}
/* This is when the  mouse is hovering over the button
 * .button:hover {
 *
 * }
 */
/* This is when the button is clicked while the mouse is hovering over it
 * .button:hover:active {
 *
 * }
 */
.button:focus {
   /* Background colour can not be set on a GtkButton without clearing the background image */
   background-image: none;
   background-color: yellow;
}
"""
style_provider.load_from_data(css)
Gtk.StyleContext.add_provider_for_screen(
    Gdk.Screen.get_default(),
    style_provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)


class ImageOrLabelButton(Gtk.Button):
    def __init__(self, label_str, image_path=None):
        super().__init__()
        if image_path:
            self.set_image(Gtk.Image.new_from_file(image_path))
        else:
            self.set_label(label_str)
        self.set_size_request(*BUTTON_SIZE)


class StationColumn(Gtk.Stack):
    # Can I use Gtk.EventBox to get focus-in and focus-out events?
    __gsignals__ = {
        'select-station': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, station):
        self.station = station

        super().__init__()

        # The stack that displays when not selected
        station_box = Gtk.VBox()
        self.add_named(station_box, "unselected")
        # Empty widget of the same size as the button itself,
        # this allows the selected station to have an extra button above the selected one.
        spacer = Gtk.DrawingArea()
        spacer.set_size_request(*BUTTON_SIZE)
        station_box.pack_start(spacer, expand=False, fill=False, padding=0)
        # The button for selecting the station itself
        station_btn = ImageOrLabelButton(station.title, station.icon)
        station_btn.connect('clicked', self.select_station)
        station_box.pack_start(station_btn, expand=False, fill=False, padding=0)

        # FIXME: Remove the upper/lower bounds on this scroller, set the step & page size to match the BUTTON_SIZE.
        #        Somehow process the scrolling using arrow keys.
        #        Note sure whether I should bind the arrows to scrolling then do things when scrolling happens,
        #        or steal the arrows and do the scrolling myself.
        scroller = Gtk.ScrolledWindow(
            # Only scroll vertically
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        # FIXME: This is a workaround for PolicyType.EXTERNAL not coming in until 3.16
        #        https://lazka.github.io/pgi-docs/Gtk-3.0/enums.html#Gtk.PolicyType.AUTOMATIC
        scroller.get_vscrollbar().set_visible(False)
        self.add_named(scroller, "selected")
#        station_btn.set_can_focus(False)

        channels_box = Gtk.VBox()
        scroller.add(channels_box)
        for channel in station.channels:
            channel_btn = ImageOrLabelButton(channel.title, channel.icon)
            channel_btn.connect('clicked', self.select_channel, channel)
            channels_box.pack_start(channel_btn, expand=False, fill=False, padding=0)

        # This spacer keeps all the buttons from growing larger than BUTTON_SIZE when the window grows.
        spacer = Gtk.DrawingArea()
        channels_box.pack_start(spacer, expand=True, fill=True, padding=0)

    def select_station(self, _):
        print('Selected', self.station.title),
        self.emit('select-station')

    def select_channel(self, _, channel):
        print('Play', channel.title, channel.uri),


class StationSelector(Gtk.ScrolledWindow):
    # The UI of this channel selector is a XMB (https://en.wikipedia.org/wiki/XrossMediaBar) style UI.
    # With stations being across the horizontal bar, and channels within those stations on the vertical bars
    def __init__(self):
        # Create the horizontal scroll window
        super().__init__(
            # Only scroll horizontally, the StationColumn has it's own vertical scroller
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        # FIXME: This is a workaround for PolicyType.EXTERNAL not coming in until 3.16
        #        https://lazka.github.io/pgi-docs/Gtk-3.0/enums.html#Gtk.PolicyType.AUTOMATIC
        self.get_hscrollbar().set_visible(False)

        # Despite being a bunch of VBoxes inside a HBox, Grid will not work in this case.
        # This is because the size of the 2nd column is intended to simply take up all the window space it can,
        # this can't be done with the Grid widget
        box = Gtk.HBox()
        self.add(box)

        vfs = emcee.vfs.VirtualFilesystem()
        self.columns = []
        for station in vfs.list_stations():
            c = StationColumn(station)
            c.connect('select-station', self.change_station)

            self.columns.append(c)
            box.pack_start(c, expand=False, fill=False, padding=0)

    def change_station(self, station_widget):
        for c in self.columns:
            if c != station_widget:
                c.set_visible_child_name("unselected")
            else:
                c.set_visible_child_name("selected")


if __name__ == '__main__':
    window = Gtk.Window(title='Emcee')
    window.connect("destroy", Gtk.main_quit)  # Quit & cleanup when closed
    ss = StationSelector()
    window.add(ss)
    window.set_size_request(BUTTON_SIZE[0] * 3, BUTTON_SIZE[1] * 3)
    window.show_all()

    Gtk.main()
