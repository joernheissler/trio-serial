# BSD implementation of trio-serial.
# (C) 2020 Jörn Heissler
#
# Code is based on pySerial, https://github.com/pyserial/pyserial
# (C) 2001-2020 Chris Liechti <cliechti@gmx.net>

# SPDX-License-Identifier: BSD-3-Clause

"""
BSD backend for trio-serial.
"""

from __future__ import annotations

from .posix import PosixSerialStream


class ReturnBaudrate:
    def __getitem__(self, key: int) -> int:
        return key


class BsdSerialStream(PosixSerialStream):
    """
    BSD specific constants and functions
    """

    # Only tested on FreeBSD:
    # The baud rate may be passed in as a literal value.
    BAUDRATE_CONSTANTS = ReturnBaudrate()
