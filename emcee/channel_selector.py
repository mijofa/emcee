from gi.repository import Gtk, GObject, Gdk, Pango
import emcee.vfs

# Note, BUTTON_SIZE should be slightly larger than the icon images themselves.
# I'm not really sure how much larger as I never bothered to look for the numbers,
# but the Button has it's own border that it puts around the icons that needs to be accounted for.
BUTTON_WIDTH = 150  # FIXME: This is based on the current size of the channel gifs
BUTTON_HEIGHT = 150  # FIXME: This is based on the current size of the channel gifs
OFFSET_UPPER = BUTTON_HEIGHT * 0.75
OFFSET_LEFT = BUTTON_WIDTH * 0.75

EPG_TEMPLATE = "{channel_title}\nCurrently playing:\n  {now_title}\nNext ({next_time}):\n  {next_title}"

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
.button.inactive {
    /* I wanted to make inactive icons smaller, but can't change size of objects in the CSS */
}
GtkStack GtkLayout .button.active {
    /* GtkButton by default has a background-image.
     *  That must be removed before we can change the background-color
     */
    background-image: none;
    background-color: red;
}
.invisible {
    opacity: 0;
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
        self.set_can_focus(False)
        self.get_style_context().add_class('inactive')

        if click:
            self.connect('clicked', click, *args)


class Picker(Gtk.Layout):
    # Generic scroller for any number of itmes in a single row or column.
    __gsignals__ = {
        'focus-change': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self, orientation, items):
        assert orientation in ('horizontal', 'vertical')
        self.orientation = orientation
        self.items = items

        super().__init__()

        # It's easier to move one box around than it is to have move around all the buttons themselves.
        if self.orientation == 'vertical':
            self.box = Gtk.VBox()
        elif self.orientation == 'horizontal':
            self.box = Gtk.HBox()
        self.put(self.box, 0, 0)

        self.buttons = []
        for item in self.items:
            self.buttons.append(ImageOrLabelButton(title=item.title, icon=item.icon))
            self.box.pack_start(self.buttons[-1], expand=False, fill=False, padding=0)

        self.adjustment = Gtk.Adjustment(value=0,
                                         lower=0,
                                         upper=len(self.items) - 1,
                                         step_increment=1)
        self.adjustment.connect('value-changed', self._value_changed)
        self._value_changed(self.adjustment)

    def _value_changed(self, adjustment):
        # List indices must be an int, however the adjustment property values are floats.
        # Since I'm explicitly setting the adjustment properties, I know they are going to be rounded numbers
        ind = int(adjustment.get_value())

        if self.orientation == 'vertical':
            self.move(self.box,
                      OFFSET_LEFT,
                      OFFSET_UPPER + (BUTTON_HEIGHT * -ind))
        elif self.orientation == 'horizontal':
            self.move(self.box,
                      OFFSET_LEFT + (BUTTON_WIDTH * -ind),
                      OFFSET_UPPER)

        self.selected = self.items[ind]
        self.emit('focus-change', self.selected)

    def do_focus_change(self, item):
        ind = self.items.index(item)
        self.buttons[ind].get_style_context().remove_class('inactive')
        self.buttons[ind].get_style_context().add_class('active')

        # FIXME: This handler_id thing is a horrible hack
        # Since lists are immutable, I'm able to abuse the shit out of it to get the result of self.connect into it's own arguments
        handler_id = []
        handler_id.append(self.connect('focus-change', self._remove_focus, self.buttons[ind], handler_id))

    def _remove_focus(self, widget, item, button, handler_id):
        # item is the newly focussed item, so it can't be used to find button
        button.get_style_context().remove_class('active')
        button.get_style_context().add_class('inactive')

        # len(handler_id) should only ever be exactly 1, I'm expanding it here to get an exception if that's not the case
        self.disconnect(*handler_id)

    def next(self, *args):
        self.adjustment.set_value(self.adjustment.get_value() + 1)

    def prev(self, *args):
        self.adjustment.set_value(self.adjustment.get_value() - 1)


class StationPicker(Picker):
    def __init__(self, stations):
        super().__init__(orientation='vertical', items=stations)

    def do_focus_change(self, item):
        ind = self.items.index(item)
        self.buttons[ind].get_style_context().add_class('invisible')

        # FIXME: This handler_id thing is a horrible hack
        # Since lists are immutable, I'm able to abuse the shit out of it to get the result of self.connect into it's own arguments
        handler_id = []
        handler_id.append(self.connect('focus-change', self._remove_focus, self.buttons[ind], handler_id))

    def _remove_focus(self, widget, item, button, handler_id):
        # item is the newly focussed item, so it can't be used to find button
        button.get_style_context().remove_class('invisible')

        # len(handler_id) should only ever be exactly 1, I'm expanding it here to get an exception if that's not the case
        self.disconnect(*handler_id)


class ChannelPicker(Gtk.Stack):
    # This has a stack of the channels from multiple stations,
    # making it slightly more complex than the generic Picker or the StationPicker,
    # Still uses the generic Picker for each of those station channels lists though.
    __gsignals__ = {
        'focus-change': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self, stations):
        super().__init__()

        for station in stations:
            picker = Picker('horizontal', station.channels)
            self.add_named(picker, station.title)
            # I want the child Picker's event to propogate upwards to whoever's connected to this object.
            picker.connect('focus-change', lambda _, i: self.emit('focus-change', i))

    def next(self, *args):
        self.get_visible_child().next()

    def prev(self, *args):
        self.get_visible_child().prev()

    def change_station(self, station):
        self.set_visible_child_name(station)
        # Trigger the value_changed function to make sure current channel selections get updated
        # I could call the functon directly, but I felt it was "more right" to do it by triggering this signal
        self.get_visible_child().adjustment.emit('value-changed')

    def select(self, button=None, channel=None):
        assert (not button and not channel) or (button and channel)
        if not button and not channel:
            channel = self.get_visible_child().selected
        print('Play', channel.title, channel.uri),


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

        ## Channel scroller
        channel_box = Gtk.VBox()
        self.add_overlay(channel_box)
        self.channel_picker = ChannelPicker(stations)
        channel_box.pack_start(self.channel_picker, expand=False, fill=False, padding=0)
        # Without setting a size_request, the label will expand and fill over the picker
        self.channel_picker.set_size_request(-1, BUTTON_HEIGHT + OFFSET_UPPER)

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
#        self.epg_label.set_lines(2)  # This is how many lines it's allowed to *wrap*, it does not affect how many \n I can use
        self.epg_label.set_text(EPG_TEMPLATE)  # FIXME: Should this be all one string?
        epg_box.pack_start(self.epg_label, expand=True, fill=True, padding=0)

        self.channel_picker.connect('focus-change', self.on_channel_change)
        self.station_picker.connect('focus-change', self.on_station_change)

        ## Functions for menu navigation
        self.up = self.station_picker.prev
        self.down = self.station_picker.next
        self.left = self.channel_picker.prev
        self.right = self.channel_picker.next
        self.select = self.channel_picker.select

    def on_channel_change(self, widget, channel):
        # FIXME: Get the NOW/NEXT info from EPG via the VFS
        self.epg_label.set_text(EPG_TEMPLATE.format(
            channel_title=channel.title,
            now_title="N/A",
            next_time="12:59pm",
            next_title="N/A 2: The revenge of the the unknown",
        ))

    def on_station_change(self, widget, station):
        self.station_label.set_text(station.title)
        self.channel_picker.change_station(station.title)


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
            ss.up()
        elif keyname == 'Down':
            ss.down()
        elif keyname == 'Left':
            ss.left()
        elif keyname == 'Right':
            ss.right()
        elif keyname in ('space', 'Return', 'KP_Enter'):
            ss.select()
        else:
            print('pressed', keyname)
    window.connect('key-press-event', on_key_press)

    min_height = OFFSET_UPPER + (BUTTON_WIDTH * 2)
    min_width = OFFSET_LEFT + (BUTTON_HEIGHT * 3)
    window.set_size_request(min_width, min_height)
    window.set_default_size(BUTTON_WIDTH * 4.5, BUTTON_HEIGHT * 3.5)
    window.show_all()

    Gtk.main()
