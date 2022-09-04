#!/usr/bin/env bash
# Remove all bluetooth devices from the system
# Arguments: --dry-run
for device in $(bluetoothctl devices  | grep -o "[[:xdigit:]:]\{8,17\}");
do
    # echo "removing bluetooth device: $device | $(bluetoothctl remove $device)"
    echo "removing bluetooth device: ${device}"
    if [[ "$1" != "--dry-run" ]]; then
        bluetoothctl remove "${device}"
    fi
done