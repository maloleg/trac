# -*- coding: utf-8 -*-
#
# Copyright (C) 2006-2022 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at https://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at https://trac.edgewall.org/log/.

import atexit
import errno
import os
import signal
import sys


def daemonize(pidfile=None, progname=None, stdin='/dev/null',
              stdout='/dev/null', stderr='/dev/null', umask=0o22):
    """Fork a daemon process."""
    if pidfile:
        # Check whether the pid file already exists and refers to a still
        # process running
        pidfile = os.path.abspath(pidfile)
        if os.path.exists(pidfile):
            with open(pidfile, 'rb') as fileobj:
                try:
                    pid = int(fileobj.read())
                except ValueError:
                    sys.exit('Invalid pid in file %s\nPlease remove it to '
                             'proceed' % pidfile)

            try: # signal the process to see if it is still running
                os.kill(pid, 0)
                if not progname:
                    progname = os.path.basename(sys.argv[0])
                sys.exit('%s is already running with pid %s' % (progname, pid))
            except OSError as e:
                if e.errno != errno.ESRCH:
                    raise

        # The pid file must be writable
        try:
            with open(pidfile, 'a+'):
                pass
        except IOError as e:
            from trac.util.text import exception_to_unicode
            sys.exit('Error writing to pid file: %s' % exception_to_unicode(e))

    # Perform first fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0) # exit first parent

    # Decouple from parent environment
    os.chdir('/')
    os.umask(umask)
    os.setsid()

    # Perform second fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0) # exit second parent

    # The process is now daemonized, redirect standard file descriptors
    for stream in sys.stdout, sys.stderr:
        stream.flush()
    stdin = os.open(stdin, os.O_RDONLY)
    stdout = os.open(stdout,  os.O_RDWR | os.O_APPEND)
    stderr = os.open(stderr, os.O_RDWR | os.O_APPEND)
    os.dup2(stdin, sys.stdin.fileno())
    os.dup2(stdout, sys.stdout.fileno())
    os.dup2(stderr, sys.stderr.fileno())
    for fd in stdin, stdout, stderr:
        os.close(fd)

    if pidfile:
        # Register signal handlers to ensure atexit hooks are called on exit
        for signum in [signal.SIGTERM, signal.SIGHUP]:
            signal.signal(signum, handle_signal)

        # Create/update the pid file, and register a hook to remove it when the
        # process exits
        def remove_pidfile():
            if os.path.exists(pidfile):
                os.remove(pidfile)
        atexit.register(remove_pidfile)
        with open(pidfile, 'wb') as fileobj:
            fileobj.write(b'%d' % os.getpid())


def handle_signal(signum, frame):
    """Handle signals sent to the daemonized process."""
    sys.exit()
