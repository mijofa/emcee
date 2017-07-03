from gi.repository import Gtk
import emcee.vfs


class ChannelSelector(Gtk.ScrolledWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only scroll horizontally
        self.set_policy(hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
                        vscrollbar_policy=Gtk.PolicyType.NEVER)
        self.set_size_request(200, 100)

        vfs = emcee.vfs.VirtualFilesystem()
        stations = Gtk.HBox()
        self.add_with_viewport(stations)
        for s in vfs.list_stations():
            sw = Gtk.ScrolledWindow()
            # Only scroll vertically
            sw.set_policy(hscrollbar_policy=Gtk.PolicyType.NEVER,
                          vscrollbar_policy=Gtk.PolicyType.AUTOMATIC)
            stations.add(sw)
            channels = Gtk.VBox()
            sw.add(channels)
            for c in vfs.list_channels(s):
                b = Gtk.Button.new_with_label(c)
                b.set_size_request(30, 30)
                channels.pack_start(b, True, True, 0)


if __name__ == '__main__':
    window = Gtk.Window(title='Emcee')
    window.connect("destroy", Gtk.main_quit)  # Quit & cleanup when closed
    window.add(ChannelSelector())
    window.show_all()

    Gtk.main()
