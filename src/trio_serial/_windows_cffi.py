"""
Originally Copied from Trio & extended.

Copyright Contributors to the Trio project.

The MIT License (MIT)

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
from __future__ import annotations

import enum
import re
from typing import TYPE_CHECKING, NewType, Protocol, cast

if TYPE_CHECKING:
    from typing_extensions import NoReturn, TypeAlias

import cffi

################################################################
# Functions and types
################################################################

LIB = """
// https://msdn.microsoft.com/en-us/library/windows/desktop/aa383751(v=vs.85).aspx
typedef int BOOL;
typedef unsigned char BYTE;
typedef BYTE BOOLEAN;
typedef void* PVOID;
typedef PVOID HANDLE;
typedef unsigned long DWORD;
typedef unsigned long ULONG;
typedef unsigned int NTSTATUS;
typedef unsigned long u_long;
typedef ULONG *PULONG;
typedef const void *LPCVOID;
typedef void *LPVOID;
typedef const wchar_t *LPCWSTR;

typedef uintptr_t ULONG_PTR;
typedef uintptr_t UINT_PTR;

typedef UINT_PTR SOCKET;

typedef struct _OVERLAPPED {
    ULONG_PTR Internal;
    ULONG_PTR InternalHigh;
    union {
        struct {
            DWORD Offset;
            DWORD OffsetHigh;
        } DUMMYSTRUCTNAME;
        PVOID Pointer;
    } DUMMYUNIONNAME;

    HANDLE  hEvent;
} OVERLAPPED, *LPOVERLAPPED;

typedef OVERLAPPED WSAOVERLAPPED;
typedef LPOVERLAPPED LPWSAOVERLAPPED;
typedef PVOID LPSECURITY_ATTRIBUTES;
typedef PVOID LPCSTR;

typedef struct _OVERLAPPED_ENTRY {
    ULONG_PTR lpCompletionKey;
    LPOVERLAPPED lpOverlapped;
    ULONG_PTR Internal;
    DWORD dwNumberOfBytesTransferred;
} OVERLAPPED_ENTRY, *LPOVERLAPPED_ENTRY;

// kernel32.dll
HANDLE WINAPI CreateIoCompletionPort(
  _In_     HANDLE    FileHandle,
  _In_opt_ HANDLE    ExistingCompletionPort,
  _In_     ULONG_PTR CompletionKey,
  _In_     DWORD     NumberOfConcurrentThreads
);

BOOL SetFileCompletionNotificationModes(
  HANDLE FileHandle,
  UCHAR  Flags
);

HANDLE CreateFileW(
  LPCWSTR               lpFileName,
  DWORD                 dwDesiredAccess,
  DWORD                 dwShareMode,
  LPSECURITY_ATTRIBUTES lpSecurityAttributes,
  DWORD                 dwCreationDisposition,
  DWORD                 dwFlagsAndAttributes,
  HANDLE                hTemplateFile
);

BOOL WINAPI CloseHandle(
  _In_ HANDLE hObject
);

BOOL WINAPI PostQueuedCompletionStatus(
  _In_     HANDLE       CompletionPort,
  _In_     DWORD        dwNumberOfBytesTransferred,
  _In_     ULONG_PTR    dwCompletionKey,
  _In_opt_ LPOVERLAPPED lpOverlapped
);

BOOL WINAPI GetQueuedCompletionStatusEx(
  _In_  HANDLE             CompletionPort,
  _Out_ LPOVERLAPPED_ENTRY lpCompletionPortEntries,
  _In_  ULONG              ulCount,
  _Out_ PULONG             ulNumEntriesRemoved,
  _In_  DWORD              dwMilliseconds,
  _In_  BOOL               fAlertable
);

BOOL WINAPI CancelIoEx(
  _In_     HANDLE       hFile,
  _In_opt_ LPOVERLAPPED lpOverlapped
);

BOOL WriteFile(
  HANDLE       hFile,
  LPCVOID      lpBuffer,
  DWORD        nNumberOfBytesToWrite,
  LPDWORD      lpNumberOfBytesWritten,
  LPOVERLAPPED lpOverlapped
);

BOOL ReadFile(
  HANDLE       hFile,
  LPVOID       lpBuffer,
  DWORD        nNumberOfBytesToRead,
  LPDWORD      lpNumberOfBytesRead,
  LPOVERLAPPED lpOverlapped
);

BOOL WINAPI SetConsoleCtrlHandler(
  _In_opt_ void*            HandlerRoutine,
  _In_     BOOL             Add
);

HANDLE CreateEventA(
  LPSECURITY_ATTRIBUTES lpEventAttributes,
  BOOL                  bManualReset,
  BOOL                  bInitialState,
  LPCSTR                lpName
);

BOOL SetEvent(
  HANDLE hEvent
);

BOOL ResetEvent(
  HANDLE hEvent
);

DWORD WaitForSingleObject(
  HANDLE hHandle,
  DWORD  dwMilliseconds
);

DWORD WaitForMultipleObjects(
  DWORD        nCount,
  HANDLE       *lpHandles,
  BOOL         bWaitAll,
  DWORD        dwMilliseconds
);

ULONG RtlNtStatusToDosError(
  NTSTATUS Status
);

int WSAIoctl(
  SOCKET                             s,
  DWORD                              dwIoControlCode,
  LPVOID                             lpvInBuffer,
  DWORD                              cbInBuffer,
  LPVOID                             lpvOutBuffer,
  DWORD                              cbOutBuffer,
  LPDWORD                            lpcbBytesReturned,
  LPWSAOVERLAPPED                    lpOverlapped,
  // actually LPWSAOVERLAPPED_COMPLETION_ROUTINE
  void* lpCompletionRoutine
);

int WSAGetLastError();

BOOL DeviceIoControl(
  HANDLE       hDevice,
  DWORD        dwIoControlCode,
  LPVOID       lpInBuffer,
  DWORD        nInBufferSize,
  LPVOID       lpOutBuffer,
  DWORD        nOutBufferSize,
  LPDWORD      lpBytesReturned,
  LPOVERLAPPED lpOverlapped
);

// From https://github.com/piscisaureus/wepoll/blob/master/src/afd.h
typedef struct _AFD_POLL_HANDLE_INFO {
  HANDLE Handle;
  ULONG Events;
  NTSTATUS Status;
} AFD_POLL_HANDLE_INFO, *PAFD_POLL_HANDLE_INFO;

// This is really defined as a messy union to allow stuff like
// i.DUMMYSTRUCTNAME.LowPart, but we don't need those complications.
// Under all that it's just an int64.
typedef int64_t LARGE_INTEGER;

typedef struct _AFD_POLL_INFO {
  LARGE_INTEGER Timeout;
  ULONG NumberOfHandles;
  ULONG Exclusive;
  AFD_POLL_HANDLE_INFO Handles[1];
} AFD_POLL_INFO, *PAFD_POLL_INFO;

typedef struct _COMSTAT {
  DWORD fCtsHold : 1;
  DWORD fDsrHold : 1;
  DWORD fRlsdHold : 1;
  DWORD fXoffHold : 1;
  DWORD fXoffSent : 1;
  DWORD fEof : 1;
  DWORD fTxim : 1;
  DWORD fReserved : 25;
  DWORD cbInQue;
  DWORD cbOutQue;
} COMSTAT, *LPCOMSTAT;

BOOL ClearCommError(
    HANDLE hFile,
    LPDWORD lpErrors,
    LPCOMSTAT lpStat
);

BOOL SetCommMask(
  HANDLE hFile,
  DWORD dwEvtMask
);

BOOL PurgeComm(
    HANDLE hFile,
    DWORD dwFlags
);

BOOL WaitCommEvent(
    HANDLE hFile,
    LPDWORD lpEvtMask,
    LPOVERLAPPED lpOverlapped
);

typedef struct _COMMTIMEOUTS {
  DWORD ReadIntervalTimeout;
  DWORD ReadTotalTimeoutMultiplier;
  DWORD ReadTotalTimeoutConstant;
  DWORD WriteTotalTimeoutMultiplier;
  DWORD WriteTotalTimeoutConstant;
} COMMTIMEOUTS, *LPCOMMTIMEOUTS;

BOOL GetCommTimeouts(
  HANDLE         hFile,
  LPCOMMTIMEOUTS lpCommTimeouts
);

BOOL SetCommTimeouts(
  HANDLE         hFile,
  LPCOMMTIMEOUTS lpCommTimeouts

);

typedef struct _DCB {
  DWORD DCBlength;
  DWORD BaudRate;
  DWORD fBinary : 1;
  DWORD fParity : 1;
  DWORD fOutxCtsFlow : 1;
  DWORD fOutxDsrFlow : 1;
  DWORD fDtrControl : 2;
  DWORD fDsrSensitivity : 1;
  DWORD fTXContinueOnXoff : 1;
  DWORD fOutX : 1;
  DWORD fInX : 1;
  DWORD fErrorChar : 1;
  DWORD fNull : 1;
  DWORD fRtsControl : 2;
  DWORD fAbortOnError : 1;
  DWORD fDummy2 : 17;
  WORD  wReserved;
  WORD  XonLim;
  WORD  XoffLim;
  BYTE  ByteSize;
  BYTE  Parity;
  BYTE  StopBits;
  char  XonChar;
  char  XoffChar;
  char  ErrorChar;
  char  EofChar;
  char  EvtChar;
  WORD  wReserved1;
} DCB, *LPDCB;

BOOL SetCommState(
  HANDLE hFile,
  LPDCB  lpDCB
);

BOOL GetCommState(
  HANDLE hFile,
  LPDCB  lpDCB
);
"""

# cribbed from pywincffi
# programmatically strips out those annotations MSDN likes, like _In_
REGEX_SAL_ANNOTATION = re.compile(r"\b(_In_|_Inout_|_Out_|_Outptr_|_Reserved_)(opt_)?\b")
LIB = REGEX_SAL_ANNOTATION.sub(" ", LIB)

# Other fixups:
# - get rid of FAR, cffi doesn't like it
LIB = re.sub(r"\bFAR\b", " ", LIB)
# - PASCAL is apparently an alias for __stdcall (on modern compilers - modern
#   being _MSC_VER >= 800)
LIB = re.sub(r"\bPASCAL\b", "__stdcall", LIB)

ffi = cffi.api.FFI()
ffi.cdef(LIB)

CData: TypeAlias = cffi.api.FFI.CData
CType: TypeAlias = cffi.api.FFI.CType
AlwaysNull: TypeAlias = CType  # We currently always pass ffi.NULL here.
Handle = NewType("Handle", CData)
HandleArray = NewType("HandleArray", CData)


class _Kernel32(Protocol):
    """Statically typed version of the kernel32.dll functions we use."""

    def CreateIoCompletionPort(
        self,
        FileHandle: Handle,
        ExistingCompletionPort: CData | AlwaysNull,
        CompletionKey: int,
        NumberOfConcurrentThreads: int,
        /,
    ) -> Handle:
        ...

    def CreateEventA(
        self,
        lpEventAttributes: AlwaysNull,
        bManualReset: bool,
        bInitialState: bool,
        lpName: AlwaysNull,
        /,
    ) -> Handle:
        ...

    def SetFileCompletionNotificationModes(
        self, handle: Handle, flags: CompletionModes, /
    ) -> int:
        ...

    def PostQueuedCompletionStatus(
        self,
        CompletionPort: Handle,
        dwNumberOfBytesTransferred: int,
        dwCompletionKey: int,
        lpOverlapped: CData | AlwaysNull,
        /,
    ) -> bool:
        ...

    def CancelIoEx(
        self,
        hFile: Handle,
        lpOverlapped: CData | AlwaysNull,
        /,
    ) -> bool:
        ...

    def WriteFile(
        self,
        hFile: Handle,
        # not sure about this type
        lpBuffer: CData,
        nNumberOfBytesToWrite: int,
        lpNumberOfBytesWritten: AlwaysNull,
        lpOverlapped: _Overlapped,
        /,
    ) -> bool:
        ...

    def ReadFile(
        self,
        hFile: Handle,
        # not sure about this type
        lpBuffer: CData,
        nNumberOfBytesToRead: int,
        lpNumberOfBytesRead: AlwaysNull,
        lpOverlapped: _Overlapped,
        /,
    ) -> bool:
        ...

    def GetQueuedCompletionStatusEx(
        self,
        CompletionPort: Handle,
        lpCompletionPortEntries: CData,
        ulCount: int,
        ulNumEntriesRemoved: CData,
        dwMilliseconds: int,
        fAlertable: bool | int,
        /,
    ) -> CData:
        ...

    def CreateFileW(
        self,
        lpFileName: CData,
        dwDesiredAccess: FileFlags,
        dwShareMode: FileFlags,
        lpSecurityAttributes: AlwaysNull,
        dwCreationDisposition: FileFlags,
        dwFlagsAndAttributes: FileFlags,
        hTemplateFile: AlwaysNull,
        /,
    ) -> Handle:
        ...

    def WaitForSingleObject(self, hHandle: Handle, dwMilliseconds: int, /) -> CData:
        ...

    def WaitForMultipleObjects(
        self,
        nCount: int,
        lpHandles: HandleArray,
        bWaitAll: bool,
        dwMilliseconds: int,
        /,
    ) -> ErrorCodes:
        ...

    def SetEvent(self, handle: Handle, /) -> None:
        ...

    def CloseHandle(self, handle: Handle, /) -> bool:
        ...

    def DeviceIoControl(
        self,
        hDevice: Handle,
        dwIoControlCode: int,
        # this is wrong (it's not always null)
        lpInBuffer: AlwaysNull,
        nInBufferSize: int,
        # this is also wrong
        lpOutBuffer: AlwaysNull,
        nOutBufferSize: int,
        lpBytesReturned: AlwaysNull,
        lpOverlapped: CData,
        /,
    ) -> bool:
        ...

    def SetCommMask(
        self,
        hFile: Handle,
        dwEvtMask: int,
        /,
    ) -> bool:
        ...

    def PurgeComm(
        self,
        hFile: Handle,
        dwFlags: int,
        /,
    ) -> bool:
        ...

    def WaitCommEvent(
        self,
        hFile: Handle,
        lpEvtMask: CData,
        lpOverlapped: CData,
        /,
    ) -> bool:
        ...

    def ClearCommError(
        self,
        hFile: Handle,
        lpErrors: CData,
        lpStat: AlwaysNull,
        /,
    ) -> bool:
        ...

    def GetCommTimeouts(self, hFile: Handle, lpCommTimeouts: CData, /) -> bool:
        ...

    def SetCommTimeouts(self, hFile: Handle, lpCommTimeouts: CData, /) -> bool:
        ...

    def SetCommState(self, hFile: Handle, lpDCB: CData, /) -> bool:
        ...

    def GetCommState(self, hFile: Handle, lpDCB: CData, /) -> bool:
        ...


class _Nt(Protocol):
    """Statically typed version of the dtdll.dll functions we use."""

    def RtlNtStatusToDosError(self, status: int, /) -> ErrorCodes:
        ...


class _Ws2(Protocol):
    """Statically typed version of the ws2_32.dll functions we use."""

    def WSAGetLastError(self) -> int:
        ...

    def WSAIoctl(
        self,
        socket: CData,
        dwIoControlCode: WSAIoctls,
        lpvInBuffer: AlwaysNull,
        cbInBuffer: int,
        lpvOutBuffer: CData,
        cbOutBuffer: int,
        lpcbBytesReturned: CData,  # int*
        lpOverlapped: AlwaysNull,
        # actually LPWSAOVERLAPPED_COMPLETION_ROUTINE
        lpCompletionRoutine: AlwaysNull,
        /,
    ) -> int:
        ...


class _DummyStruct(Protocol):
    Offset: int
    OffsetHigh: int


class _DummyUnion(Protocol):
    DUMMYSTRUCTNAME: _DummyStruct
    Pointer: object


class _Overlapped(Protocol):
    Internal: int
    InternalHigh: int
    DUMMYUNIONNAME: _DummyUnion
    hEvent: Handle


class CommTimeouts:
    ReadIntervalTimeout: int
    ReadTotalTimeoutMultiplier: int
    ReadTotalTimeoutConstant: int
    WriteTotalTimeoutMultiplier: int
    WriteTotalTimeoutConstant: int


kernel32 = cast(_Kernel32, ffi.dlopen("kernel32.dll"))
ntdll = cast(_Nt, ffi.dlopen("ntdll.dll"))
ws2_32 = cast(_Ws2, ffi.dlopen("ws2_32.dll"))

################################################################
# Magic numbers
################################################################

# Here's a great resource for looking these up:
#   https://www.magnumdb.com
# (Tip: check the box to see "Hex value")

INVALID_HANDLE_VALUE = Handle(ffi.cast("HANDLE", -1))


class ErrorCodes(enum.IntEnum):
    STATUS_TIMEOUT = 0x102
    WAIT_TIMEOUT = 0x102
    WAIT_ABANDONED = 0x80
    WAIT_OBJECT_0 = 0x00  # object is signaled
    WAIT_FAILED = 0xFFFFFFFF
    ERROR_IO_PENDING = 997
    ERROR_OPERATION_ABORTED = 995
    ERROR_ABANDONED_WAIT_0 = 735
    ERROR_INVALID_HANDLE = 6
    ERROR_INVALID_PARMETER = 87
    ERROR_NOT_FOUND = 1168
    ERROR_NOT_SOCKET = 10038
    ERROR_TIMEOUT = 1460


class FileFlags(enum.IntFlag):
    GENERIC_READ = 0x80000000
    SYNCHRONIZE = 0x00100000
    FILE_FLAG_OVERLAPPED = 0x40000000
    FILE_SHARE_READ = 1
    FILE_SHARE_WRITE = 2
    FILE_SHARE_DELETE = 4
    CREATE_NEW = 1
    CREATE_ALWAYS = 2
    OPEN_EXISTING = 3
    OPEN_ALWAYS = 4
    TRUNCATE_EXISTING = 5
    GENERIC_WRITE = 0x40000000
    FILE_ATTRIBUTE_NORMAL = 0x00000080


class AFDPollFlags(enum.IntFlag):
    # These are drawn from a combination of:
    #   https://github.com/piscisaureus/wepoll/blob/master/src/afd.h
    #   https://github.com/reactos/reactos/blob/master/sdk/include/reactos/drivers/afd/shared.h
    AFD_POLL_RECEIVE = 0x0001
    AFD_POLL_RECEIVE_EXPEDITED = 0x0002  # OOB/urgent data
    AFD_POLL_SEND = 0x0004
    AFD_POLL_DISCONNECT = 0x0008  # received EOF (FIN)
    AFD_POLL_ABORT = 0x0010  # received RST
    AFD_POLL_LOCAL_CLOSE = 0x0020  # local socket object closed
    AFD_POLL_CONNECT = 0x0040  # socket is successfully connected
    AFD_POLL_ACCEPT = 0x0080  # you can call accept on this socket
    AFD_POLL_CONNECT_FAIL = 0x0100  # connect() terminated unsuccessfully
    # See WSAEventSelect docs for more details on these four:
    AFD_POLL_QOS = 0x0200
    AFD_POLL_GROUP_QOS = 0x0400
    AFD_POLL_ROUTING_INTERFACE_CHANGE = 0x0800
    AFD_POLL_EVENT_ADDRESS_LIST_CHANGE = 0x1000


class WSAIoctls(enum.IntEnum):
    SIO_BASE_HANDLE = 0x48000022
    SIO_BSP_HANDLE_SELECT = 0x4800001C
    SIO_BSP_HANDLE_POLL = 0x4800001D


class CompletionModes(enum.IntFlag):
    FILE_SKIP_COMPLETION_PORT_ON_SUCCESS = 0x1
    FILE_SKIP_SET_EVENT_ON_HANDLE = 0x2


class IoControlCodes(enum.IntEnum):
    IOCTL_AFD_POLL = 0x00012024


class CommEvtMask(enum.IntFlag):
    EV_BREAK = 0x0040
    EV_CTS = 0x0008
    EV_DSR = 0x0010
    EV_ERR = 0x0080
    EV_RING = 0x0100
    EV_RLSD = 0x0020
    EV_RXCHAR = 0x0001
    EV_RXFLAG = 0x0002
    EV_TXEMPTY = 0x0004


class PurgeCommFlags(enum.IntFlag):
    PURGE_RXABORT = 0x0002
    PURGE_RXCLEAR = 0x0008
    PURGE_TXABORT = 0x0001
    PURGE_TXCLEAR = 0x0004


# https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-clearcommerror
class CommErrorFlags(enum.IntFlag):
    CE_BREAK = 0x0010
    CE_FRAME = 0x0008
    CE_OVERRUN = 0x0002
    CE_RXOVER = 0x0001
    CE_RXPARITY = 0x0004


class DcbParity(enum.IntEnum):
    NOPARITY = 0
    ODDPARITY = 1
    EVENPARITY = 2
    MARKPARITY = 3
    SPACEPARITY = 4


# https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-dcb
class Dcb:
    DCBlength: int
    BaudRate: int
    fBinary: int
    fParity: int
    fOutxCtsFlow: int
    fOutxDsrFlow: int
    fDtrControl: int
    fDsrSensitivity: int
    fTXContinueOnXoff: int
    fOutX: int
    fInX: int
    fErrorChar: int
    fNull: int
    fRtsControl: int
    fAbortOnError: int
    fDummy2: int
    wReserved: int
    XonLim: int
    XoffLim: int
    ByteSize: int
    Parity: int
    StopBits: int
    XonChar: int
    XoffChar: int
    ErrorChar: int
    EofChar: int
    EvtChar: int
    wReserved1: int


################################################################
# Generic helpers
################################################################


def _handle(obj: int | CData) -> Handle:
    # For now, represent handles as either cffi HANDLEs or as ints.  If you
    # try to pass in a file descriptor instead, it's not going to work
    # out. (For that msvcrt.get_osfhandle does the trick, but I don't know if
    # we'll actually need that for anything...) For sockets this doesn't
    # matter, Python never allocates an fd. So let's wait until we actually
    # encounter the problem before worrying about it.
    if isinstance(obj, int):
        return Handle(ffi.cast("HANDLE", obj))
    return Handle(obj)


def handle_array(count: int) -> HandleArray:
    """Make an array of handles."""
    return HandleArray(ffi.new(f"HANDLE[{count}]"))


def raise_winerror(
    winerror: int | None = None,
    *,
    filename: str | None = None,
    filename2: str | None = None,
) -> NoReturn:
    # assert sys.platform == "win32"  # TODO: make this work in MyPy
    # ... in the meanwhile, ffi.getwinerror() is undefined on non-Windows, necessitating the type
    # ignores.

    if winerror is None:
        err = ffi.getwinerror()  # type: ignore[attr-defined,unused-ignore]
        if err is None:
            raise RuntimeError("No error set?")
        winerror, msg = err
    else:
        err = ffi.getwinerror(winerror)  # type: ignore[attr-defined,unused-ignore]
        if err is None:
            raise RuntimeError("No error set?")
        _, msg = err
    # https://docs.python.org/3/library/exceptions.html#OSError
    raise OSError(0, msg, filename, winerror, filename2)
