from gi.repository import Gtk
import emcee.vfs


class ChannelSelector(Gtk.ScrolledWindow):
    # FIXME: Should this be a "tabbed" widget that switches between a single-button and a scrolledwindow depending on focus status?
    def __init__(self, station):
        super().__init__(
            # Only scroll vertically
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )

        channels = Gtk.VBox()
        self.add(channels)
        for channel in station.channels:
            channel_button = Gtk.Button.new_with_label(channel.title)
            channel_button.title = channel.title  # FIXME: Debugging
            if channel.icon:
                # If there is a channel icon, add it to the button and remove the text label.
                channel_button.set_image(Gtk.Image.new_from_file(channel.icon))
                channel_button.set_label('')  # FIXME: Can I "hide" the label without clearing it?

            channels.pack_start(channel_button, True, True, 0)
            channel_button.connect('clicked', self.select, channel)
            channel_button.connect('focus-out-event', lambda btn, direction: print('focus out', btn.title))
            channel_button.connect('focus-in-event', lambda btn, direction: print('focus in', btn.title, btn.clicked()))

        self.title = station.title  # FIXME: Debugging
        # FIXME: ScrolledWindow doesn't get focus-in event, only "focus" which doesn't differentiate in/out.
        #        Is there some way to check "any-child-has-focus" or similar?
        self.connect('focus', lambda widget, direction: print('focus change of some sort', widget.title, direction))

    def select(self, btn, channel):
        print('Selected', channel.title, channel.uri),


class StationSelector(Gtk.ScrolledWindow):
    # The UI of this channel selector is a XMB (https://en.wikipedia.org/wiki/XrossMediaBar) style UI.
    # With stations being across the horizontal bar, and channels within those stations on the vertical bars
    def __init__(self):
        # Create the horizontal scroll window
        super().__init__(
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        stations = Gtk.HBox()
        self.add_with_viewport(stations)

        # Get the list of stations, and create a vertical scroll window for each
        vfs = emcee.vfs.VirtualFilesystem()
        for station in vfs.list_stations():
            stations.add(ChannelSelector(station))


if __name__ == '__main__':
    window = Gtk.Window(title='Emcee')
    window.connect("destroy", Gtk.main_quit)  # Quit & cleanup when closed
    window.add(StationSelector())
    window.set_size_request(500, 400)
    window.show_all()

    Gtk.main()
