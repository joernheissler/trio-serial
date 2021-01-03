# Entrypoint of trio-serial.
# (C) 2020 Jörn Heissler

# SPDX-License-Identifier: BSD-3-Clause

"""
Module to select an implementation of trio-serial suitable for the user's OS.
"""

from __future__ import annotations

import os
import sys

from typing import Type

from .abstract import AbstractSerialStream, Parity, StopBits

if os.name == "posix":
    SerialStream: Type[AbstractSerialStream]

    plat = sys.platform.lower()
    if plat.startswith("linux"):
        from .linux import LinuxSerialStream as SerialStream
    elif plat == "cygwin":
        from .cygwin import CygwinSerialStream as SerialStream
    elif plat.startswith("darwin"):
        from .darwin import DarwinSerialStream as SerialStream
    elif any(plat.startswith(term) for term in ["bsd", "freebsd", "netbsd", "openbsd"]):
        from .bsd import BsdSerialStream as SerialStream
    else:
        from .posix import PosixSerialStream as SerialStream
else:
    raise ImportError(f"Platform {os.name!r} not supported.")
