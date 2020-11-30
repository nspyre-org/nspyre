from threading import Thread
import ctypes
import time

class KillTheadException(Exception):
    """ """

class Test():
    """A class for transferring data to/from a queue"""
    def __init__(self):
        # data processing thread for sending/receiving data to/from the socket
        self.thread = Thread(target=self._thread_fun)
        self.thread.start()

    def stop(self):
        """Stop the data processing thread and wait for it to finish"""
        # this asynchronously raises an exception in the thread
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self.thread.ident), 
                                                ctypes.py_object(KillTheadException))
        if res == 0:
            print('fail1')
        elif res > 1:
            print('fail2')
        # wait until thread exits
        self.thread.join()

    def _thread_fun(self):
        """Override me"""
        while True:
            pass
        print('thread exit')


t = Test()
time.sleep(1)
t.stop()