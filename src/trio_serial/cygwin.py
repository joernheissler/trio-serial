# Cygwin implementation of trio-serial.
# (C) 2020 Jörn Heissler
#
# Code is based on pySerial, https://github.com/pyserial/pyserial
# (C) 2001-2020 Chris Liechti <cliechti@gmx.net>

# SPDX-License-Identifier: BSD-3-Clause

"""
Cygwin backend for trio-serial.
"""

from __future__ import annotations

from .posix import PosixSerialStream


class CygwinSerialStream(PosixSerialStream):
    """
    Cygwin specific constants and functions
    """

    BAUDRATE_CONSTANTS = {
        128000: 0x01003,
        256000: 0x01005,
        500000: 0x01007,
        576000: 0x01008,
        921600: 0x01009,
        1000000: 0x0100A,
        1152000: 0x0100B,
        1500000: 0x0100C,
        2000000: 0x0100D,
        2500000: 0x0100E,
        3000000: 0x0100F,
    }
