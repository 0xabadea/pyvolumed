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


PCM_DEVICE = 'PCM'
SPDIF_DEVICE = 'IEC958'
NOTIF_TIMEOUT = 3000


def volume_key_callback(keystr, user_data):
    pcm_mixer, vol_change = user_data
    volume = max(pcm_mixer.getvolume())
    new_volume = max(0, min(100, volume + vol_change))
    pcm_mixer.setvolume(new_volume)


def mute_key_callback(keystr, user_data):
    spdif_mixer = user_data
    mute = max(spdif_mixer.getmute())
    new_mute = 0 if mute else 1
    spdif_mixer.setmute(new_mute)


def start_mixer_poll_thread(pcm_mixer, pcm_notif, spdif_mixer, spdif_notif):
    poll = select.poll()
    for fd, events in pcm_mixer.polldescriptors():
        poll.register(fd, events)
    for fd, events in spdif_mixer.polldescriptors():
        poll.register(fd, events)

    # We need a way to end the poll thread. We use a pipe: poll on its
    # read end and (when we need to end the thread) we write to its write end.
    quit_rfd, quit_wfd = os.pipe()
    poll.register(quit_rfd, select.POLLIN)

    def poll_mixer():
        old_volume = pcm_volume_changed(pcm_mixer, None, pcm_notif)
        old_mute = spdif_mute_changed(spdif_mixer, None, spdif_notif)
        while True:
            for fd, _ in poll.poll():
                if fd == quit_rfd:
                    return
                else:
                    pcm_mixer.handleevents()
                    old_volume = pcm_volume_changed(pcm_mixer, old_volume, pcm_notif)
                    spdif_mixer.handleevents()
                    old_mute = spdif_mute_changed(spdif_mixer, old_mute, spdif_notif)

    thread = threading.Thread(target=poll_mixer)
    thread.start()

    return (thread, quit_wfd)


def pcm_volume_changed(pcm_mixer, old_volume, pcm_notif):
    volume = max(pcm_mixer.getvolume())

    if old_volume != None and volume != old_volume:
        pcm_notif.update('Volume', icon=get_icon_name(volume))
        pcm_notif.set_hint('value', GLib.Variant("i", volume))
        pcm_notif.show()

    return volume


def spdif_mute_changed(spdif_mixer, old_mute, spdif_notif):
    mute = max(spdif_mixer.getmute())

    if old_mute != None and mute != old_mute:
        spdif_notif.update('S/PDIF ' + ('muted' if mute else 'unmuted'), icon=get_icon_name(0 if mute else 100))
        spdif_notif.show()

    return mute


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

    Notify.init('pyvolumed')
    pcm_notif = Notify.Notification.new('Volume')
    pcm_notif.set_timeout(NOTIF_TIMEOUT)
    spdif_notif = Notify.Notification.new('SPDIF')
    spdif_notif.set_timeout(NOTIF_TIMEOUT)

    pcm_mixer = Mixer(PCM_DEVICE)
    spdif_mixer = Mixer(SPDIF_DEVICE)

    thread, quit_wfd = start_mixer_poll_thread(pcm_mixer, pcm_notif, spdif_mixer, spdif_notif)

    Keybinder.init()
    Keybinder.bind('AudioLowerVolume', volume_key_callback, (pcm_mixer, -5))
    Keybinder.bind('AudioRaiseVolume', volume_key_callback, (pcm_mixer, 5))
    Keybinder.bind('AudioMute', mute_key_callback, spdif_mixer)

    # Apparently need to run the GLib main loop, otherwise the notification is
    # lost after 10 minutes or so, and we get a "The name was not provided by
    # any .service files" error from DBus when showing it.
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

    spdif_notif.close()
    pcm_notif.close()
    Notify.uninit()


if __name__ == '__main__':
    main()
