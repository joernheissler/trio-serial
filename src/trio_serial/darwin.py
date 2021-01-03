# Darwin implementation of trio-serial.
# (C) 2020 Jörn Heissler
#
# Code is based on pySerial, https://github.com/pyserial/pyserial
# (C) 2001-2020 Chris Liechti <cliechti@gmx.net>

# SPDX-License-Identifier: BSD-3-Clause

"""
Darwin backend for trio-serial.
"""

from __future__ import annotations

import array
import fcntl
import os

from trio import ClosedResourceError

from .posix import PosixSerialStream


class DarwinSerialStream(PosixSerialStream):
    """
    Darwin specific constants and functions
    """

    IOSSIOSPEED = 0x80045402  # _IOW('T', 2, speed_t)
    osx_version = int(os.uname().release.split(".")[0])

    # Tiger or above can support arbitrary serial speeds
    if osx_version >= 8:

        def _set_special_baudrate(self, fd: int) -> None:
            """
            Set custom baudrate
            """
            # use IOKit-specific call to set up high speeds
            buf = array.array("i", [self._baudrate])
            fcntl.ioctl(fd, self.IOSSIOSPEED, buf, 1)
