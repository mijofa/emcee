from gi.repository import Gtk, GObject, Gdk, Pango
import emcee.vfs

# Note, BUTTON_SIZE should be slightly larger than the icon images themselves.
# I'm not really sure how much larger as I never bothered to look for the numbers,
# but the Button has it's own border that it puts around the icons that needs to be accounted for.
BUTTON_SIZE = (150, 150)  # FIXME: This is based on the current size of the channel gifs

# FIXME: Move this stylesheet out into a CSS file and import that as a theme in the application
style_provider = Gtk.CssProvider()
css = b"""
GtkLabel#station-name {
   font-size: 30px;
}
GtkWindow {
   background-color: #729fcf;
}
GtkButton {
   font-size: 50px;
   border-radius: 99999px;  /* FIXME: This is a stupid number to put here */
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


def scroller_resize(scroller, rect, orientation):
    # Double the upper and lower bounds of the scrolling window, otherwise we can't scroll any of the buttons off the screen.

    if orientation == 'horizontal':
        adj = scroller.get_hadjustment()
        rect_size = rect.width
        object_size = BUTTON_SIZE[0]
    elif orientation == 'vertical':
        adj = scroller.get_vadjustment()
        rect_size = rect.height
        object_size = BUTTON_SIZE[1]
    else:
        raise ValueError("Orientation must be 'horizontal' or 'vertical'")

    num_objects = len(scroller.get_child().get_child().get_children())
    size = (num_objects * object_size) + (rect_size - (object_size * 2))
    adj.set_lower(-object_size)
    adj.set_upper(size)


class ImageOrLabelButton(Gtk.Button):
    def __init__(self, title, icon, click, args=()):
        super().__init__()
        if icon:
            self.set_image(Gtk.Image.new_from_file(icon))
            self.set_always_show_image(True)
        else:
            self.set_label('?')  # FIXME: Style this better.
            ## Wanted to make the label display the channel/station title when an icon was unavailable, this didn't go so well.
            ## Since I don't seem to be able to set a max-size in pixels for the label only in characters of text,
            ## it kept trying to grow out of the bounds of the icon size.
            #label = self.get_children()[0]
            #label.set_size_request(*BUTTON_SIZE)
            #label.set_line_wrap(True)
            #label.set_ellipsize(Pango.EllipsizeMode.END)
            #label.set_lines(3)
        self.set_size_request(*BUTTON_SIZE)
        self.set_can_focus(False)

        self.connect('clicked', click, *args)


class ChannelPicker(Gtk.Stack):
    # Can I use Gtk.EventBox to get focus-in and focus-out events?
    def __init__(self, stations):
        super().__init__()

#        # The stack that displays when not selected
#        station_box = Gtk.VBox()
#        self.add_named(station_box, "unselected")
#        # Empty widget of the same size as the button itself,
#        # this allows the selected station to have an extra button above the selected one.
#        spacer = Gtk.DrawingArea()
#        spacer.set_size_request(*BUTTON_SIZE)
#        station_box.pack_start(spacer, expand=False, fill=False, padding=0)
#        # The button for selecting the station itself
#        station_box.pack_start(
#            ImageOrLabelButton(title=station.title, icon=station.icon, click=self.select_station),
#            expand=False,
#            fill=False,
#            padding=0
#        )

        for station in stations:
            # FIXME: Remove the upper/lower bounds on this scroller, set the step & page size to match the BUTTON_SIZE.
            #        Somehow process the scrolling using arrow keys.
            #        Note sure whether I should bind the arrows to scrolling then do things when scrolling happens,
            #        or steal the arrows and do the scrolling myself.
            scroller = Gtk.ScrolledWindow(
                # Only scroll vertically
                hscrollbar_policy=Gtk.PolicyType.NEVER,
                vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            )
            scroller.connect('size-allocate', scroller_resize, 'vertical')
            # FIXME: This is a workaround for PolicyType.EXTERNAL not coming in until 3.16
            #        https://lazka.github.io/pgi-docs/Gtk-3.0/enums.html#Gtk.PolicyType.AUTOMATIC
            scroller.get_vscrollbar().set_visible(False)
            self.add_named(scroller, station.title)

            channels_box = Gtk.VBox()
            scroller.add(channels_box)
            for channel in station.channels:
                channels_box.pack_start(
                    ImageOrLabelButton(title=channel.title, icon=channel.icon, click=self.select_channel, args=(channel,)),
                    expand=False,
                    fill=False,
                    padding=0
                )

#    def select_station(self, _):
#        # _ is the widget that triggered the event, I don't actually care about it
#        print('Selected', self.station.title),
#        self.emit('select-station')

    def next(self, *args):
        print(self, 'next')
        adj = self.get_visible_child().get_vadjustment()
        adj.set_value(adj.get_value() + BUTTON_SIZE[1])
        print(adj.get_value())

    def prev(self, *args):
        print(self, 'prev')
        adj = self.get_visible_child().get_vadjustment()
        adj.set_value(adj.get_value() - BUTTON_SIZE[1])
        print(adj.get_value())

    def change_station(self, widget, station):
        print(self.set_visible_child_name(station))
        print(widget, station)

    def select_channel(self, _, channel):
        # _ is the widget that triggered the event, I don't actually care about it
        print('Play', channel.title, channel.uri),


class StationPicker(Gtk.ScrolledWindow):
    __gsignals__ = {
        'select-station': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str,)),
    }

    def __init__(self, stations):
        # Create the horizontal scroll window
        super().__init__(
            # Only scroll horizontally, the StationColumn has it's own vertical scroller
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        self.connect('size-allocate', scroller_resize, 'horizontal')
        # FIXME: This is a workaround for PolicyType.EXTERNAL not coming in until 3.16
        #        https://lazka.github.io/pgi-docs/Gtk-3.0/enums.html#Gtk.PolicyType.AUTOMATIC
        self.get_hscrollbar().set_visible(False)

        # Despite being a bunch of VBoxes inside a HBox, Grid will not work in this case.
        # This is because the size of the 2nd column is intended to simply take up all the window space it can,
        # this can't be done with the Grid widget
        box = Gtk.HBox()
        self.add(box)

        self.stations = stations
        for station in self.stations:
            b = ImageOrLabelButton(title=station.title, icon=station.icon, click=lambda _: print(station.title))
            b.set_can_focus(False)
            box.pack_start(b, expand=False, fill=False, padding=0)

    def next(self, *args):
        print(self, 'next')
        adj = self.get_hadjustment()
        adj.set_value(adj.get_value() + BUTTON_SIZE[0])
        cur_pos = int((adj.get_value() + BUTTON_SIZE[0]) / BUTTON_SIZE[0])
        print(cur_pos)
        self.emit('select-station', self.stations[cur_pos].title)

    def prev(self, *args):
        print(self, 'prev')
        adj = self.get_hadjustment()
        adj.set_value(adj.get_value() - BUTTON_SIZE[0])
        cur_pos = int((adj.get_value() + BUTTON_SIZE[0]) / BUTTON_SIZE[0])
        print(cur_pos)
        self.emit('select-station', self.stations[cur_pos].title)


class StreamSelector(Gtk.Overlay):
    def __init__(self):
        super().__init__()
        vfs = emcee.vfs.VirtualFilesystem()
        stations = vfs.list_stations()

        station_box = Gtk.VBox()
        self.add(station_box)
        station_spacer = Gtk.DrawingArea()
        station_spacer.set_size_request(*BUTTON_SIZE)
        station_box.pack_start(station_spacer, expand=False, fill=False, padding=0)
        self.station_picker = StationPicker(stations)
        station_box.pack_start(self.station_picker, expand=False, fill=False, padding=0)
        station_box.pack_start(Gtk.DrawingArea(), expand=True, fill=True, padding=0)

        channel_box = Gtk.HBox()
        self.add_overlay(channel_box)
        channel_spacer = Gtk.DrawingArea()
        channel_spacer.set_size_request(*BUTTON_SIZE)
        channel_box.pack_start(channel_spacer, expand=False, fill=False, padding=0)
        self.channel_picker = ChannelPicker(stations)
        channel_box.pack_start(self.channel_picker, expand=False, fill=False, padding=0)
        channel_box.pack_start(Gtk.DrawingArea(), expand=True, fill=True, padding=0)

        self.station_label = Gtk.Label(
            name="station-name",
            halign=Gtk.Align.START,
            valign=Gtk.Align.START,
            justify=Gtk.Justification.LEFT,
        )
        self.station_label.set_line_wrap(True)
        self.station_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.station_label.set_lines(2)
        self.station_label.set_text("foobar")
        channel_box.pack_start(self.station_label, expand=True, fill=True, padding=2)

        self.station_picker.connect('select-station', self.change_station)

        self.connect('key-press-event', self.on_key_press)

    def change_station(self, widget, station_name):
        self.station_label.set_text(station_name)
        self.channel_picker.change_station(widget, station_name)

    def on_key_press(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        print('press', keyname)
        if keyname == 'Left':
            self.station_picker.prev()
        elif keyname == 'Right':
            self.station_picker.next()
        elif keyname == 'Up':
            self.channel_picker.prev()
        elif keyname == 'Down':
            self.channel_picker.next()


if __name__ == '__main__':
    window = Gtk.Window(title='Emcee')
    window.connect("destroy", Gtk.main_quit)  # Quit & cleanup when closed
    ss = StreamSelector()
    window.add(ss)
    window.set_size_request(BUTTON_SIZE[0] * 4.5, BUTTON_SIZE[1] * 3.5)
    window.show_all()

    Gtk.main()
