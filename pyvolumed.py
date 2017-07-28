#!/usr/bin/env python3

import select
import gi
from alsaaudio import Mixer

gi.require_version('Notify', '0.7')
from gi.repository import Notify


ALSA_DEVICE = 'PCM'
NOTIF_TIMEOUT = 3000


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
    Notify.init('Volume Control')
    notif = Notify.Notification.new('Volume')
    notif.set_timeout(NOTIF_TIMEOUT)

    mixer = Mixer(ALSA_DEVICE)
    poll = select.poll()
    for fd, events in mixer.polldescriptors():
        poll.register(fd, events)

    old_volume = -1
    while True:
        try:
            for _ in poll.poll():
                mixer.handleevents()
                old_volume = volume_changed(mixer, old_volume, notif)
        except KeyboardInterrupt:
            break

    Notify.uninit()


if __name__ == '__main__':
    main()
