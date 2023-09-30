# Public interface of trio-serial.
# (C) 2020 Jörn Heissler

# SPDX-License-Identifier: BSD-3-Clause

"""
Public interface of trio-serial. Modules implement the OS specific parts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import ByteString, Optional

import trio.lowlevel
from trio._util import ConflictDetector
from trio.abc import Stream


class Parity(Enum):
    """
    Enumeration of parity types.
    """

    #: No parity
    NONE = auto()

    #: Even parity
    EVEN = auto()

    #: Odd parity
    ODD = auto()

    #: Parity bit always 1
    MARK = auto()

    #: Parity bit always 0
    SPACE = auto()


class StopBits(Enum):
    """
    Enumeration of stop bit lengths.
    """

    #: One bit
    ONE = auto()

    #: One and a half bits
    ONE_POINT_FIVE = auto()

    #: Two bits
    TWO = auto()


class AbstractSerialStream(Stream, ABC):
    """
    Operating system independant public interface of :py:class:`SerialStream`.
    """

    # Name of port, e.g. "/dev/ttyUSB0" or "COM7"
    _port: str

    # Lock for exclusive use
    _exclusive: bool

    # Baudrate, e.g. 115200 or 9600
    _baudrate: int

    # Bits per byte
    _bytesize: int

    # Parity
    _parity: Parity

    # Number of stop bits
    _stopbits: StopBits

    # Software Flow Control
    _xonxoff: bool

    # Hardware Flow Control
    _rtscts: bool

    # Guard against parallel recv or send on the port.
    _recv_conflict_detector: ConflictDetector
    _send_conflict_detector: ConflictDetector

    def __init__(
        self,
        port: str,
        *,
        exclusive: bool = False,
        baudrate: int = 115200,
        bytesize: int = 8,
        parity: Parity = Parity.NONE,
        stopbits: StopBits = StopBits.ONE,
        xonxoff: bool = False,
        rtscts: bool = False,
    ) -> None:
        """
        Create new SerialStream object.

        Args:
            port: Name of port. Format depends on implementation. This could be "/dev/ttyUSB0" on Linux or
                  "COM7" on Windows.
            exclusive: Lock port for exclusive use
            baudrate: Initial Port speed
            bytesize: Number of bits per byte
            parity: Parity
            stopbits: Number of stop bits
            xonxoff: Software Flow Control with XON/XOFF
            rtscts: Hardware Flow Control with RTS/CTS
        """
        self._port = port
        self._exclusive = exclusive
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._xonxoff = xonxoff
        self._rtscts = rtscts
        self._recv_conflict_detector = ConflictDetector(
            "Another task is currently sending data on this SerialStream"
        )
        self._send_conflict_detector = ConflictDetector(
            "Another task is currently receiving data on this SerialStream"
        )

    async def __aenter__(self) -> AbstractSerialStream:
        """
        Enter the async context manager, open the port.
        __aexit__ is inherited from the super class.

        Returns:
            self
        """
        await self.aopen()
        return self

    def __del__(self) -> None:
        """
        Destructor. Closes the port if still open.
        """
        self._close()

    @property
    def port(self) -> str:
        """
        Get the port name.

        Returns:
            port name or device
        """
        return self._port

    @abstractmethod
    async def aclose(self) -> None:
        """
        Cleanly close the port.

        Do nothing if already closed.
        """

    @abstractmethod
    async def aopen(self) -> None:
        """
        Open the port and configure it with the initial state from :py:meth:`__init__`.
        """

    @abstractmethod
    def _close(self) -> None:
        """
        Close the port as fast as possible, even if closing it quick+dirty.
        Do not use this method directly. Instead use :py:meth:`aclose`
        or the async context manager.

        Do nothing if already closed.
        """

    @abstractmethod
    async def discard_input(self) -> None:
        """
        Discard any unread input.
        """

    @abstractmethod
    async def discard_output(self) -> None:
        """
        Discard any unwritten output.
        """

    @abstractmethod
    async def send_break(self, duration: float = 0.25) -> None:
        """
        Transmit a continuous stream of zero-valued bits for a specific duration.

        Params:
            duration: Number of seconds
        """

    async def receive_some(self, max_bytes: Optional[int] = None) -> bytes:
        """
        Receive some bytes from the serial port.

        Args:
            max_bytes: Maximum number of bytes to receive.

        Returns:
            On success, between 1 and :py:obj:`max_bytes` bytes.
            On End-of-file (e.g. serial port is gone) an empty bytes object is returned.
        """
        with self._recv_conflict_detector:
            return bytes(await self._recv(max_bytes))

    async def send_all(self, data: ByteString) -> None:
        """
        Send :py:obj:`data` to the serial port.
        Args:
            data: Data to send
        """
        with self._send_conflict_detector:
            with memoryview(data) as data:
                if not data:
                    await trio.lowlevel.checkpoint()
                total_sent = 0
                while total_sent < len(data):
                    await self._wait_writable()
                    with data[total_sent:] as remaining:
                        sent = await self._send(remaining)
                        total_sent += sent

    async def wait_send_all_might_not_block(self) -> None:
        """
        Wait until sending might not block (it still might block).
        """
        with self._send_conflict_detector:
            await self._wait_writable()

    @abstractmethod
    async def get_cts(self) -> bool:
        """
        Retrieve current *Clear To Send* state.

        Returns:
            Current CTS state
        """

    @abstractmethod
    async def get_rts(self) -> bool:
        """
        Retrieve current *Ready To Send* state.

        Returns:
            Current RTS state
        """

    @abstractmethod
    async def set_rts(self, value: bool) -> None:
        """
        Set *Ready To Send* state.

        Args:
            value: New *Ready To Send* state
        """

    @abstractmethod
    async def get_hangup(self) -> bool:
        """
        Retrieve current *Hangup on Close* state.

        Returns:
            Current *Hangup on Close* state
        """

    @abstractmethod
    async def set_hangup(self, value: bool) -> None:
        """
        Set *Hangup on Close* state.

        Args:
            value: New *Hangup on Close* state
        """

    @abstractmethod
    async def _recv(self, max_bytes: Optional[int]) -> ByteString:
        """
        Retrieve up to :py:obj:`max_bytes` bytes from the serial port.
        This function may return zero bytes, but it still MUST try to block until data is
        actually available.

        Returns:
            Received data
        """

    @abstractmethod
    async def _wait_writable(self) -> None:
        """
        Wait until serial port is writable.
        """

    @abstractmethod
    async def _send(self, data: memoryview) -> int:
        """
        Send :py:obj:`data` to the serial port. Partial writes are allowed.

        Args:
            data: Bytes to write.

        Returns:
            Number of bytes actually written.
        """
