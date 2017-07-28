# pyvolumed

Display a notification when the volume of the ALSA PCM control changes.

xfce4-notifyd handles that task just fine, but it only watches the master control.
In my audio setup I output the audio to an external amplifier via S/PDIF, and the only control that changes
the volume of the S/PDIF output is the PCM control.
