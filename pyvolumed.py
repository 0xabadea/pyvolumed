#!/usr/bin/env python3

import gi
import os
import select
import threading
from alsaaudio import Mixer

gi.require_version('GLib', '2.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Keybinder', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Keybinder
from gi.repository import Notify


ALSA_DEVICE = 'PCM'
NOTIF_TIMEOUT = 3000


def volume_key_callback(keystr, user_data):
    mixer, vol_change = user_data
    volume = max(mixer.getvolume())
    new_volume = max(0, min(100, volume + vol_change))
    mixer.setvolume(new_volume)


def start_mixer_poll_thread(mixer, notif):
    poll = select.poll()
    for fd, events in mixer.polldescriptors():
        poll.register(fd, events)

    # We need a way to end the poll thread. We use a pipe: poll on its
    # read end and (when we need to end the thread) we write to its write end.
    quit_rfd, quit_wfd = os.pipe()
    poll.register(quit_rfd, select.POLLIN)

    def poll_mixer():
        old_volume = -1
        while True:
            for fd, _ in poll.poll():
                if fd == quit_rfd:
                    return
                else:
                    mixer.handleevents()
                    old_volume = volume_changed(mixer, old_volume, notif)

    thread = threading.Thread(target=poll_mixer)
    thread.start()

    return (thread, quit_wfd)


def volume_changed(mixer, old_volume, notif):
    volume = max(mixer.getvolume())

    if volume != old_volume:
        notif.update('Volume', icon=get_icon_name(volume))
        notif.set_hint_int32('value', volume)
        notif.show()

    return volume


def get_icon_name(volume):
    # As per https://standards.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html#names
    if volume <= 0:
        return 'audio-volume-muted'
    if volume <= 30:
        return 'audio-volume-low'
    elif volume <= 70:
        return 'audio-volume-medium'
    else:
        return 'audio-volume-high'


def main():
    Gtk.init()

    Notify.init('Volume Control')
    notif = Notify.Notification.new('Volume')
    notif.set_timeout(NOTIF_TIMEOUT)

    mixer = Mixer(ALSA_DEVICE)
    thread, quit_wfd = start_mixer_poll_thread(mixer, notif)

    Keybinder.init()
    Keybinder.bind('AudioLowerVolume', volume_key_callback, (mixer, -5))
    Keybinder.bind('AudioRaiseVolume', volume_key_callback, (mixer, 5))

    # Apparently need to run the GLib main loop, otherwise the notification
    # is lost after 10 minutes or so, and we get a
    # "The name was not provided by any .service files" error from DBus
    # when showing it.
    # We also need to run the loop for Keybinder to work. Actually we should
    # run the GTK loop, but that can't be interrupted by SIGINT, and the GLib
    # loop seems to work well too.
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass

    os.write(quit_wfd, b'quit')
    thread.join()

    notif.close()
    Notify.uninit()


if __name__ == '__main__':
    main()
