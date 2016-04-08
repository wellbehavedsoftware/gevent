# pylint: disable=too-many-lines, protected-access, redefined-outer-name, not-callable
from __future__ import absolute_import, print_function
import sys

__all__ = [
    'get_version',
    'get_header_version',
    'supported_backends',
    'recommended_backends',
    'embeddable_backends',
    'time',
    'loop',
]

import gevent.libev._corecffi as _corecffi # pylint:disable=no-name-in-module,import-error

ffi = _corecffi.ffi # pylint:disable=no-member
libev = _corecffi.lib # pylint:disable=no-member

if hasattr(libev, 'vfd_open'):
    # Must be on windows
    assert sys.platform.startswith("win"), "vfd functions only needed on windows"
    vfd_open = libev.vfd_open
    vfd_free = libev.vfd_free
    vfd_get = libev.vfd_get
else:
    vfd_open = vfd_free = vfd_get = lambda fd: fd

#####
## NOTE on Windows:
# The C implementation does several things specially for Windows;
# a possibly incomplete list is:
#
# - the loop runs a periodic signal checker;
# - the io watcher constructor is different and it has a destructor;
# - the child watcher is not defined
#
# The CFFI implementation does none of these things, and so
# is possibly NOT FUNCTIONALLY CORRECT on Win32
#####



from gevent._ffi.loop import assign_standard_callbacks
_callbacks = assign_standard_callbacks(ffi, libev)


UNDEF = libev.EV_UNDEF
NONE = libev.EV_NONE
READ = libev.EV_READ
WRITE = libev.EV_WRITE
TIMER = libev.EV_TIMER
PERIODIC = libev.EV_PERIODIC
SIGNAL = libev.EV_SIGNAL
CHILD = libev.EV_CHILD
STAT = libev.EV_STAT
IDLE = libev.EV_IDLE
PREPARE = libev.EV_PREPARE
CHECK = libev.EV_CHECK
EMBED = libev.EV_EMBED
FORK = libev.EV_FORK
CLEANUP = libev.EV_CLEANUP
ASYNC = libev.EV_ASYNC
CUSTOM = libev.EV_CUSTOM
ERROR = libev.EV_ERROR

READWRITE = libev.EV_READ | libev.EV_WRITE

MINPRI = libev.EV_MINPRI
MAXPRI = libev.EV_MAXPRI

BACKEND_PORT = libev.EVBACKEND_PORT
BACKEND_KQUEUE = libev.EVBACKEND_KQUEUE
BACKEND_EPOLL = libev.EVBACKEND_EPOLL
BACKEND_POLL = libev.EVBACKEND_POLL
BACKEND_SELECT = libev.EVBACKEND_SELECT
FORKCHECK = libev.EVFLAG_FORKCHECK
NOINOTIFY = libev.EVFLAG_NOINOTIFY
SIGNALFD = libev.EVFLAG_SIGNALFD
NOSIGMASK = libev.EVFLAG_NOSIGMASK


class _EVENTSType(object):
    def __repr__(self):
        return 'gevent.core.EVENTS'

EVENTS = GEVENT_CORE_EVENTS = _EVENTSType()


def get_version():
    return 'libev-%d.%02d' % (libev.ev_version_major(), libev.ev_version_minor())


def get_header_version():
    return 'libev-%d.%02d' % (libev.EV_VERSION_MAJOR, libev.EV_VERSION_MINOR)

_flags = [(libev.EVBACKEND_PORT, 'port'),
          (libev.EVBACKEND_KQUEUE, 'kqueue'),
          (libev.EVBACKEND_EPOLL, 'epoll'),
          (libev.EVBACKEND_POLL, 'poll'),
          (libev.EVBACKEND_SELECT, 'select'),
          (libev.EVFLAG_NOENV, 'noenv'),
          (libev.EVFLAG_FORKCHECK, 'forkcheck'),
          (libev.EVFLAG_SIGNALFD, 'signalfd'),
          (libev.EVFLAG_NOSIGMASK, 'nosigmask')]

_flags_str2int = dict((string, flag) for (flag, string) in _flags)



def _flags_to_list(flags):
    result = []
    for code, value in _flags:
        if flags & code:
            result.append(value)
        flags &= ~code
        if not flags:
            break
    if flags:
        result.append(flags)
    return result

if sys.version_info[0] >= 3:
    basestring = (bytes, str)
    integer_types = int,
else:
    import __builtin__ # pylint:disable=import-error
    basestring = __builtin__.basestring,
    integer_types = (int, __builtin__.long)


def _flags_to_int(flags):
    # Note, that order does not matter, libev has its own predefined order
    if not flags:
        return 0
    if isinstance(flags, integer_types):
        return flags
    result = 0
    try:
        if isinstance(flags, basestring):
            flags = flags.split(',')
        for value in flags:
            value = value.strip().lower()
            if value:
                result |= _flags_str2int[value]
    except KeyError as ex:
        raise ValueError('Invalid backend or flag: %s\nPossible values: %s' % (ex, ', '.join(sorted(_flags_str2int.keys()))))
    return result


def _str_hex(flag):
    if isinstance(flag, integer_types):
        return hex(flag)
    return str(flag)


def _check_flags(flags):
    as_list = []
    flags &= libev.EVBACKEND_MASK
    if not flags:
        return
    if not flags & libev.EVBACKEND_ALL:
        raise ValueError('Invalid value for backend: 0x%x' % flags)
    if not flags & libev.ev_supported_backends():
        as_list = [_str_hex(x) for x in _flags_to_list(flags)]
        raise ValueError('Unsupported backend: %s' % '|'.join(as_list))


def supported_backends():
    return _flags_to_list(libev.ev_supported_backends())


def recommended_backends():
    return _flags_to_list(libev.ev_recommended_backends())


def embeddable_backends():
    return _flags_to_list(libev.ev_embeddable_backends())


def time():
    return libev.ev_time()

_default_loop_destroyed = False


from gevent._ffi.loop import AbstractLoop

# from gevent.libev.watcher import watcher
# from gevent.libev.watcher import io
# from gevent.libev.watcher import timer
# from gevent.libev.watcher import signal
# from gevent.libev.watcher import idle
# from gevent.libev.watcher import prepare
# from gevent.libev.watcher import check
# from gevent.libev.watcher import fork
# from gevent.libev.watcher import async
# from gevent.libev.watcher import child
# from gevent.libev.watcher import stat

from gevent.libev import watcher as _watchers
_events_to_str = _watchers._events_to_str # exported

class loop(AbstractLoop):
    # pylint:disable=too-many-public-methods

    error_handler = None

    _CHECK_POINTER = 'struct ev_check *'
    _CHECK_CALLBACK_SIG = "void(*)(struct ev_loop *, void*, int)"

    _PREPARE_POINTER = 'struct ev_prepare *'
    _PREPARE_CALLBACK_SIG = "void(*)(struct ev_loop *, void*, int)"

    _TIMER_POINTER = 'struct ev_timer *'

    def __init__(self, flags=None, default=None):
        AbstractLoop.__init__(self, ffi, libev, _watchers, flags, default)

    def _init_loop(self, flags, default):
        c_flags = _flags_to_int(flags)
        _check_flags(c_flags)
        c_flags |= libev.EVFLAG_NOENV
        c_flags |= libev.EVFLAG_FORKCHECK
        if default is None:
            default = True
            if _default_loop_destroyed:
                default = False

        if default:
            ptr = libev.gevent_ev_default_loop(c_flags)
            if not ptr:
                raise SystemError("ev_default_loop(%s) failed" % (c_flags, ))
        else:
            ptr = libev.ev_loop_new(c_flags)
            if not ptr:
                raise SystemError("ev_loop_new(%s) failed" % (c_flags, ))
        if default or globals()["__SYSERR_CALLBACK"] is None:
            set_syserr_cb(self._handle_syserr)

        return ptr

    def _init_and_start_check(self):
        libev.ev_check_init(self._check, self._check_callback_ffi)
        libev.ev_check_start(self._ptr, self._check)
        self.unref()

    def _init_and_start_prepare(self):
        libev.ev_prepare_init(self._prepare, self._prepare_callback_ffi)
        libev.ev_prepare_start(self._ptr, self._prepare)
        self.unref()

    def _init_callback_timer(self):
        libev.ev_timer_init(self._timer0, libev.gevent_noop, 0.0, 0.0)

    def _stop_callback_timer(self):
        libev.ev_timer_stop(self._ptr, self._timer0)

    def _start_callback_timer(self):
        libev.ev_timer_start(self._ptr, self._timer0)

    def _stop_aux_watchers(self):
        if libev.ev_is_active(self._prepare):
            self.ref()
            libev.ev_prepare_stop(self._ptr, self._prepare)
        if libev.ev_is_active(self._check):
            self.ref()
            libev.ev_check_stop(self._ptr, self._check)

    def destroy(self):
        global _default_loop_destroyed
        if self._ptr:
            ptr = self._ptr

            super(loop, self).destroy()

            if globals()["__SYSERR_CALLBACK"] == self._handle_syserr:
                set_syserr_cb(None)
            if libev.ev_is_default_loop(ptr):
                _default_loop_destroyed = True
            libev.ev_loop_destroy(ptr)

    @property
    def MAXPRI(self):
        return libev.EV_MAXPRI

    @property
    def MINPRI(self):
        return libev.EV_MINPRI

    def _default_handle_error(self, context, type, value, tb): # pylint:disable=unused-argument
        super(loop, self)._default_handle_error(context, type, value, tb)
        libev.ev_break(self._ptr, libev.EVBREAK_ONE)

    def run(self, nowait=False, once=False):
        flags = 0
        if nowait:
            flags |= libev.EVRUN_NOWAIT
        if once:
            flags |= libev.EVRUN_ONCE

        libev.ev_run(self._ptr, flags)

    def reinit(self):
        libev.ev_loop_fork(self._ptr)

    def ref(self):
        libev.ev_ref(self._ptr)

    def unref(self):
        libev.ev_unref(self._ptr)

    def break_(self, how=libev.EVBREAK_ONE):
        libev.ev_break(self._ptr, how)

    def verify(self):
        libev.ev_verify(self._ptr)

    def now(self):
        return libev.ev_now(self._ptr)

    def update(self):
        libev.ev_now_update(self._ptr)

    def __repr__(self):
        return '<%s at 0x%x %s>' % (self.__class__.__name__, id(self), self._format())

    @property
    def default(self):
        return True if libev.ev_is_default_loop(self._ptr) else False

    @property
    def iteration(self):
        return libev.ev_iteration(self._ptr)

    @property
    def depth(self):
        return libev.ev_depth(self._ptr)

    @property
    def backend_int(self):
        return libev.ev_backend(self._ptr)

    @property
    def backend(self):
        backend = libev.ev_backend(self._ptr)
        for key, value in _flags:
            if key == backend:
                return value
        return backend

    @property
    def pendingcnt(self):
        return libev.ev_pending_count(self._ptr)

    if sys.platform != "win32":

        def install_sigchld(self):
            libev.gevent_install_sigchld_handler()

    def fileno(self):
        if self._ptr:
            fd = self._ptr.backend_fd
            if fd >= 0:
                return fd

    @property
    def activecnt(self):
        if not self._ptr:
            raise ValueError('operation on destroyed loop')
        return self._ptr.activecnt



def _syserr_cb(msg):
    try:
        msg = ffi.string(msg)
        __SYSERR_CALLBACK(msg, ffi.errno)
    except:
        set_syserr_cb(None)
        raise  # let cffi print the traceback

_syserr_cb._cb = ffi.callback("void(*)(char *msg)", _syserr_cb)


def set_syserr_cb(callback):
    global __SYSERR_CALLBACK
    if callback is None:
        libev.ev_set_syserr_cb(ffi.NULL)
        __SYSERR_CALLBACK = None
    elif callable(callback):
        libev.ev_set_syserr_cb(_syserr_cb._cb)
        __SYSERR_CALLBACK = callback
    else:
        raise TypeError('Expected callable or None, got %r' % (callback, ))

__SYSERR_CALLBACK = None

LIBEV_EMBED = True
