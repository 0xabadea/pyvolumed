# pyvolumed

Display a notification when the volume of the ALSA PCM control changes.

xfce4-volumed handles that task just fine, but it only watches the master control.
In my audio setup I output the audio to an external amplifier via S/PDIF, and the only control that changes
the volume of the S/PDIF output is the PCM control.

## Installation

### Native packages

It requires `libkeybinder3`, which can be installed with your distro's package manager.

### Python packages

#### PyGObject

Follow https://pygobject.readthedocs.io/en/latest/getting_started.html to install it for your distro.

#### PyAlsaAudio

See https://github.com/larsimmisch/pyalsaaudio. For Arch Linux, see https://aur.archlinux.org/packages/python-pyalsaaudio.
