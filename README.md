# HifiBerry

## Introduction

HifiBerry is a simple script to make a Raspberry PI a bluetooth sink.

## Installation

Installation is in three parts: first, install all dependencies, configure permissions, PulseAudio and Bluetooth. Second, plug the button to the pin 18 (GPIO 24). Third, install HifiBerry to handle devices connects.

### Global config

Install dependencies

```bash
sudo apt install bluez-test-scripts python3-rpi.gpio pulseaudio-module-bluetooth bluez-tools python3-dbus
```

Add users to groups

```bash
sudo gpasswd -a pi pulse
sudo gpasswd -a pi lp
sudo gpasswd -a pulse lp
sudo gpasswd -a pi audio
sudo gpasswd -a pulse audio
```

Setup PulseAudio and Bluetooth device class

```bash
sudo sh -c "echo 'extra-arguments = --exit-idle-time=-1 --log-target=syslog' >> /etc/pulse/client.conf"
sudo hciconfig hci0 up
sudo hciconfig hci0 class 0x200420
sudo reboot
```

### Button

Connect the button to the pin 18 (GPIO 24) and ground. The button should be connected to ground when not pressed.

To test the button, run the following command:

```bash
python3 button.py
```

### HifiBerry config

<!-- Script is included in the repository
Copy bluezutils to the script directory.

```bash
cp /usr/share/doc/bluez-test-scripts/examples/bluezutils.py .
``` -->

Configure the systemd service (optional, needed if you use the button and want to start the script on boot).

You may want to change the path to the script and the user (edit the User, Group and ExecStart lines).

Copy or link the service file to the systemd directory.

```bash
# Yoy can choose to copy or link the file, I prefer to link it, but it's less secure, so I recommand to copy it
sudo cp hifiberry.service /etc/systemd/system/ # To copy the service file (recommended)
sudo ln hifiberry.service /etc/systemd/system/hifiberry.service # To create a symlink (if you want to edit the service file, it's less secure if you set the wrong permissions to the original file, as the service can ask for root permissions)
```

Then, enable and start the service.

```bash
sudo systemctl daemon-reload
sudo systemctl enable hifiberry.service
sudo systemctl start hifiberry.service
```

To disable the service, run

```bash
sudo systemctl disable bluetooth-sink.service
```

## Reset the paired devices

To reset the paired devices, run

```bash
./reset-paired-devices.sh
```

## Troubleshooting

### Pulseaudio / Bluetooth

If you have an error like this:

```bash
E: [pulseaudio] module-bluetooth-policy.c: Failed to get transport: org.bluez.Error.Failed (Operation failed)
```

You may need to change the Bluetooth device class. To do so, run

```bash
sudo hciconfig hci0 class 0x200420
```

### Button

If you have an error like this:

```bash
Traceback (most recent call last):
  File "button.py", line 1, in <module>
    import RPi.GPIO as GPIO
ModuleNotFoundError: No module named 'RPi'
```

You may need to install the RPi.GPIO module. To do so, run

```bash
sudo apt install python3-rpi.gpio
```

### Useful links

- [Pinout.xyz](https://fr.pinout.xyz/) to find the pinout of the Raspberry PI
- [TheCodeNinja](https://thecodeninja.net/2016/06/bluetooth-audio-receiver-a2dp-sink-with-raspberry-pi/) for the original config
- [BlueZ test scripts](https://github.com/bluez/bluez/tree/master/test) for the `bluezutils.py`, `simple-agent.py` and other examples of scripts
