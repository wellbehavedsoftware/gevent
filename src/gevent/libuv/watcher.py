# pylint: disable=too-many-lines, protected-access, redefined-outer-name, not-callable
from __future__ import absolute_import, print_function

import gevent.libuv._corecffi as _corecffi # pylint:disable=no-name-in-module,import-error

ffi = _corecffi.ffi # pylint:disable=no-member
libuv = _corecffi.lib # pylint:disable=no-member


from gevent._ffi import watcher as _base

_closing_handles = set()

@ffi.callback("void(*)(uv_handle_t*)")
def _uv_close_callback(handle):
    _closing_handles.remove(handle)


class watcher(_base.watcher):
    _FFI = ffi
    _LIB = libuv

    _watcher_prefix = 'uv'
    _watcher_struct_pattern = '%s_t'
    _watcher_callback_name = '_gevent_generic_callback0'

    def __del__(self):
        # Managing the lifetime of _watcher is tricky.
        # They have to be uv_close()'d, but that only
        # queues them to be closed in the *next* loop iteration.
        # The memory most stay valid for at least that long,
        # or assert errors are triggered. We can't use a ffi.gc()
        # pointer to queue the uv_close, because by the time the
        # destructor is called, there's no way to keep the memory alive
        # and it could be re-used.
        # So here we resort to resurrecting the pointer object out
        # of our scope, keeping it alive past this object's lifetime.
        # We then use the uv_close callback to handle removing that
        # reference. There's no context passed to the closs callback,
        # so we have to do this globally.

        # Sadly, doing this causes crashes if there were multiple
        # watchers for a given FD. See https://github.com/gevent/gevent/issues/790#issuecomment-208076604
        #print("Del", ffi.cast('void*', self._watcher), 'started', libuv.uv_is_active(self._watcher), type(self), id(self))
        #if hasattr(self, '_fd'):
        #    print("FD", self._fd)
        if not libuv.uv_is_closing(self._watcher):
            self._watcher.data = ffi.NULL
            _closing_handles.add(self._watcher)
            libuv.uv_close(self._watcher, _uv_close_callback)
            self._watcher = None

    def _watcher_ffi_set_priority(self, priority):
        # libuv has no concept of priority
        pass

    def _watcher_ffi_init(self, args):
        self._watcher_init(self.loop.ptr,
                           self._watcher,
                           *args)

    def _watcher_ffi_start(self):
        self._watcher_start(self._watcher, self._watcher_callback)

    def _watcher_ffi_stop(self):
        self._watcher_stop(self._watcher)

    def _watcher_ffi_ref(self):
        libuv.uv_ref(self._watcher)

    def _watcher_ffi_unref(self):
        libuv.uv_unref(self._watcher)

    def _watcher_ffi_start_unref(self):
        # libev manipulates these refs at start and stop for
        # some reason; we don't
        pass

    def _watcher_ffi_stop_ref(self):
        pass

    def _get_ref(self):
        # Convert 1/0 to True/False
        return True if libuv.uv_has_ref(self._watcher) else False

    def _set_ref(self, value):
        if value:
            self._watcher_ffi_ref()
        else:
            self._watcher_ffi_unref()

    ref = property(_get_ref, _set_ref)

    def feed(self, _revents, _callback, *_args):
        raise Exception("Not implemented")

class io(_base.IoMixin, watcher):
    _watcher_type = 'poll'
    _watcher_callback_name = '_gevent_poll_callback2'

    EVENT_MASK = libuv.UV_READABLE | libuv.UV_WRITABLE

    def __init__(self, loop, fd, events, ref=True, priority=None):
        super(io, self).__init__(loop, fd, events, ref=ref, priority=priority, _args=(fd,))
        self._fd = fd
        self._events = events

    def _get_fd(self):
        return self._fd

    @_base.not_while_active
    def _set_fd(self, fd):
        self._fd = fd
        self._watcher_ffi_init((fd,))

    def _get_events(self):
        return self._events

    @_base.not_while_active
    def _set_events(self, events):
        self._events = events

    def _watcher_ffi_start(self):
        self._watcher_start(self._watcher, self._events, self._watcher_callback)

class fork(_base.ForkMixin):
    # We'll have to implement this one completely manually

    def __init__(self, *args, **kwargs):
        pass

    def start(self, *args):
        pass

    def stop(self, *args):
        pass

class child(_base.ChildMixin, watcher):
    _watcher_skip_ffi = True
    # We'll have to implement this one completely manually.
    # Our approach is to use a SIGCHLD handler and the original
    # os.waitpid call.

    # On Unix, libuv's uv_process_t and uv_spawn use SIGCHLD,
    # just like libev does for its child watchers. So
    # we're not adding any new SIGCHLD related issues not already
    # present in libev.

    def __init__(self, *args, **kwargs):
        super(child, self).__init__(*args, **kwargs)
        self._async = self.loop.async()

    def _watcher_create(self, _args):
        return

    @property
    def _watcher_handle(self):
        return None

    def _watcher_ffi_init(self, args):
        return

    def start(self, cb, *args):
        self.loop._child_watchers[self._pid].append(self)
        self.callback = cb
        self.args = args
        self._async.start(cb, *args)
        #watcher.start(self, cb, *args)

    @property
    def active(self):
        return self._async.active

    def stop(self):
        try:
            self.loop._child_watchers[self._pid].remove(self)
        except ValueError:
            pass
        self.callback = None
        self.args = None
        self._async.stop()

    def _set_status(self, status):
        self._rstatus = status
        self._async.send()

class async(_base.AsyncMixin, watcher):

    def _watcher_ffi_init(self, args):
        pass

    def _watcher_ffi_start(self):
        self._watcher_init(self.loop.ptr, self._watcher, self._watcher_callback)

    def _watcher_ffi_stop(self):
        self._watcher_init(self.loop.ptr, self._watcher, ffi.NULL)

    def send(self):
        libuv.uv_async_send(self._watcher)

    @property
    def pending(self):
        return None

class timer(_base.TimerMixin, watcher):

    def _update_now(self):
        self.loop.update()

    _again = False

    def _watcher_ffi_init(self, args):
        self._watcher_init(self.loop._ptr, self._watcher)
        self._after, self._repeat = args

    def _watcher_ffi_start(self):
        if self._again:
            libuv.uv_timer_again(self._watcher)
        else:
            self._watcher_start(self._watcher, self._watcher_callback,
                                int(self._after * 1000),
                                int(self._repeat * 1000))

    def again(self, callback, *args, **kw):
        if not self.active:
            # If we've never been started, this is the same as starting us.
            # libuv makes the distinction, libev doesn't.
            self.start(callback, *args, **kw)
            return

        self._again = True
        try:
            self.start(callback, *args, **kw)
        finally:
            del self._again

class stat(_base.StatMixin, watcher):
    _watcher_type = 'fs_poll'
    _watcher_struct_name = 'gevent_fs_poll_t'
    _watcher_callback_name = '_gevent_fs_poll_callback3'

    def _watcher_create(self, ref):
        self._handle = type(self).new_handle(self)
        self._watcher = type(self).new(self._watcher_struct_pointer_type)
        self._watcher.handle.data = self._handle

    def _watcher_ffi_init(self, args):
        self._watcher_init(self.loop._ptr, self._watcher)

    MIN_STAT_INTERVAL = 0.1074891 # match libev; 0.0 is default

    def _watcher_ffi_start(self):
        # libev changes this when the watcher is started
        if self._interval < self.MIN_STAT_INTERVAL:
            self._interval = self.MIN_STAT_INTERVAL
        self._watcher_start(self._watcher, self._watcher_callback,
                            self._cpath,
                            int(self._interval * 1000))

    @property
    def _watcher_handle(self):
        return self._watcher.handle.data

    @property
    def attr(self):
        if not self._watcher.curr.st_nlink:
            return
        return self._watcher.curr

    @property
    def prev(self):
        if not self._watcher.prev.st_nlink:
            return
        return self._watcher.prev

class signal(_base.SignalMixin, watcher):

    _watcher_callback_name = '_gevent_generic_callback1'

    def _watcher_ffi_init(self, args):
        self._watcher_init(self.loop._ptr, self._watcher)
        self.ref = False # libev doesn't ref these by default

    def _watcher_ffi_start(self):
        self._watcher_start(self._watcher, self._watcher_callback,
                            self._signalnum)
