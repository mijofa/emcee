#!/usr/bin/python3

from gi.repository import Gtk, Gdk, GdkPixbuf, GdkX11, GLib

class osd_window(Gtk.Window):
    def __init__(self, parent):
        super(osd_window, self).__init__(
            title='OSD',
            role='OSD',
            border_width=0,
            resizable=False,
            decorated=False,
            accept_focus=False,
            skip_pager_hint=True,
            skip_taskbar_hint=True,
        )
        self.connect('show', self.reposition)
        parent.connect('configure-event', self.reposition)
        self.set_transient_for(parent) # Force the OSD to stay above the main window

        overlay = Gtk.Overlay()
        self.add(overlay)
        bg = Gtk.Image.new_from_file('osd_bg.png')
        bg.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1)) # Set the background to black
        overlay.add(bg)
        self.add = overlay.add_overlay

    def reposition(self, parent, *args, **kwargs):
        # Set OSD position based on the position of the main window
        osd_size = self.get_size()
        parent_pos = parent.get_position()
        parent_size = parent.get_size()
        pos_offset = parent_size[0]-osd_size[0]
        self.move(parent_pos[0]+pos_offset-osd_margin, parent_pos[1]+osd_margin)

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show_all()
            self.reposition(window)

osd = osd_window(window)
textview = Gtk.TextView()
##textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
textbuffer = textview.get_buffer()
textbuffer.set_text("Welcome to the PyGObject Tutorial\n\nThis guide aims to provide an introduction to using Python and GTK+.\n\nIt includes many sample code files and exercises for building your knowledge of the language.", -1)
textview.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0)) # Set the background to transparent
textview.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1)) # Set the foreground to white
osd.add(textview)

if __name__ == '__main__':
    Gtk.main()
