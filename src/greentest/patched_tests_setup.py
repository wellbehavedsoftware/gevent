# pylint:disable=missing-docstring,invalid-name
from __future__ import print_function
import sys
import os
import re

# By default, test cases are expected to switch and emit warnings if there was none
# If a test is found in this list, it's expected not to switch.
no_switch_tests = '''test_patched_select.SelectTestCase.test_error_conditions
test_patched_ftplib.*.test_all_errors
test_patched_ftplib.*.test_getwelcome
test_patched_ftplib.*.test_sanitize
test_patched_ftplib.*.test_set_pasv
#test_patched_ftplib.TestIPv6Environment.test_af
test_patched_socket.TestExceptions.testExceptionTree
test_patched_socket.Urllib2FileobjectTest.testClose
test_patched_socket.TestLinuxAbstractNamespace.testLinuxAbstractNamespace
test_patched_socket.TestLinuxAbstractNamespace.testMaxName
test_patched_socket.TestLinuxAbstractNamespace.testNameOverflow
test_patched_socket.FileObjectInterruptedTestCase.*
test_patched_urllib.*
test_patched_asyncore.HelperFunctionTests.*
test_patched_httplib.BasicTest.*
test_patched_httplib.HTTPSTimeoutTest.test_attributes
test_patched_httplib.HeaderTests.*
test_patched_httplib.OfflineTest.*
test_patched_httplib.HTTPSTimeoutTest.test_host_port
test_patched_httplib.SourceAddressTest.testHTTPSConnectionSourceAddress
test_patched_select.SelectTestCase.test_error_conditions
test_patched_smtplib.NonConnectingTests.*
test_patched_urllib2net.OtherNetworkTests.*
test_patched_wsgiref.*
test_patched_subprocess.HelperFunctionTests.*
'''

ignore_switch_tests = '''
test_patched_socket.GeneralModuleTests.*
test_patched_httpservers.BaseHTTPRequestHandlerTestCase.*
test_patched_queue.*
test_patched_signal.SiginterruptTest.*
test_patched_urllib2.*
test_patched_ssl.*
test_patched_signal.BasicSignalTests.*
test_patched_threading_local.*
test_patched_threading.*
'''


def make_re(tests):
    tests = [x.strip().replace(r'\.', r'\\.').replace('*', '.*?')
             for x in tests.split('\n') if x.strip()]
    return re.compile('^%s$' % '|'.join(tests))


no_switch_tests = make_re(no_switch_tests)
ignore_switch_tests = make_re(ignore_switch_tests)


def get_switch_expected(fullname):
    """
    >>> get_switch_expected('test_patched_select.SelectTestCase.test_error_conditions')
    False
    >>> get_switch_expected('test_patched_socket.GeneralModuleTests.testCrucialConstants')
    False
    >>> get_switch_expected('test_patched_socket.SomeOtherTest.testHello')
    True
    >>> get_switch_expected("test_patched_httplib.BasicTest.test_bad_status_repr")
    False
    """
    # certain pylint versions mistype the globals as
    # str, not re.
    # pylint:disable=no-member
    if ignore_switch_tests.match(fullname) is not None:
        return None
    if no_switch_tests.match(fullname) is not None:
        return False
    return True


disabled_tests = [
    # The server side takes awhile to shut down
    'test_httplib.HTTPSTest.test_local_bad_hostname',

    'test_threading.ThreadTests.test_PyThreadState_SetAsyncExc',
    # uses some internal C API of threads not available when threads are emulated with greenlets

    'test_threading.ThreadTests.test_join_nondaemon_on_shutdown',
    # asserts that repr(sleep) is '<built-in function sleep>'

    'test_urllib2net.TimeoutTest.test_ftp_no_timeout',
    'test_urllib2net.TimeoutTest.test_ftp_timeout',
    'test_urllib2net.TimeoutTest.test_http_no_timeout',
    'test_urllib2net.TimeoutTest.test_http_timeout',
    # accesses _sock.gettimeout() which is always in non-blocking mode

    'test_urllib2net.OtherNetworkTests.test_ftp',
    # too slow

    'test_urllib2net.OtherNetworkTests.test_urlwithfrag',
    # fails dues to some changes on python.org

    'test_urllib2net.OtherNetworkTests.test_sites_no_connection_close',
    # flaky

    'test_socket.UDPTimeoutTest.testUDPTimeout',
    # has a bug which makes it fail with error: (107, 'Transport endpoint is not connected')
    # (it creates a TCP socket, not UDP)

    'test_socket.GeneralModuleTests.testRefCountGetNameInfo',
    # fails with "socket.getnameinfo loses a reference" while the reference is only "lost"
    # because it is referenced by the traceback - any Python function would lose a reference like that.
    # the original getnameinfo does not "lose" it because it's in C.

    'test_socket.NetworkConnectionNoServer.test_create_connection_timeout',
    # replaces socket.socket with MockSocket and then calls create_connection.
    # this unfortunately does not work with monkey patching, because gevent.socket.create_connection
    # is bound to gevent.socket.socket and updating socket.socket does not affect it.
    # this issues also manifests itself when not monkey patching DNS: http://code.google.com/p/gevent/issues/detail?id=54
    # create_connection still uses gevent.socket.getaddrinfo while it should be using socket.getaddrinfo

    'test_asyncore.BaseTestAPI.test_handle_expt',
    # sends some OOB data and expect it to be detected as such; gevent.select.select does not support that

    'test_signal.WakeupSignalTests.test_wakeup_fd_early',
    # expects time.sleep() to return prematurely in case of a signal;
    # gevent.sleep() is better than that and does not get interrupted (unless signal handler raises an error)

    'test_signal.WakeupSignalTests.test_wakeup_fd_during',
    # expects select.select() to raise select.error(EINTR'interrupted system call')
    # gevent.select.select() does not get interrupted (unless signal handler raises an error)
    # maybe it should?

    'test_signal.SiginterruptTest.test_without_siginterrupt',
    'test_signal.SiginterruptTest.test_siginterrupt_on',
    # these rely on os.read raising EINTR which never happens with gevent.os.read

    'test_subprocess.test_leak_fast_process_del_killed',
    'test_subprocess.test_zombie_fast_process_del',
    # relies on subprocess._active which we don't use

    'test_ssl.ThreadedTests.test_default_ciphers',
    'test_ssl.ThreadedTests.test_empty_cert',
    'test_ssl.ThreadedTests.test_malformed_cert',
    'test_ssl.ThreadedTests.test_malformed_key',
    'test_ssl.NetworkedTests.test_non_blocking_connect_ex',
    # XXX needs investigating

    'test_ssl.NetworkedTests.test_algorithms',
    # The host this wants to use, sha256.tbs-internet.com, is not resolvable
    # right now (2015-10-10), and we need to get Windows wheels

    # Relies on the repr of objects (Py3)
    'test_ssl.BasicSocketTests.test_dealloc_warn',

    'test_urllib2.HandlerTests.test_cookie_redirect',
    # this uses cookielib which we don't care about

    'test_thread.ThreadRunningTests.test__count',
    'test_thread.TestForkInThread.test_forkinthread',
    # XXX needs investigating

    'test_subprocess.POSIXProcessTestCase.test_terminate_dead',
    'test_subprocess.POSIXProcessTestCase.test_send_signal_dead',
    'test_subprocess.POSIXProcessTestCase.test_kill_dead',
    # Don't exist in the test suite until 2.7.4+; with our monkey patch in place,
    # they fail because the process they're looking for has been allowed to exit.
    # Our monkey patch waits for the process with a watcher and so detects
    # the exit before the normal polling mechanism would

    'test_subprocess.POSIXProcessTestCase.test_preexec_errpipe_does_not_double_close_pipes',
    # Does not exist in the test suite until 2.7.4+. Subclasses Popen, and overrides
    # _execute_child. But our version has a different parameter list than the
    # version that comes with PyPy/CPython, so fails with a TypeError.
]

if 'thread' in os.getenv('GEVENT_FILE', ''):
    disabled_tests += [
        'test_subprocess.ProcessTestCase.test_double_close_on_error'
        # Fails with "OSError: 9 invalid file descriptor"; expect GC/lifetime issues
    ]

if os.getenv('GEVENT_CORE_CFFI_ONLY') == 'libuv':
    disabled_tests += [
        # A 2.7 test. Tries to fork, and libuv cannot fork
        'test_signal.InterProcessSignalTests.test_main',
        # Likewise, a forking problem
        'test_signal.SiginterruptTest.test_siginterrupt_off',
    ]


if sys.version_info[:3] <= (2, 7, 8):

    disabled_tests += [
        # SSLv2 May or may not be available depending on the build
        'test_ssl.BasicTests.test_constants',
        'test_ssl.ThreadedTests.test_protocol_sslv23',
        'test_ssl.ThreadedTests.test_protocol_sslv3',
        'test_ssl.ThreadedTests.test_protocol_tlsv1',
    ]

    # Our 2.7 tests are from 2.7.11 so all the new SSLContext stuff
    # has to go.
    disabled_tests += [
        'test_ftplib.TestTLS_FTPClass.test_check_hostname',
        'test_ftplib.TestTLS_FTPClass.test_context',

        'test_urllib2.TrivialTests.test_cafile_and_context',
        'test_urllib2_localnet.TestUrlopen.test_https',
        'test_urllib2_localnet.TestUrlopen.test_https_sni',
        'test_urllib2_localnet.TestUrlopen.test_https_with_cadefault',
        'test_urllib2_localnet.TestUrlopen.test_https_with_cafile',

        'test_httplib.HTTPTest.testHTTPWithConnectHostPort',
        'test_httplib.HTTPSTest.test_local_good_hostname',
        'test_httplib.HTTPSTest.test_local_unknown_cert',
        'test_httplib.HTTPSTest.test_networked_bad_cert',
        'test_httplib.HTTPSTest.test_networked_good_cert',
        'test_httplib.HTTPSTest.test_networked_noverification',
        'test_httplib.HTTPSTest.test_networked',
    ]

    # Except for test_ssl, which is from 2.7.8. But it has some certificate problems
    # due to age
    disabled_tests += [
        'test_ssl.NetworkedTests.test_connect',
        'test_ssl.NetworkedTests.test_connect_ex',
        'test_ssl.NetworkedTests.test_get_server_certificate',

        # XXX: Not sure
        'test_ssl.BasicSocketTests.test_unsupported_dtls',
    ]

    # These are also bugs fixed more recently
    disabled_tests += [
        'test_httpservers.CGIHTTPServerTestCase.test_nested_cgi_path_issue21323',
        'test_httpservers.CGIHTTPServerTestCase.test_query_with_continuous_slashes',
        'test_httpservers.CGIHTTPServerTestCase.test_query_with_multiple_question_mark',

        'test_socket.GeneralModuleTests.test_weakref__sock',

        'test_threading.ThreadingExceptionTests.test_print_exception_stderr_is_none_1',
        'test_threading.ThreadingExceptionTests.test_print_exception_stderr_is_none_2',

        'test_wsgiref.IntegrationTests.test_request_length',

        'test_httplib.HeaderTests.test_content_length_0',
        'test_httplib.HeaderTests.test_invalid_headers',
        'test_httplib.HeaderTests.test_malformed_headers_coped_with',
        'test_httplib.BasicTest.test_error_leak',
        'test_httplib.BasicTest.test_too_many_headers',
        'test_httplib.BasicTest.test_proxy_tunnel_without_status_line',
        'test_httplib.TunnelTests.test_connect',

        'test_smtplib.TooLongLineTests.testLineTooLong',
        'test_smtplib.SMTPSimTests.test_quit_resets_greeting',

        # features in test_support not available
        'test_threading_local.ThreadLocalTests.test_derived',
        'test_threading_local.PyThreadingLocalTests.test_derived',
        'test_urllib.UtilityTests.test_toBytes',
        'test_httplib.HTTPSTest.test_networked_trusted_by_default_cert',
    ]


    # somehow these fail with "Permission denied" on travis
    disabled_tests += [
        'test_httpservers.CGIHTTPServerTestCase.test_post',
        'test_httpservers.CGIHTTPServerTestCase.test_headers_and_content',
        'test_httpservers.CGIHTTPServerTestCase.test_authorization',
        'test_httpservers.SimpleHTTPServerTestCase.test_get'
    ]


if sys.platform == 'darwin':
    disabled_tests += [
        'test_subprocess.POSIXProcessTestCase.test_run_abort',
        # causes Mac OS X to show "Python crashes" dialog box which is annoying
    ]

if sys.platform.startswith('win'):
    disabled_tests += [
        # Issue with Unix vs DOS newlines in the file vs from the server
        'test_ssl.ThreadedTests.test_socketserver',
    ]

if hasattr(sys, 'pypy_version_info'):
    disabled_tests += [
        'test_subprocess.ProcessTestCase.test_failed_child_execute_fd_leak',
        # Does not exist in the CPython test suite, tests for a specific bug
        # in PyPy's forking. Only runs on linux and is specific to the PyPy
        # implementation of subprocess (possibly explains the extra parameter to
        # _execut_child)
    ]

    import cffi # pylint:disable=import-error,useless-suppression
    if cffi.__version_info__ < (1, 2, 0):
        disabled_tests += [
            'test_signal.InterProcessSignalTests.test_main',
            # Fails to get the signal to the correct handler due to
            # https://bitbucket.org/cffi/cffi/issue/152/handling-errors-from-signal-handlers-in
        ]

# Generic Python 3

if sys.version_info[0] == 3:

    disabled_tests += [
        # Triggers the crash reporter
        'test_threading.SubinterpThreadingTests.test_daemon_threads_fatal_error',

        # Relies on an implementation detail, Thread._tstate_lock
        'test_threading.ThreadTests.test_tstate_lock',
        # Relies on an implementation detail (reprs); we have our own version
        'test_threading.ThreadTests.test_various_ops',
        'test_threading.ThreadTests.test_various_ops_large_stack',
        'test_threading.ThreadTests.test_various_ops_small_stack',

        # Relies on Event having a _cond and an _reset_internal_locks()
        # XXX: These are commented out in the source code of test_threading because
        # this doesn't work.
        # 'lock_tests.EventTests.test_reset_internal_locks',

        # Python bug 13502. We may or may not suffer from this as its
        # basically a timing race condition.
        # XXX Same as above
        # 'lock_tests.EventTests.test_set_and_clear',

    ]

if sys.version_info[:2] == (3, 4) and sys.version_info[:3] < (3, 4, 4):
    # Older versions have some issues with the SSL tests. Seen on Appveyor
    disabled_tests += [
        'test_ssl.ContextTests.test_options',
        'test_ssl.ThreadedTests.test_protocol_sslv23',
        'test_ssl.ThreadedTests.test_protocol_sslv3',
        'test_httplib.HTTPSTest.test_networked',
    ]

if sys.version_info[:2] >= (3, 4):
    disabled_tests += [
        'test_subprocess.ProcessTestCase.test_threadsafe_wait',
        # XXX: It seems that threading.Timer is not being greened properly, possibly
        # due to a similar issue to what gevent.threading documents for normal threads.
        # In any event, this test hangs forever

        'test_subprocess.ProcessTestCase.test_io_buffered_by_default',
        'test_subprocess.ProcessTestCase.test_io_unbuffered_works',
        # These tests want to assert on the type of the class that implements
        # `Popen.stdin`; we use a FileObject, but they expect different subclasses
        # from the `io` module

        'test_subprocess.POSIXProcessTestCase.test_terminate_dead',
        'test_subprocess.POSIXProcessTestCase.test_send_signal_dead',
        'test_subprocess.POSIXProcessTestCase.test_kill_dead',
        # With our monkey patch in place,
        # they fail because the process they're looking for has been allowed to exit.
        # Our monkey patch waits for the process with a watcher and so detects
        # the exit before the normal polling mechanism would

        'test_subprocess.POSIXProcessTestCase.test_exception_bad_args_0',
        'test_subprocess.POSIXProcessTestCase.test_exception_bad_executable',
        'test_subprocess.POSIXProcessTestCase.test_exception_cwd',
        # These all want to inspect the string value of an exception raised
        # by the exec() call in the child. The _posixsubprocess module arranges
        # for better exception handling and printing than we do.

        'test_subprocess.POSIXProcessTestCase.test_preexec_errpipe_does_not_double_close_pipes',
        # Subclasses Popen, and overrides _execute_child. Expects things to be done
        # in a particular order in an exception case, but we don't follow that
        # exact order

        'test_subprocess.POSIXProcessTestCase.test_small_errpipe_write_fd',
        # Python 3 fixed a bug if the stdio file descriptors were closed;
        # we still have that bug

        'test_selectors.PollSelectorTestCase.test_above_fd_setsize',
        # This test attempts to open many many file descriptors and
        # poll on them, expecting them all to be ready at once. But
        # libev limits the number of events it will return at once. Specifically,
        # on linux with epoll, it returns a max of 64 (ev_epoll.c).

        # XXX: Hangs (Linux only)
        'test_socket.NonBlockingTCPTests.testInitNonBlocking',
        # We don't handle the Linux-only SOCK_NONBLOCK option
        'test_socket.NonblockConstantTest.test_SOCK_NONBLOCK',

        # Tries to use multiprocessing which doesn't quite work in
        # monkey_test module (Windows only)
        'test_socket.TestSocketSharing.testShare',

        # Windows-only: Sockets have a 'ioctl' method in Python 3
        # implemented in the C code. This test tries to check
        # for the presence of the method in the class, which we don't
        # have because we don't inherit the C implementation. But
        # it should be found at runtime.
        'test_socket.GeneralModuleTests.test_sock_ioctl',

        # Relies on implementation details
        'test_socket.GeneralModuleTests.test_SocketType_is_socketobject',
        'test_socket.GeneralModuleTests.test_dealloc_warn',
        'test_socket.GeneralModuleTests.test_repr',
        'test_socket.GeneralModuleTests.test_str_for_enums',
        'test_socket.GeneralModuleTests.testGetaddrinfo',

    ]

    if sys.platform == 'darwin':
        disabled_tests += [
            # These raise "OSError: 12 Cannot allocate memory" on both
            # patched and unpatched runs
            'test_socket.RecvmsgSCMRightsStreamTest.testFDPassEmpty',
        ]

    if sys.version_info[:2] == (3, 4):
        disabled_tests += [
            # These are all expecting that a signal (sigalarm) that
            # arrives during a blocking call should raise
            # InterruptedError with errno=EINTR. gevent does not do
            # this, instead its loop keeps going and raises a timeout
            # (which fails the test). HOWEVER: Python 3.5 fixed this
            # problem and started raising a timeout,
            # (https://docs.python.org/3/whatsnew/3.5.html#pep-475-retry-system-calls-failing-with-eintr)
            # and removed these tests (InterruptedError is no longer
            # raised). So basically, gevent was ahead of its time.
            'test_socket.InterruptedRecvTimeoutTest.testInterruptedRecvIntoTimeout',
            'test_socket.InterruptedRecvTimeoutTest.testInterruptedRecvTimeout',
            'test_socket.InterruptedRecvTimeoutTest.testInterruptedRecvfromIntoTimeout',
            'test_socket.InterruptedRecvTimeoutTest.testInterruptedRecvfromTimeout',
            'test_socket.InterruptedRecvTimeoutTest.testInterruptedSendTimeout',
            'test_socket.InterruptedRecvTimeoutTest.testInterruptedSendtoTimeout',
            'test_socket.InterruptedRecvTimeoutTest.testInterruptedRecvmsgTimeout',
            'test_socket.InterruptedRecvTimeoutTest.testInterruptedRecvmsgIntoTimeout',
            'test_socket.InterruptedSendTimeoutTest.testInterruptedSendmsgTimeout',
        ]

    if os.environ.get('TRAVIS') == 'true':
        disabled_tests += [
            'test_subprocess.ProcessTestCase.test_double_close_on_error',
            # This test is racy or OS-dependent. It passes locally (sufficiently fast machine)
            # but fails under Travis
        ]

if sys.version_info[:2] >= (3, 5):
    disabled_tests += [
        # XXX: Hangs
        'test_ssl.ThreadedTests.test_nonblocking_send',
        'test_ssl.ThreadedTests.test_socketserver',
        # Relies on the regex of the repr having the locked state (TODO: it'd be nice if
        # we did that).
        # XXX: These are commented out in the source code of test_threading because
        # this doesn't work.
        # 'lock_tests.LockTests.lest_locked_repr',
        # 'lock_tests.LockTests.lest_repr',

    ]

    if os.environ.get('GEVENT_RESOLVER') == 'ares':
        disabled_tests += [
            # These raise different errors or can't resolve
            # the IP address correctly
            'test_socket.GeneralModuleTests.test_host_resolution',
            'test_socket.GeneralModuleTests.test_getnameinfo',
        ]

# if 'signalfd' in os.environ.get('GEVENT_BACKEND', ''):
#     # tests that don't interact well with signalfd
#     disabled_tests.extend([
#         'test_signal.SiginterruptTest.test_siginterrupt_off',
#         'test_socketserver.SocketServerTest.test_ForkingTCPServer',
#         'test_socketserver.SocketServerTest.test_ForkingUDPServer',
#         'test_socketserver.SocketServerTest.test_ForkingUnixStreamServer'])


def disable_tests_in_source(source, name):
    if name.startswith('./'):
        # turn "./test_socket.py" (used for auto-complete) into "test_socket.py"
        name = name[2:]

    my_disabled_tests = [x for x in disabled_tests if x.startswith(name + '.')]
    if not my_disabled_tests:
        return source
    for test in my_disabled_tests:
        # XXX ignoring TestCase class name
        testcase = test.split('.')[-1]
        source, n = re.subn(testcase, 'XXX' + testcase, source)
        print('Removed %s (%d)' % (testcase, n), file=sys.stderr)

    return source
