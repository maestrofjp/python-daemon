# -*- coding: utf-8 -*-

# Copyright © 2007–2009 Robert Niederreiter, Jens Klein, Ben Finney
# Copyright © 2003 Clark Evans
# Copyright © 2002 Noah Spurrier
# Copyright © 2001 Jürgen Hermann
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

import os
import sys
import time
import resource
import errno
import signal


def prevent_core_dump():
    """ Prevent this process from generating a core dump.

        Sets the soft and hard limits for core dump size to zero. On
        Unix, this prevents the process from creating core dump
        altogether.

        """
    core_resource = resource.RLIMIT_CORE

    # Ensure the resource limit exists on this platform, by requesting
    # its current value
    core_limit_prev = resource.getrlimit(core_resource)

    # Set hard and soft limits to zero, i.e. no core dump at all
    core_limit = (0, 0)
    resource.setrlimit(core_resource, core_limit)


def detach_process_context():
    """ Detach the process context from parent and session.

        Detach from the parent process and session group, allowing the
        parent to exit while this process continues running.

        Reference: “Advanced Programming in the Unix Environment”,
        section 13.3, by W. Richard Stevens, published 1993 by
        Addison-Wesley.
    
        """
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError, e:
        msg = "fork #1 failed: (%d) %s\n" % (e.errno, e.strerror)
        sys.stderr.write(msg)
        sys.exit(1)

    os.setsid()

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError, e:
        msg = "fork #2 failed: (%d) %s\n" % (e.errno, e.strerror)
        sys.stderr.write(msg)
        sys.exit(1)


def redirect_stream(system_stream, target_stream):
    """ Redirect a system stream to a specified file.

        `system_stream` is a standard system stream such as
        ``sys.stdout``. `target_stream` is an open file object that
        should replace the corresponding system stream object.

        """
    os.dup2(target_stream.fileno(), system_stream.fileno())


class DaemonContext(object):
    """ Context for turning the current program into a daemon process.

        Implements the well-behaved daemon behaviour defined in PEP
        [no number yet].

        """
    
    """Class Daemon is used to run any routine in the background on unix
    environments as daemon.
    
    There are several things to consider:
    
    * The instance object MUST provide global file descriptors for
      (and named as):
        -stdin
        -stdout
        -stderr
    
    * The instance object MUST provide a global (and named as) pidfile.
    """

    UMASK = 0
    WORKDIR = "."
    startmsg = 'started with pid %s'

    def __init__(
        self,
        pidfile=None,
        stdin=None,
        stdout=None,
        stderr=None,
        ):
        self.pidfile = pidfile
        self.pidlockfile = self.pidfile
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def start(self):
        """ Become a daemon process. """
        if self.pidlockfile is not None:
            if self.pidlockfile.is_locked():
                pidfile_path = self.pidlockfile.path
                error = SystemExit(
                    "PID file %(pidfile_path)r already locked"
                    % vars())
                raise error

        detach_process_context()

        os.chdir(self.WORKDIR)
        os.umask(self.UMASK)

        prevent_core_dump()

        if not self.stderr:
            self.stderr = self.stdout

        pid = str(os.getpid())

        sys.stderr.write("\n%s\n" % self.startmsg % pid)
        sys.stderr.flush()

        if self.pidlockfile is not None:
            self.pidlockfile.acquire()

        redirect_stream(sys.stdin, self.stdin)
        redirect_stream(sys.stdout, self.stdout)
        redirect_stream(sys.stderr, self.stderr)

    def stop(self):
        """ Stop the running daemon process. """
        if self.pidlockfile is None:
            exception = SystemExit()
            raise exception

        else:
            if not self.pidlockfile.is_locked():
                pidfile_path = self.pidlockfile.path
                error = SystemExit(
                    "PID file %(pidfile_path)r not locked"
                    % vars())
                raise error

            pid = self.pidlockfile.read_pid()
            self.pidlockfile.release()
            os.kill(pid, signal.SIGTERM)

    def startstop(self):
        """Start/stop/restart behaviour.
        """
        if len(sys.argv) > 1:
            action = sys.argv[1]
            if 'stop' == action:
                self.stop()
                sys.exit(0)
                return
            if 'start' == action:
                self.start()
                return
            if 'restart' == action:
                self.stop()
                self.start()
                return
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
