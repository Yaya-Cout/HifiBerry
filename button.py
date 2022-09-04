#!/usr/bin/env python3
"""Script to test the button."""
import logging
import time

import RPi.GPIO as GPIO

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# TODO: Import it from sinkpair.py, or make it a config file
BUTTON_GPIO = 18

# GPIO.setwarnings(False)
# Use physical pin numbering
GPIO.setmode(GPIO.BOARD)
# Set pin to be an input pin and set initial value to be pulled low (off)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

LAST_STATE = -1

while True:
    if GPIO.input(BUTTON_GPIO) == GPIO.HIGH:
        if LAST_STATE != 1:
            logging.info("Button is pushed")
            LAST_STATE = 1
    else:
        if LAST_STATE != 0:
            logging.info("Button is released!")
            LAST_STATE = 0
    time.sleep(0.1)
