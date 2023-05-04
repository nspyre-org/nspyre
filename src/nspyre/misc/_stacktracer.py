"""Stack tracer for multi-threaded applications.

From: https://code.activestate.com/recipes/577334-how-to-debug-deadlocked-multi-threaded-programs/

Usage:

from nspyre.misc._stacktracer import trace_start, trace_stop

...

trace_start('trace.html', interval=1)
app.exec()
trace_stop()

"""
import os
import sys
import threading
import time
import traceback

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

_tracer = None


def stacktraces():

    # TODO TEST
    for thread in threading.enumerate(): 
        print(thread.name)
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# ThreadID: %s" % threadId)
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))

    return highlight(
        "\n".join(code),
        PythonLexer(),
        HtmlFormatter(
            full=False,
            # style="native",
            noclasses=True,
        ),
    )


class TraceDumper(threading.Thread):
    """Dump stack traces into a given file periodically."""

    def __init__(self, fpath, interval, auto):
        """
        Args:
            fpath: File path to output HTML (stack trace file)
            auto: Set flag (True) to update trace continuously.
                Clear flag (False) to update only if file not exists.
                (Then delete the file to force update.)
            interval: In seconds: how often to update the trace file.
        """
        assert interval > 0.1
        self.auto = auto
        self.interval = interval
        self.fpath = os.path.abspath(fpath)
        self.stop_requested = threading.Event()
        threading.Thread.__init__(self)

    def run(self):
        while not self.stop_requested.isSet():
            time.sleep(self.interval)
            if self.auto or not os.path.isfile(self.fpath):
                self.stacktraces()

    def stop(self):
        self.stop_requested.set()
        self.join()
        if os.path.isfile(self.fpath):
            os.unlink(self.fpath)

    def stacktraces(self):
        with open(self.fpath, 'w+') as fout:
            fout.write(stacktraces())


def trace_start(fpath, interval=5, auto=True):
    """Start tracing into the given file."""
    global _tracer
    if _tracer is None:
        _tracer = TraceDumper(fpath, interval, auto)
        _tracer.setDaemon(True)
        _tracer.start()
    else:
        raise Exception("Already tracing to %s" % _tracer.fpath)


def trace_stop():
    """Stop tracing."""
    global _tracer
    if _tracer is None:
        raise Exception("Not tracing, cannot stop.")
    else:
        _tracer.stop()
        _tracer = None
