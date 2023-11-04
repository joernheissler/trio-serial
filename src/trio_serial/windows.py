from __future__ import annotations

from typing import Optional

import trio.lowlevel

from .abstract import AbstractSerialStream, Parity, StopBits

from ._windows_cffi import (
    INVALID_HANDLE_VALUE,
    ErrorCodes,
    FileFlags,
    Handle,
    IoControlCodes,
    WSAIoctls,
    _handle,
    _Overlapped,
    ffi,
    kernel32,
    ntdll,
    raise_winerror,
    ws2_32,
    CommEvtMask,
    CommTimeouts,
    Dcb,
    DcbParity,
)
from typing import cast

# trio's win cffi doesn't define this
GENERIC_WRITE = 0x40000000
FILE_ATTRIBUTE_NORMAL = 0x00000080


def _check(success):
    if not success:
        raise_winerror()
    return success


class WindowsSerialStream(AbstractSerialStream):
    """
    Windows implementation of :py:class:`SerialStream`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

        if self._handle is None:
            rawname_buf = ffi.from_buffer(self._port.encode("utf-16le") + b"\0\0")

            self._handle = kernel32.CreateFileW(
                ffi.cast("LPCWSTR", rawname_buf),
                GENERIC_WRITE | FileFlags.GENERIC_READ,
                0,  # exclusive access
                ffi.NULL,  # no security attributes
                FileFlags.OPEN_EXISTING,
                FileFlags.FILE_FLAG_OVERLAPPED | FILE_ATTRIBUTE_NORMAL,
                ffi.NULL,  # no template file
            )

            if self._handle == INVALID_HANDLE_VALUE:
                raise_winerror()

            _check(kernel32.ClearCommError(self._handle, ffi.NULL, ffi.NULL))
            _check(kernel32.SetCommMask(self._handle, CommEvtMask.EV_ERR))

            timeouts = cast(CommTimeouts, ffi.new("LPCOMMTIMEOUTS"))
            # https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-commtimeouts
            # If an application sets ReadIntervalTimeout and ReadTotalTimeoutMultiplier
            # to MAXDWORD and sets ReadTotalTimeoutConstant to a value greater than
            # zero and less than MAXDWORD, one of the following occurs when the ReadFile
            # function is called:
            # - If there are any bytes in the input buffer, ReadFile returns immediately
            #   with the bytes in the buffer.
            # - If there are no bytes in the input buffer, ReadFile waits until a byte
            #   arrives and then returns immediately.
            # - If no bytes arrive within the time specified by ReadTotalTimeoutConstant,
            #   ReadFile times out.
            #
            # So using that, we loop on a timeout and retry. Even though it's a long
            # with is very unlikely to ever happen in real code.
            timeouts.ReadIntervalTimeout = 0xFFFF_FFFF
            timeouts.ReadTotalTimeoutMultiplier = 0xFFFF_FFFF
            timeouts.ReadTotalTimeoutConstant = 0xFFFF_FFFF - 1  # approx. 49 days...
            timeouts.WriteTotalTimeoutMultiplier = 0
            timeouts.WriteTotalTimeoutConstant = 0
            _check(kernel32.SetCommTimeouts(self._handle, timeouts))

            trio.lowlevel.register_with_iocp(self._handle)

            self._reconfigure_port()

    def _close(self, notify_closing: bool = False) -> None:
        """
        Close the port. Do nothing if already closed.

        Args:
            notify_closing: We need this for sockets, but not sure what is needed
            for {read,write}_overlapped operations. Need to test/read further.
        """
        if self._handle is None:
            return

        handle = self._handle
        self._handle = None
        _check(kernel32.CloseHandle(handle))

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
        while True:
            try:
                bytes_read = await trio.lowlevel.readinto_overlapped(
                    self._handle, self._read_buffer
                )
                break
            except OSError as exc:
                if exc.winerror == ErrorCodes.ERROR_TIMEOUT:
                    print("rx timeout")
                    continue
                raise

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
        if self._handle is None:
            return

        dcb = cast(Dcb, ffi.new("LPDCB"))

        dcb.DCBlength = ffi.sizeof("DCB")
        dcb.BaudRate = self._baudrate
        dcb.fBinary = 1  # must be true
        dcb.fParity = 1 if self._parity == Parity.NONE else 0
        dcb.fOutxCtsFlow = 0  # not implemented
        dcb.fOutxCtsFlow = 0  # not implemented
        dcb.fDtrControl = 0  # not implemented
        dcb.fDsrSensitivity = 0  # not implemented
        dcb.fOutX = 0
        dcb.fInX = 0
        dcb.fErrorChar = 0
        dcb.fNull = 0
        dcb.fRtsControl = 0
        dcb.fAbortOnError = 0
        dcb.fDummy2 = 0
        dcb.wReserved = 0  # must be zero
        dcb.XonLim = 0
        dcb.XoffLim = 0
        dcb.ByteSize = self._bytesize

        if self._parity == Parity.NONE:
            dcb.Parity = DcbParity.NOPARITY
        elif self._parity == Parity.EVEN:
            dcb.Parity = DcbParity.EVENPARITY
        elif self._parity == Parity.ODD:
            dcb.Parity = DcbParity.ODDPARITY
        elif self._parity == Parity.MARK:
            dcb.Parity = DcbParity.MARKPARITY
        elif self._parity == Parity.SPACE:
            dcb.Parity = DcbParity.SPACEPARITY
        else:
            raise ValueError(f"Invalid parity: {self._parity}")

        if self._stopbits == StopBits.ONE:
            dcb.StopBits = 0
        elif self._stopbits == StopBits.ONE_POINT_FIVE:
            dcb.StopBits = 1
        elif self._stopbits == StopBits.TWO:
            dcb.StopBits = 2
        else:
            raise ValueError(f"Invalid stop bit specification: {self._stopbits}")

        dcb.XonChar = b"\x11"
        dcb.XoffChar = b"\x13"
        dcb.ErrorChar = b"\x00"
        dcb.EofChar = b"\x00"
        dcb.EvtChar = b"\x00"
        dcb.wReserved1 = 0

        _check(kernel32.SetCommState(self._handle, dcb))
