import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GObject', '2.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, GObject, Gdk, Pango
import emcee.vfs
import logging
logger = logging.getLogger(__name__)

# Note, BUTTON_SIZE should be slightly larger than the icon images themselves.
# I'm not really sure how much larger as I never bothered to look for the numbers,
# but the Button has it's own border that it puts around the icons that needs to be accounted for.
BUTTON_WIDTH = 150  # FIXME: This is based on the current size of the channel gifs
BUTTON_HEIGHT = 150  # FIXME: This is based on the current size of the channel gifs
OFFSET_UPPER = BUTTON_HEIGHT * 0.75
OFFSET_LEFT = BUTTON_WIDTH * 0.75

EPG_TEMPLATE = """{channel.title}
Currently playing:
  {channel.epg_brief.now}
Next ({channel.epg_brief.next_starttime}):
  {channel.epg_brief.next}"""

# FIXME: Move this stylesheet out into a CSS file and import that as a theme in the application
style_provider = Gtk.CssProvider()
css = b"""
#station-name, #epg {
    padding: 40px 0 0 40px;
    font-size: 2em;
}

.button,  /* Jessie */
button    /* Stretch */
{
    font-size: 90px;  /* FIXME: Magic number based on the icon size */
    border-radius: 99999px;  /* FIXME: This is a stupid number to put here */
    color: green;

    /* Remove the button style entirely and just display the image */
    box-shadow: none;
    border-style: none;
    /* GtkButton by default has a background-image.
     *  That must be removed before we can change the background-color
     */
    background-image: none;
    transition: 1s ease-in-out;
}

.button.inactive,  /* Jessie */
button.inactive    /* Stretch */
{
    /* I wanted to make inactive icons smaller, but CSS can't be used to change the size of objects.
     * I think this can be done with a background image, but not worth the effort
     */
    opacity: 0.4;
    color: grey;
}
.button.inactive:hover,  /* Jessie */
button.inactive:hover    /* Stretch */
{
    /* Only highlight the .active one, because the ? buttons don't highlight
     * and it's less noticable on .active than on .inactive */
    opacity: 0.6;
}
.button.active:hover,  /* Jessie */
button.active:hover    /* Stretch */
{
    /* I know this is deprecated, but I want it to work on Jessie & Stretch */
    -gtk-image-effect: highlight;
/*    -gtk-image-effect: highlight/dim/none; */
}
#ChannelPicker #Picker {
    opacity: 0;
    transition: 1s ease-in-out;
}
#ChannelPicker #Picker.active{
    opacity: 1;
}
#StationPicker * .button.active,  /* Jessie */
#StationPicker * button.active    /* Stretch */
{
    /* This button is directly behind the active ChannelPicker, make it invisible */
    opacity: 0;
}
"""
#/*
# * GtkImage,  /* Jessie */
# * image      /* Stretch */
# * {
# *     box-shadow: none;
# *     border-style: none;
# *     border-image: none;
# *     background-image: none;
# *     background-color: transparent;
# * }
# */
style_provider.load_from_data(css)
Gtk.StyleContext.add_provider_for_screen(
    screen=Gdk.Screen.get_default(),
    provider=style_provider,
    priority=Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)


class ImageOrLabelButton(Gtk.Button):
    __gsignals__ = {
        'focus-in': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'focus-out': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }
    saturated = False
    pixbuf_copy = None

    def __init__(self, title, icon):
        super().__init__()
        self.title = title
        if icon:
            image = Gtk.Image.new_from_file(icon)
            self.pixbuf_copy = image.get_pixbuf().copy()
            self.pixbuf_copy.saturate_and_pixelate(image.get_pixbuf(), 0, False)
            self.set_image(image)
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

    def do_focus_in(self):
        self.get_style_context().remove_class('inactive')
        self.get_style_context().add_class('active')
        print("Focus in", self.title, self.saturated)
        if self.pixbuf_copy and not self.saturated:
            print("Not saturated, saturating", self.title)
            self.pixbuf_copy.saturate_and_pixelate(self.get_image().get_pixbuf(), 1, False)
            self.saturated = True

    def do_focus_out(self):
        self.get_style_context().remove_class('active')
        self.get_style_context().add_class('inactive')
        if self.pixbuf_copy and self.saturated:
            print("Saturated, desaturating", self.title)
            self.pixbuf_copy.saturate_and_pixelate(self.get_image().get_pixbuf(), 0, False)
            self.saturated = False


class Picker(Gtk.Layout):
    # Generic scroller for any number of itmes in a single row or column.
    __gsignals__ = {
        'focus-change': (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_PYOBJECT,)),
        'selected': (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self, orientation, items, *args, **kwargs):
        assert orientation in ('horizontal', 'vertical')
        self.orientation = orientation
        self.items = items

        super().__init__(*args, **kwargs)
        self.set_name("Picker")

        # It's easier to move one box around than it is to have move around all the buttons themselves.
        if self.orientation == 'vertical':
            self.box = Gtk.VBox()
        elif self.orientation == 'horizontal':
            self.box = Gtk.HBox()
        self.put(self.box, 0, 0)

        self.buttons = []
        for item in self.items:
            button = ImageOrLabelButton(title=item.title, icon=item.icon)
            button.connect('clicked', self.on_button_click)
            self.buttons.append(button)
            self.box.pack_start(self.buttons[-1], expand=False, fill=False, padding=0)

        self.adjustment = Gtk.Adjustment(value=0,
                                         lower=0,
                                         upper=len(self.items) - 1,
                                         step_increment=1)
        self.adjustment.connect('value-changed', self._value_changed)
        # Trigger the focus-change when the widget gets realised.
        # This allows the station title and channel EPG to update on startup.
        self.connect('realize', lambda _: self._value_changed(self.adjustment))

    def on_button_click(self, button):
        index = self.buttons.index(button)
        if index == self.adjustment.get_value():
            self.emit('selected', self.items[index])
        else:
            self.adjustment.set_value(index)

    def _value_changed(self, adjustment):
        # List indices must be an int, however the adjustment property values are floats.
        # Since I'm explicitly setting the adjustment properties, I know they are going to be rounded numbers
        ind = int(adjustment.get_value())

        if self.orientation == 'vertical':
            self.move(self.box,
                      0,
                      OFFSET_UPPER + (BUTTON_HEIGHT * -ind))
        elif self.orientation == 'horizontal':
            self.move(self.box,
                      OFFSET_LEFT + (BUTTON_WIDTH * -ind),
                      0)

        self.selected = self.items[ind]
        self.emit('focus-change', self.selected)

    def do_focus_change(self, item):
        ind = self.items.index(item)
        self.buttons[ind].emit('focus-in')

        # FIXME: This handler_id thing is a horrible hack
        # Since lists are immutable, I'm able to abuse the shit out of it to get the result of self.connect into it's own arguments
        handler_id = []
        handler_id.append(self.connect('focus-change', self._remove_focus, self.buttons[ind], handler_id))

    def _remove_focus(self, widget, item, button, handler_id):
        # item is the newly focussed item, so it can't be used to find button
        button.emit('focus-out')

        # len(handler_id) should only ever be exactly 1, I'm expanding it here to get an exception if that's not the case
        self.disconnect(*handler_id)

    def next(self, *args):
        self.adjustment.set_value(self.adjustment.get_value() + 1)

    def prev(self, *args):
        self.adjustment.set_value(self.adjustment.get_value() - 1)

    def select(self):
        self.emit('selected', self.selected)


class StationPicker(Picker):
    def __init__(self, stations, *args, **kwargs):
        super().__init__(orientation='vertical', items=stations, *args, **kwargs)
        self.set_name("StationPicker")


class ChannelPicker(Gtk.Stack):
    # This has a stack of the channels from multiple stations,
    # making it slightly more complex than the generic Picker or the StationPicker,
    # Still uses the generic Picker for each of those station channels lists though.
    __gsignals__ = {
        'focus-change': (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_PYOBJECT,)),
        'selected': (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self, stations, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_name("ChannelPicker")

        for station in stations:
            picker = Picker('horizontal', station.channels)
            self.add_named(picker, station.title)
            # FIXME: There must be a better way to do this
            picker.connect('focus-change', lambda _, i: self.emit('focus-change', i))
            picker.connect('selected', lambda _, i: self.emit('selected', i))

    def do_focus_change(self, item):
        for st in self.get_children():
            st.get_style_context().remove_class('active')
        self.get_visible_child().get_style_context().remove_class('inactive')
        self.get_visible_child().get_style_context().add_class('active')

        # FIXME: This handler_id thing is a horrible hack
        # Since lists are immutable, I'm able to abuse the shit out of it to get the result of self.connect into it's own arguments
        handler_id = []
        handler_id.append(self.connect('focus-change', self._remove_focus, self.get_visible_child(), handler_id))

    def _remove_focus(self, widget, item, picker, handler_id):
        # item is the newly focussed item, so it can't be used to find button
        picker.get_style_context().remove_class('active')
        picker.get_style_context().add_class('inactive')

        # len(handler_id) should only ever be exactly 1, I'm expanding it here to get an exception if that's not the case
        self.disconnect(*handler_id)

    def next(self, *args):
        self.get_visible_child().next()

    def prev(self, *args):
        self.get_visible_child().prev()

    def change_station(self, station):
        self.set_visible_child_name(station)
        # Trigger the value_changed function to make sure current channel selections get updated
        # I could call the functon directly, but I felt it was "more right" to do it by triggering this signal
        self.get_visible_child().adjustment.emit('value-changed')

    def select(self):
        self.get_visible_child().select()


class StreamSelector(Gtk.Overlay):
    __gsignals__ = {
        'selected': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        'select_channel': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'next_channel': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'prev_channel': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'next_station': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'prev_station': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__()
        vfs = emcee.vfs.VirtualFilesystem()
        stations = vfs.list_stations()

        under_box = Gtk.HBox()
        self.add(under_box)

        ## Station scroller
        self.station_picker = StationPicker(stations, margin_left=OFFSET_LEFT)
        under_box.pack_start(self.station_picker, expand=False, fill=False, padding=0)
        # Without setting a size_request, the info_box will until this is 1px wide.
        self.station_picker.set_size_request(BUTTON_WIDTH, -1)

        ## Channel scroller
        self.channel_picker = ChannelPicker(
            stations,
            margin_top=OFFSET_UPPER,
            halign=Gtk.Align.START,
            valign=Gtk.Align.START,
        )
        self.add_overlay(self.channel_picker)
        # If I don't set the size_request here it will default to 1x1px
        self.channel_picker.set_size_request(
            # FIXME: I should be able to tell it to figure this out on it's own, but -1 just goes for 1x1px
            OFFSET_LEFT + max([len(s.channels) for s in stations]) * BUTTON_WIDTH,
            BUTTON_HEIGHT)

        ## Current selection info
        info_box = Gtk.VBox()
        under_box.pack_start(info_box, expand=True, fill=True, padding=0)

        ## Station label to sit above the channel scroller
        self.station_label = Gtk.Label(
            name="station-name",
            halign=Gtk.Align.START,
            valign=Gtk.Align.START,
            justify=Gtk.Justification.LEFT,
        )
        self.station_label.set_size_request(-1, OFFSET_UPPER)
        self.station_label.set_line_wrap(False)
        self.station_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.station_label.set_text("Station title")
        info_box.pack_start(self.station_label, expand=False, fill=False, padding=0)

        ## EPG info to go below the channel scroller
        # Spacer to keep below the channel scroller
        epg_spacer = Gtk.DrawingArea()
        epg_spacer.set_size_request(-1, BUTTON_HEIGHT)
        info_box.pack_start(epg_spacer, expand=False, fill=False, padding=0)
        self.epg_label = Gtk.Label(
            name="epg",
            halign=Gtk.Align.START,
            valign=Gtk.Align.START,
            justify=Gtk.Justification.LEFT,
        )
        self.epg_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.epg_label.set_line_wrap(True)  # Has no effect with ellipsize set unless set_lines is called
        self.epg_label.set_lines(2)  # This is how many lines it's allowed to *wrap*, it does not affect how many \n I can use
        # NOTE: With the wrapping set up like this, it's possible the channel name or the now/next strings will wrap and look bad.
        # FIXME: Should we use separate labels here so as to get different wrapping behaviour for each?
        #        Alternatively can we use the markup thing to do that?
        self.epg_label.set_text(EPG_TEMPLATE)
        info_box.pack_start(self.epg_label, expand=True, fill=True, padding=0)

        self.channel_picker.connect('focus-change', self.on_channel_change)
        self.station_picker.connect('focus-change', self.on_station_change)
        self.channel_picker.connect('selected', lambda _, i: self.emit('selected', i))

        ## Signal handlers for menu navigation
        ## These all get triggered by their associated signals being emitted
        self.do_prev_station = self.station_picker.prev
        self.do_next_station = self.station_picker.next
        self.do_prev_channel = self.channel_picker.prev
        self.do_next_channel = self.channel_picker.next
        self.do_select_channel = self.channel_picker.select

    def on_channel_change(self, widget, channel):
        # FIXME: Get the NOW/NEXT info from EPG via the VFS
        self.epg_label.set_text(EPG_TEMPLATE.format(channel=channel))

    def on_station_change(self, widget, station):
        self.station_label.set_text(station.title)
        self.channel_picker.change_station(station.title)


if __name__ == '__main__':
    window = Gtk.Window(title='Emcee')
    window.connect("destroy", Gtk.main_quit)  # Quit & cleanup when closed
    ss = StreamSelector()
    window.add(ss)
    ss.connect('selected', lambda _, selected: print('Selected', selected))

    def on_key_press(widget, event):
        # FIXME: Use -gtk-key-bindings in CSS for configuring this. Can't be done in Mike's current version
        #   https://developer.gnome.org/gtk3/stable/gtk3-Bindings.html
        #   I think it comes in ~3.16 although the property name is "gtk-key-bindings" until a later version when the - is prefixed
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            Gtk.main_quit()
        elif keyname == 'Up':
            ss.emit('prev_station')
        elif keyname == 'Down':
            ss.emit('next_station')
        elif keyname == 'Left':
            ss.emit('prev_channel')
        elif keyname == 'Right':
            ss.emit('next_channel')
        elif keyname in ('space', 'Return', 'KP_Enter'):
            ss.emit('select_channel')
        else:
            print('Pressed unbound key:', keyname)
    window.connect('key-press-event', on_key_press)

    min_height = OFFSET_UPPER + (BUTTON_HEIGHT * 2)
    min_width = OFFSET_LEFT + (BUTTON_WIDTH * 3)
    window.set_size_request(min_width, min_height)
    window.set_default_size(
        min_width + BUTTON_WIDTH * 1.5,
        min_height + BUTTON_HEIGHT * 1.5
    )
    window.show_all()

    Gtk.main()