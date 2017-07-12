from gi.repository import Gtk, GObject, Gdk, Pango
import emcee.vfs

# Note, BUTTON_SIZE should be slightly larger than the icon images themselves.
# I'm not really sure how much larger as I never bothered to look for the numbers,
# but the Button has it's own border that it puts around the icons that needs to be accounted for.
BUTTON_WIDTH = 150  # FIXME: This is based on the current size of the channel gifs
BUTTON_HEIGHT = 150  # FIXME: This is based on the current size of the channel gifs
OFFSET_UPPER = BUTTON_HEIGHT * 0.75
OFFSET_LEFT = BUTTON_WIDTH * 0.5

EPG_TEMPLATE = "{channel_title}\nNOW:\n  {now_title}\nNEXT ({next_time}):\n  {next_title}"

# FIXME: Move this stylesheet out into a CSS file and import that as a theme in the application
style_provider = Gtk.CssProvider()
css = b"""
GtkLabel#station-name, GtkLabel#epg {
   border-style: solid;
   border-color: green;
   border-width: 20px;
   font-size: 20px;
   background-color: red;
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


class ImageOrLabelButton(Gtk.Button):
    def __init__(self, title, icon, click=None, args=()):
        super().__init__()
        if icon:
            self.set_image(Gtk.Image.new_from_file(icon))
            self.set_always_show_image(True)
        else:
            self.set_label('?')  # FIXME: Style this better.
            ## Wanted to make the label display the channel/station title when an icon was unavailable, this didn't go so well.
            ## Since I don't seem to be able to set a max-size in pixels for the label, only in characters of text,
            ## it kept trying to grow out of the bounds of the icon size.
            #label = self.get_children()[0]
            #label.set_size_request(*BUTTON_SIZE)
            #label.set_line_wrap(True)
            #label.set_ellipsize(Pango.EllipsizeMode.END)
            #label.set_lines(3)
        self.set_size_request(BUTTON_WIDTH, BUTTON_HEIGHT)

        # I'm using the focus attribute to style the button nicely, however I want to control what keys change the focus.
        # Easiest way to do this was to make it disable taking focus, then temporarily enable it as I grab focus.
        ## FIXME: This is ugly, maybe stop using focus and make my own style attribute
        self.set_can_focus(False)
        self.connect('focus-out-event', lambda self, _: self.set_can_focus(False))

        if click:
            self.connect('clicked', click, *args)

    def grab_focus(self):
        self.set_can_focus(True)
        super().grab_focus()


class ChannelPicker(Gtk.Stack):
    __gsignals__ = {
        'selection-change': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str,)),
    }

    def __init__(self, stations):
        super().__init__()

        for station in stations:
            layout = Gtk.Layout()
            self.add_named(layout, station.title)
            layout.channels = station.channels

            # It's easier to move one box around than it is to have move around all the buttons themselves.
            layout.box = Gtk.HBox()
            layout.put(layout.box, 0, 0)

            for channel in layout.channels:
                button = ImageOrLabelButton(title=channel.title, icon=channel.icon, click=self.select, args=(channel,))
                layout.box.pack_start(button, expand=False, fill=False, padding=0)

            layout.adjustment = Gtk.Adjustment(value=0,
                                               lower=0,
                                               upper=len(layout.channels) - 1,
                                               step_increment=1)
            layout.adjustment.connect('value-changed', self._value_changed, layout)
            self._value_changed(layout.adjustment, layout)

    def _value_changed(self, adjustment, layout):
        # List indices must be an int, however the adjustment property values are floats.
        # Since I'm explicitly setting the adjustment properties, I know they are going to be rounded numbers
        ind = int(adjustment.get_value())

        layout.move(layout.box,
                    OFFSET_LEFT + (BUTTON_WIDTH * -ind),
                    OFFSET_UPPER)

        layout.box.get_children()[ind].grab_focus()
        layout.selected = layout.channels[ind]
        self.emit('selection-change', layout.selected.title)

    def next(self, *args):
        adjustment = self.get_visible_child().adjustment
        adjustment.set_value(adjustment.get_value() + 1)

    def prev(self, *args):
        adjustment = self.get_visible_child().adjustment
        adjustment.set_value(adjustment.get_value() - 1)

    def change_station(self, station):
        self.set_visible_child_name(station)
        # Trigger the _self.value_changed function to make sure current channel selections get updated
        # I could call the functon directly, but I felt it was "more right" to do it by triggering this signal
        self.get_visible_child().adjustment.emit('value-changed')

    def select(self, button=None, channel=None):
        assert (not button and not channel) or (button and channel)
        if not button and not channel:
            channel = self.get_visible_child().selected
        print('Play', channel.title, channel.uri),


class StationPicker(Gtk.Layout):
    __gsignals__ = {
        'select': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str,)),
    }

    def __init__(self, stations):
        # Create the horizontal scroll window
        super().__init__()
        self.stations = stations

        # It's easier to move one box around than it is to have move around all the buttons themselves.
        self.box = Gtk.VBox()
        self.put(self.box, 0, 0)

        for station in self.stations:
            button = ImageOrLabelButton(title=station.title, icon=station.icon)
            button.set_can_focus(False)
            self.box.pack_start(button, expand=False, fill=False, padding=0)

        self.adjustment = Gtk.Adjustment(value=0,
                                         lower=0,
                                         upper=len(self.stations) - 1,
                                         step_increment=1)
        self.adjustment.connect('value-changed', self._value_changed)
        self._value_changed(self.adjustment)

    def _value_changed(self, adjustment):
        # List indices must be an int, however the adjustment property values are floats.
        # Since I'm explicitly setting the adjustment properties, I know they are going to be rounded numbers
        ind = int(adjustment.get_value())

        self.move(self.box,
                  OFFSET_LEFT,
                  OFFSET_UPPER + (BUTTON_HEIGHT * -ind))

        station = self.stations[ind]
        self.emit('select', station.title)

    def next(self, *args):
        self.adjustment.set_value(self.adjustment.get_value() + 1)

    def prev(self, *args):
        self.adjustment.set_value(self.adjustment.get_value() - 1)


class StreamSelector(Gtk.Overlay):
    def __init__(self):
        super().__init__()
        vfs = emcee.vfs.VirtualFilesystem()
        stations = vfs.list_stations()

        station_box = Gtk.HBox()
        self.add(station_box)

        ## Station scroller
        self.station_picker = StationPicker(stations)
        station_box.pack_start(self.station_picker, expand=False, fill=False, padding=0)
        # Without setting a size_request, the label will expand and fill over the picker
        self.station_picker.set_size_request(BUTTON_WIDTH + OFFSET_LEFT, -1)
        ## Station label to sit above the channel scroller
        self.station_label = Gtk.Label(
            name="station-name",
            halign=Gtk.Align.START,
            valign=Gtk.Align.START,
            justify=Gtk.Justification.LEFT,
        )
        self.station_label.set_line_wrap(True)
        self.station_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.station_label.set_lines(3)
        self.station_label.set_text("Station title")
        station_box.pack_start(self.station_label, expand=True, fill=True, padding=0)

        ## Functions for controlling the station menu
        self.prev_station = self.station_picker.prev
        self.next_station = self.station_picker.next

        ## Channel scroller
        channel_box = Gtk.VBox()
        self.add_overlay(channel_box)
        self.channel_picker = ChannelPicker(stations)
        channel_box.pack_start(self.channel_picker, expand=False, fill=False, padding=0)
        # Without setting a size_request, the label will expand and fill over the picker
        self.channel_picker.set_size_request(-1, BUTTON_HEIGHT + OFFSET_UPPER)

        ## Functions for controlling the channel menu
        self.prev_channel = self.channel_picker.prev
        self.next_channel = self.channel_picker.next
        self.select_channel = self.channel_picker.select

        ## EPG info to go below the channel scroller
        epg_box = Gtk.HBox()
        channel_box.pack_start(epg_box, expand=False, fill=False, padding=0)
        # Spacer to keep it to the right of the station scroller.
        epg_spacer = Gtk.DrawingArea()
        epg_spacer.set_size_request(BUTTON_WIDTH + OFFSET_LEFT, BUTTON_HEIGHT)
        epg_box.pack_start(epg_spacer, expand=False, fill=False, padding=0)
        self.epg_label = Gtk.Label(
            name="epg",
            halign=Gtk.Align.START,
            valign=Gtk.Align.END,
            justify=Gtk.Justification.LEFT,
        )
        self.epg_label.set_line_wrap(True)  # Has no effect with ellipsize set unless set_lines is called
        self.epg_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.epg_label.set_lines(2)  # This is how many lines it's allowed to *wrap*, it does not affect how many \n I can use
        self.epg_label.set_text(EPG_TEMPLATE)  # FIXME: Should this be all one string?
        epg_box.pack_start(self.epg_label, expand=True, fill=True, padding=0)

        self.channel_picker.connect('selection-change', self.on_channel_change)
        self.station_picker.connect('select', self.on_station_change)

    def on_channel_change(self, widget, channel_name):
        # FIXME: Get the NOW/NEXT info from EPG via the VFS
        self.epg_label.set_text(EPG_TEMPLATE.format(channel_title=channel_name, now_title="N/A", next_time="??:??", next_title="N/A 2: The revenge of the the unknown"))

    def on_station_change(self, widget, station_name):
        self.station_label.set_text(station_name)
        self.channel_picker.change_station(station_name)


if __name__ == '__main__':
    window = Gtk.Window(title='Emcee')
    window.connect("destroy", Gtk.main_quit)  # Quit & cleanup when closed
    ss = StreamSelector()
    window.add(ss)

    def on_key_press(widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            Gtk.main_quit()
        elif keyname == 'Up':
            ss.prev_station()
        elif keyname == 'Down':
            ss.next_station()
        elif keyname == 'Left':
            ss.prev_channel()
        elif keyname == 'Right':
            ss.next_channel()
        elif keyname in ('space', 'Return'):
            ss.select_channel()
    window.connect('key-press-event', on_key_press)

    min_height = OFFSET_UPPER + (BUTTON_WIDTH * 2)
    min_width = OFFSET_LEFT + (BUTTON_HEIGHT * 3)
    window.set_size_request(min_width, min_height)
    window.set_default_size(BUTTON_WIDTH * 4.5, BUTTON_HEIGHT * 3.5)
    window.show_all()

    Gtk.main()
