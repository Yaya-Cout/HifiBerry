#!/usr/bin/python
# SPDX-License-Identifier: LGPL-2.1-or-later

# Script from /usr/share/doc/bluez-test-scripts/examples/simple-agent.py,
# from bluez-test-scripts package (modified)

from __future__ import absolute_import, print_function, unicode_literals

from optparse import OptionParser
import sys
import time
import signal
import dbus
import dbus.service
import dbus.mainloop.glib
try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject
import bluezutils
import RPi.GPIO as GPIO

####################### Config ############################
# The GPIO pin that the button is connected to
BUTTON_GPIO = 18
# The timeout for the button press
CONNECTION_TIMEOUT = 60
# The name of the adapter visible by other devices
ADAPTER_NAME = "HifiBerry"
# The button press mode (0 = connection allowed only when button is pressed,
# 1 = connection allowed during the whole timeout)
BUTTON_MODE = 1
############################################################

BUS_NAME = 'org.bluez'
AGENT_INTERFACE = 'org.bluez.Agent1'
AGENT_PATH = "/test/agent"


bus = None
device_obj = None
dev_path = None


def ask(prompt):
    try:
        return raw_input(prompt)
    except:
        return input(prompt)


def set_trusted(path):
    props = dbus.Interface(bus.get_object("org.bluez", path),
                           "org.freedesktop.DBus.Properties")
    props.Set("org.bluez.Device1", "Trusted", True)


def dev_connect(path):
    dev = dbus.Interface(bus.get_object("org.bluez", path),
                         "org.bluez.Device1")
    dev.Connect()


def set_adapter_name(path, name):
    proxy = bus.get_object("org.bluez", path)
    property_manager = dbus.Interface(proxy, "org.freedesktop.DBus.Properties")
    curr_name = property_manager.Get("org.bluez.Adapter1", "Alias")
    # Check if the name is already set
    if curr_name == name:
        print("Adapter name already set to %s" % name)
        return
    # Else set the name and wait for the change to take effect
    property_manager.Set("org.bluez.Adapter1", "Alias", name)
    poll_start = time.time()
    while curr_name != name and time.time():
        curr_name = property_manager.Get("org.bluez.Adapter1", "Alias")
        if time.time() - poll_start > 5:
            print("Failed to set adapter name")
            return False
        time.sleep(0.1)
    print("Adapter name set to: %s" % curr_name)
    return True

class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"


class Agent(dbus.service.Object):
    # Whether if the connection is authorized
    allow_connect = False
    # The last timeout set by the temporary_allow_connect function
    last_timeout = None
    exit_on_release = True

    def set_exit_on_release(self, exit_on_release):
        self.exit_on_release = exit_on_release

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="", out_signature="")
    def Release(self):
        print("Release")
        if self.exit_on_release:
            mainloop.quit()

    def auth_backend(self, device):
        # If the button mode is 0, the connection is allowed only when the
        # button is pressed
        if BUTTON_MODE == 0:
            if GPIO.input(BUTTON_GPIO) == GPIO.HIGH:
                print("yes")
                return
            else:
                print("no")
                raise Rejected("Pairing rejected by user")
        if self.allow_connect:
            print("yes")
            set_trusted(device)
            return
        else:
            print("no")
            raise Rejected("Pairing rejected by user")

    def temporary_allow_connect(self, pin):
        self.allow_connect = True
        # Cancel the last timeout if it exists
        if self.last_timeout:
            GObject.source_remove(self.last_timeout)
            print("Cancelled last timeout")
            self.last_timeout = None
        # Set a new timeout
        self.last_timeout = GObject.timeout_add_seconds(
            CONNECTION_TIMEOUT,
            self.reset_allow_connect
        )
        print("Temporary allow connect for %d seconds" % CONNECTION_TIMEOUT)

    def reset_allow_connect(self):
        self.allow_connect = False
        self.last_timeout = None
        print("Reset allow connect")

    def interrupt_handler(self, signum, frame):
        print("Stopping")
        # Reset the allow_connect flag on SIGINT
        self.reset_allow_connect()
        # Stop the mainloop
        mainloop.quit()

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print("AuthorizeService (%s, %s)" % (device, uuid))
        print("Authorize connection (yes/no) ?", end="")
        return self.auth_backend(device)

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print("RequestPinCode (%s)" % (device))
        set_trusted(device)
        return ask("Enter PIN Code: ")

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print("RequestPasskey (%s)" % (device))
        set_trusted(device)
        passkey = ask("Enter passkey: ")
        return dbus.UInt32(passkey)

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        print("DisplayPasskey (%s, %06u entered %u)" %
              (device, passkey, entered))

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        print("DisplayPinCode (%s, %s)" % (device, pincode))

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print("RequestConfirmation (%s, %06d)" % (device, passkey))
        print("Confirm passkey (yes/no) :", end="")
        return self.auth_backend(device)

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print("RequestAuthorization (%s)" % (device))
        print("Authorize (yes/no) :", end="")
        return self.auth_backend(device)

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="", out_signature="")
    def Cancel(self):
        print("Cancel")


def pair_reply():
    print("Device paired")
    set_trusted(dev_path)
    dev_connect(dev_path)
    mainloop.quit()


def pair_error(error):
    err_name = error.get_dbus_name()
    if err_name == "org.freedesktop.DBus.Error.NoReply" and device_obj:
        print("Timed out. Cancelling pairing")
        device_obj.CancelPairing()
    else:
        print("Creating device failed: %s" % (error))

    mainloop.quit()


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    capability = "KeyboardDisplay"

    parser = OptionParser()
    parser.add_option("-i", "--adapter", action="store",
                      type="string",
                      dest="adapter_pattern",
                      default=None)
    parser.add_option("-c", "--capability", action="store",
                      type="string", dest="capability")
    parser.add_option("-t", "--timeout", action="store",
                      type="int", dest="timeout",
                      default=60000)
    (options, args) = parser.parse_args()
    if options.capability:
        capability = options.capability

    path = "/test/agent"
    agent = Agent(bus, path)

    mainloop = GObject.MainLoop()

    obj = bus.get_object(BUS_NAME, "/org/bluez")
    manager = dbus.Interface(obj, "org.bluez.AgentManager1")
    manager.RegisterAgent(path, capability)

    print("Agent registered")

    # Fix-up old style invocation (BlueZ 4)
    if len(args) > 0 and args[0].startswith("hci"):
        options.adapter_pattern = args[0]
        del args[:1]

    if len(args) > 0:
        device = bluezutils.find_device(args[0],
                                        options.adapter_pattern)
        dev_path = device.object_path
        agent.set_exit_on_release(False)
        device.Pair(reply_handler=pair_reply, error_handler=pair_error,
                    timeout=60000)
        device_obj = device
    else:
        manager.RequestDefaultAgent(path)

    # Set the adapter name
    set_adapter_name("/org/bluez/hci0", ADAPTER_NAME)

    # Setup the GPIO pin
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    # If the button mode is 1, setup the callback
    if BUTTON_MODE == 1:
        GPIO.add_event_detect(
            BUTTON_GPIO,
            # GPIO.FALLING,
            GPIO.RISING,
            callback=agent.temporary_allow_connect,
            bouncetime=200
        )

    # Enable connect mode on startup if button mode is 1
    if BUTTON_MODE == 1:
        agent.temporary_allow_connect(None)

    # Setup the Ctrl+C handler
    signal.signal(signal.SIGINT, agent.interrupt_handler)

    mainloop.run()

    # adapter.UnregisterAgent(path)
    # print("Agent unregistered")
