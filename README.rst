Emcee
=====
Emcee is meant to be a successor to UPMC, because UPMC has many problems and it's too hard to fix without just starting again.
The purpose of Emcee is to be used for watching streaming TV, as well as on-demand video files on both a dedicated media machine with nothing but an IR remote for input, as well as on standard desktops that will have keyboard, & mouse. Consequently it needs to have a UI that can be used easily both from a distance (across the room) and close up.

Functional requirements
=======================
General
-------
User interface
~~~~~~~~~~~~~~
* MUST have a UI for choosing TV channels & video files
* MUST be navigable entirely by arrows, enter, & back buttons
* MAY have a tile/grid layout
* MUST display posters/icons
* SHOULD support alpha-channel transparency of poster/icon images
  UPMC doesn't work with with PNG transparency due to PyGame not supporting partial transparency.

* SHOULD support vector graphic images such as SVG for post/icon image files
* MUST have support for categories
* SHOULD have support for subcategories
* The [sub]category icons SHOULD be visibly distinct from the channel/file icons
* SHOULD take advantage of hardware & OS video acceleration
* SHOULD NOT rely on any info that is not sitting in the filesystem alongside the movie files, or in the application's installation package
* SHOULD have some level of help info for easy discoverability

Playback
~~~~~~~~
* MUST display subtitles when provided, with the option to hide them.
* MUST display media info (title, length, volume, position, current time) on demand during playback
* MUST support fullscreen playback
* SHOULD support windowed playback, primarily for multitasking with audio-only media
* SHOULD NOT have a app volume control separate from the system volume so as not to confuse users with separate volume levels
* SHOULD take advantage of hardware & OS video acceleration
* SHOULD render movies & TV channels in the same window as the rest of the UI
* MAY play DVDs
  * If DVDs are supported DVD menus MUST be supported via all user-input options.

User-input
~~~~~~~~~~
* MUST work with only a keyboard
* MUST work with only an IR remote (via LIRC?)
* MAY work with only a mouse
* MUST hide the mouse as necessary when not using it
* MAY work with only a joystick/gamepad

PrisonPC
--------
* MUST allow notification popup messages (eg; from staff) to be visible during playback
* MUST support streaming media via PrisonPC's IPTV streams (multicasting?)
* SHOULD display EPG for TV stations & channels
* SHOULD support some level of branding (currently done via a background overlay)

Home
----
* MUST support on-demand files (.mp4, .avi, .mkv, etc.) in the media directory.
* MUST playback music from a HTTP stream when not watching movies.
* MUST have separate volumes for music and movies.
  * simply having music as 25% of movie volume MAY be good enough

* SHOULD display IMDB info (can be prefetched) for movies, TV shows and/or episodes

Problems we've had with UPMC
============================
Every event loop has all the keys redefined making it near impossible to remap keys and such without missing something.
We can't do real fullscreen because then you can't minimise UPMC to multi-task while listening to music, but borderless window the size of the screen doesn't work either because XFCE in Jessie doesn't let it above the panel unless it's in always-on-top mode. Current workaround is to force itself into always-on-top mode, this is ugly.
Users tend to use the mouse even though there is no visible mouse-pointer and mouse usage is completely undocumented.
Users don't like needing to go out of the stream, back to the menu to pick a new channel, next/prev channel buttons made them happy.
AOSD is horrible, it's also not actually available in the Jessie repo.
