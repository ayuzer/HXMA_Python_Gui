# System imports
# import threading
import time

# Library imports
from PyQt4 import QtCore

class EmitterWorker(QtCore.QObject):
    """
    Worker that runs in dedicated thread and emits
    signals on behalf of clients
    """
    def __init__(self, *args, **kwargs):
        """
        Initialize this worker
        """
        super(EmitterWorker, self).__init__(*args, **kwargs)

        # This is the signal from the Emitter to this worker that
        # triggers processing of the queued client signals.
        self.signal = None

        # List of queued client signals
        self.signal_queue = []

    def set_signal(self, signal):
        self.signal = signal

    def queue(self, signal, value):
        """
        Queue a signal (and value) on behalf of client as a tuple.
        Note that this particular method is called in the context of the
        client thread.  However we do net need to lock access to this
        list as signals (and handlers) are thread-safe.
        """
        self.signal_queue.append((signal, value))

    def started_handler(self):
        """
        This handler is called when the worker thread starts.
        """
        self.signal.connect(self.signal_handler)

    def signal_handler(self, value):
        """
        Handler that responds to the Emitter class's SIGNAL.  This handler
        pops queued signals and emits them
        """

        # print "EMITTER_WORKER: signal_handler called", value, threading.currentThread()

        while True:
            if not self.signal_queue:
                break

            item = self.signal_queue.pop(0)

            # print "EMITTER WORKER: item:", item
            # The queued signal is a tuple.  item[0] is the signal itself,
            # item[1] is the value to be emitted in the signal
            if not item[0]:
                continue
            # print "EMITTER WORKER emitting signal", item[1]
            item[0].emit(item[1])


class Emitter(QtCore.QObject):
    """
    The Emitter is a class that creates an independent thread
    for emitting signals.

    This ensures that if a thread sends a signal to
    itself, the signal is processes asynchronously.

    Without the emitter, a thread sending a signal to itself calls the
    handler in a nested (potentially recursive) fashion.
    """

    # Signal used to trigger (i.e., call) the handler in the emitter's
    # worker thread.
    SIGNAL = QtCore.pyqtSignal(unicode)

    def __init__(self, *args, **kwargs):

        super(Emitter, self).__init__(*args, **kwargs)

        self.thread = QtCore.QThread()
        self.worker = EmitterWorker()
        self.worker.set_signal(self.SIGNAL)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.started_handler)
        self.thread.start()


    def emit(self, signal, value):

        #print "EMITTER: emitting a signal: %s %s" % (
        #    value, threading.currentThread())

        # First, queue the signal (and value) to ultimately be emitted
        self.worker.queue(signal, value)

        # Signal the worker thread.... its handler will pop the
        # queued signals and emit them.
        self.SIGNAL.emit("future_value")

    def stop(self):

        print "EMITTER: stop() called"
        if self.thread:
            self.thread.quit()
            while True:
                if self.thread.isFinished():
                    break
                print "EMITTER: Waiting for thread to finish..."
                time.sleep(0.2)
            self.thread = None
