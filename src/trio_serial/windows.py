from __future__ import annotations

import array
from typing import ByteString, Dict, Optional

import trio.lowlevel
from trio import ClosedResourceError

from .abstract import AbstractSerialStream, Parity, StopBits
import serial
import ctypes


class WindowsSerialStream(AbstractSerialStream):
    """
    Windows implementation of :py:class:`SerialStream`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # to get started just use a pyserial to open the file and do all the configuration.
        # we reach into the Serial instance to grab is _port_handle
        self._py_serial: serial.Serial | None = None
        self._handle = None
        self._read_buffer = bytearray()

    async def aclose(self) -> None:
        """
        Close the port. Do nothing if already closed.
        """
        self._close(True)

    async def aopen(self) -> None:
        """
        Open the port and configure it with the initial state from :py:method:`__init__`.
        """
        if self._py_serial is None:
            self._py_serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=self._bytesize,
                stopbits=2
                # just use the defaults for now...
                # parity=self._parity.value,
                # stopbits=self._stopbits.value,
                # xonxoff=self._xonxoff,
                # rtscts=self._rtscts,
            )
            self._handle = self._py_serial._port_handle

            timeouts = serial.win32.COMMTIMEOUTS()
            timeouts.ReadIntervalTimeout = 0
            timeouts.ReadTotalTimeoutMultiplier = 0
            timeouts.ReadTotalTimeoutConstant = 0
            serial.win32.SetCommTimeouts(self._handle, ctypes.byref(timeouts))
            trio.lowlevel.register_with_iocp(self._handle)

    def _close(self, notify_closing: bool = False) -> None:
        """
        Close the port. Do nothing if already closed.

        Args:
            notify_closing: We need this for sockets, but not sure what is needed
            for {read,write}_overlapped operations. Need to test/read further.
        """
        if self._py_serial is None:
            return

        py_serial = self._py_serial
        self._py_serial = None
        self._handle = None
        py_serial.close()

    async def discard_input(self) -> None:
        """
        Discard any unread input.
        """
        self._py_serial.reset_input_buffer()

    async def discard_output(self) -> None:
        """
        Discard any unwritten output.
        """
        self._py_serial.reset_input_buffer()

    async def send_break(self, duration: float = 0.25) -> None:
        """
        Transmit a continuous stream of zero-valued bits for a specific duration.

        Params:
            duration: Number of seconds
        """
        # termios.tcsendbreak(self.fd, int(duration / 0.25))

    async def _send(self, data: memoryview) -> int:
        """
        Send :py:obj:`data` to the serial port. Partial writes are allowed.

        Args:
            data: Bytes to write.

        Returns:
            Number of bytes actually written.
        """
        r = await trio.lowlevel.write_overlapped(self._handle, data)
        return r

    async def _wait_writable(self) -> None:
        """
        Wait until serial port is writable.
        """
        # are we always writable? I think so... If not, how to we test if we're writable???
        pass

    async def _recv(self, max_bytes: Optional[int]) -> bytes:
        """
        Retrieve up to :py:obj:`max_bytes` bytes from the serial port.

        Returns:
            Received data
        """
        # The buffer size is used in readinto_overlapped to work out how many
        # bytes to request. We keep a buffer on the stream object so that
        # it doesn't need to be allocated each call, then copy the data
        # out into a bytestring to return it. 4096 is the default buffer size
        # from pyserial. Haven't thought any further about that yet...
        read_size = max_bytes or 4096
        if read_size != len(self._read_buffer):
            self._read_buffer = bytearray(b"\x00" * read_size)

        bytes_read = await trio.lowlevel.readinto_overlapped(self._handle, self._read_buffer)
        return self._read_buffer[:bytes_read]

    async def get_cts(self) -> bool:
        """
        Retrieve current *Clear To Send* state.

        Returns:
            Current CTS state
        """
        # return self._get_bit(BIT_CTS)

    async def get_rts(self) -> bool:
        """
        Retrieve current *Ready To Send* state.

        Returns:
            Current RTS state
        """
        # return self._get_bit(BIT_RTS)

    async def set_rts(self, value: bool) -> None:
        """
        Set *Ready To Send* state.

        Args:
            value: New *Ready To Send* state
        """
        # self._set_bit(BUF_RTS, value)

    async def get_hangup(self) -> bool:
        """
        Retrieve current *Hangup on Close* state.

        Returns:
            Current *Hangup on Close* state
        """
        # return self._hangup_on_close

    async def set_hangup(self, value: bool) -> None:
        """
        Set *Hangup on Close* state.

        Args:
            value: New *Hangup on Close* state
        """
        # self._hangup_on_close = value
        # self._reconfigure_port()

    def _set_bit(self, bit: bytes, value: bool) -> None:
        """
        Set or reset one of the modem bits.

        Args:
            bit: Modem bit constant as byte string
            value: new state
        """
        # if value:
        #     cmd = TIOCMBIS
        # else:
        #     cmd = TIOCMBIC
        #
        # fcntl.ioctl(self.fd, cmd, bit)

    def _get_bit(self, bit: int) -> bool:
        """
        Get one of the modem bits.

        Arg:
            bit: Modem bit constant as integer

        Returns:
            Current state
        """
        # buf = fcntl.ioctl(self.fd, TIOCMGET, BUF_ZERO)
        # value = unpack("@I", buf)[0]
        # return bool(value & bit)

    def _reconfigure_port(self, force_update: bool = False) -> None:
        """
        Set communication parameters on opened port.

        Args:
            force_update: Set the parameters, even if did not change?
        """
        # try:
        #     fd = self.fd
        # except ClosedResourceError:
        #     # Don't try to configure a closed port. Next aopen will configure it.
        #     return
        #
        # # Lock port
        # if self._exclusive:
        #     try:
        #         fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        #     except IOError as ex:
        #         raise IOError(f"Could not exclusively lock port {self._port!r}: {ex!s}") from ex
        # else:
        #     fcntl.flock(fd, fcntl.LOCK_UN)
        #
        # # Retrieve current attributes
        # orig_attr = termios.tcgetattr(fd)
        # iflag, oflag, cflag, lflag, ispeed, ospeed, cc = orig_attr
        #
        # # Set up raw mode / no echo / binary
        # cflag |= termios.CLOCAL | termios.CREAD
        # lflag &= ~(
        #         termios.ICANON
        #         | termios.ECHO
        #         | termios.ECHOE
        #         | termios.ECHOK
        #         | termios.ECHONL
        #         | termios.ISIG
        #         | termios.IEXTEN
        # )
        #
        # # Netbsd workaround for Erk
        # for flag in ("ECHOCTL", "ECHOKE"):
        #     if hasattr(termios, flag):
        #         lflag &= ~getattr(termios, flag)
        #
        # oflag &= ~(termios.OPOST | termios.ONLCR | termios.OCRNL)
        # iflag &= ~(termios.INLCR | termios.IGNCR | termios.ICRNL | termios.IGNBRK)
        #
        # if hasattr(termios, "IUCLC"):
        #     iflag &= ~termios.IUCLC
        #
        # if hasattr(termios, "PARMRK"):
        #     iflag &= ~termios.PARMRK
        #
        # # Setup baud rate
        # custom_baud = False
        # try:
        #     ispeed = ospeed = getattr(termios, f"B{self._baudrate}")
        # except AttributeError:
        #     try:
        #         ispeed = ospeed = self.BAUDRATE_CONSTANTS[self._baudrate]
        #     except KeyError:
        #         # See if BOTHER is defined for this platform; if it is, use
        #         # this for a speed not defined in the baudrate constants list.
        #         try:
        #             ispeed = ospeed = self.BOTHER
        #         except AttributeError:
        #             # may need custom baud rate, it isn't in our list.
        #             ispeed = ospeed = termios.B38400
        #
        #         custom_baud = True
        #
        # # Setup char len
        # cflag &= ~termios.CSIZE
        # try:
        #     cflag |= getattr(termios, f"CS{self._bytesize}")
        # except AttributeError as ex:
        #     raise ValueError(f"Invalid char len: {self._bytesize}") from ex
        #
        # # Setup stop bits
        # if self._stopbits == StopBits.ONE:
        #     cflag &= ~termios.CSTOPB
        # elif self._stopbits == StopBits.ONE_POINT_FIVE:
        #     # XXX same as TWO.. there is no POSIX support for 1.5
        #     cflag |= termios.CSTOPB
        # elif self._stopbits == StopBits.TWO:
        #     cflag |= termios.CSTOPB
        # else:
        #     raise ValueError(f"Invalid stop bit specification: {self._stopbits}")
        #
        # # Setup parity
        # iflag &= ~(termios.INPCK | termios.ISTRIP)
        # if self._parity == Parity.NONE:
        #     cflag &= ~(termios.PARENB | termios.PARODD | self.CMSPAR)
        # elif self._parity == Parity.EVEN:
        #     cflag &= ~(termios.PARODD | self.CMSPAR)
        #     cflag |= termios.PARENB
        # elif self._parity == Parity.ODD:
        #     cflag &= ~self.CMSPAR
        #     cflag |= termios.PARENB | termios.PARODD
        # elif self._parity == Parity.MARK and self.CMSPAR:
        #     cflag |= termios.PARENB | self.CMSPAR | termios.PARODD
        # elif self._parity == Parity.SPACE and self.CMSPAR:
        #     cflag |= termios.PARENB | self.CMSPAR
        #     cflag &= ~(termios.PARODD)
        # else:
        #     raise ValueError(f"Invalid parity: {self._parity}")
        #
        # # Setup XON/XOFF flow control
        # if hasattr(termios, "IXANY"):
        #     if self._xonxoff:
        #         iflag |= termios.IXON | termios.IXOFF  # |termios.IXANY)
        #     else:
        #         iflag &= ~(termios.IXON | termios.IXOFF | termios.IXANY)
        # else:
        #     if self._xonxoff:
        #         iflag |= termios.IXON | termios.IXOFF
        #     else:
        #         iflag &= ~(termios.IXON | termios.IXOFF)
        #
        # # Setup RTS/CTS flow control
        # if hasattr(termios, "CRTSCTS"):
        #     if self._rtscts:
        #         cflag |= termios.CRTSCTS
        #     else:
        #         cflag &= ~(termios.CRTSCTS)
        # elif hasattr(termios, "CNEW_RTSCTS"):  # try it with alternate constant name
        #     if self._rtscts:
        #         cflag |= termios.CNEW_RTSCTS
        #     else:
        #         cflag &= ~(termios.CNEW_RTSCTS)
        #
        # # Setup Hangup on Close
        # if self._hangup_on_close:
        #     cflag |= termios.HUPCL
        # else:
        #     cflag &= ~termios.HUPCL
        #
        # # Use nonblocking operations with no buffers
        # cc[termios.VMIN] = 0
        # cc[termios.VTIME] = 0
        #
        # new_attr = [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
        #
        # if force_update or new_attr != orig_attr:
        #     termios.tcsetattr(fd, termios.TCSANOW, new_attr)
        #
        # # apply custom baud rate, if any
        # if custom_baud:
        #     self._set_special_baudrate(fd)

    def _set_special_baudrate(self, fd: int) -> None:
        """
        Implemented by sub classes
        """
        raise NotImplementedError("Non-standard baudrates are not supported on this platform")
