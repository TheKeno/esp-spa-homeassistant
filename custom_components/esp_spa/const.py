"""Constants for the ESP Spa integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "esp_spa"

# The module API version this integration is written for (docs/API.md)
API_VERSION: Final = 1

CONF_TOKEN: Final = "token"

DEFAULT_NAME: Final = "Spa"
CLIENT_NAME: Final = "home-assistant"
SCAN_INTERVAL: Final = timedelta(seconds=5)

# The spa is considered connected while its last status is younger than this
MAX_STATUS_AGE_MS: Final = 15000

# Pause between panel button presses when one change needs several presses
# (for example Off -> High on a two-speed pump is two presses)
PRESS_DELAY: Final = 1.0

# How long after a command to poll again, so the new state shows quickly
REFRESH_DELAY: Final = 1.0

# Reminder codes in the status, and the keys used for states and events
REMINDERS: Final = {4: "clean_filter", 9: "check_sanitizer", 10: "check_ph"}
REMINDER_OTHER: Final = "other"
REMINDER_NONE: Final = "none"
# 0x1E means "see the error", it is not a reminder
REMINDER_FAULT: Final = 0x1E

# Error codes from the spa's error log, and the keys used for states
FAULTS: Final = {
    15: "sensors_out_of_sync",
    16: "low_flow",
    17: "flow_failed",
    18: "settings_reset",
    19: "priming",
    20: "clock_failed",
    21: "settings_reset",
    22: "memory_failure",
    26: "sensors_out_of_sync_service",
    27: "heater_dry",
    28: "heater_may_be_dry",
    29: "water_too_hot",
    30: "heater_too_hot",
    31: "sensor_a_fault",
    32: "sensor_b_fault",
    34: "pump_stuck",
    35: "hot_fault",
    36: "gfci_test_failed",
    37: "standby",
}
FAULT_NONE: Final = "none"
FAULT_UNKNOWN: Final = "unknown"

EVENT_ERROR: Final = "error"
