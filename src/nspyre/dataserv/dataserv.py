"""
The DataServer asynchronously serves data to a set of network clients. Data 
is pushed to the server, serialized into binary data, then diffed with any 
previously pushed data. The diff is then sent to all of the clients rather 
than the full object in order to minimize the required network bandwidth. 
The client can then reconstruct the pushed data on the other side.

Author: Jacob Feder
Date: 11/24/2020
"""

# TODO logger.debug original error for except: statements

import pickle
import difflib
import socket
import logging
import copy
import xdelta3
from threading import Thread, Lock, Event
import queue
import time
from typing import List

logger = logging.getLogger(__name__)

# length (bytes) of the header section that identifies how large the payload is
HEADER_MSG_LEN = 8
# length (bytes) of the header section that carries meta-data
HEADER_METADATA_LEN = 8

# if no data is available, any socket sender should send an empty message with an
# interval given by KEEPALIVE
KEEPALIVE = 10000
# general timeout (s) for data source / sink connections
TIMEOUT = KEEPALIVE + 1.0

# indicates that the client is requesting some data about the server
NEGOTIATION_INFO = b'\xDE'
# TODO
# NEGOTIATION_CMD = b'\xAD'
# indicates that the client will source data to the server
NEGOTIATION_SOURCE = b'\xBE'
# indicates that the client will accept data from the server
NEGOTIATION_SINK = b'\xEF'
# timeout (s) for send/recv operations during the client negotiation phase
NEGOTIATION_TIMEOUT = TIMEOUT

# indicates that the payload data is a delta
SINK_DATA_TYPE_DELTA_UNPADDED = b'\xAB'
SINK_DATA_TYPE_DELTA = SINK_DATA_TYPE_DELTA_UNPADDED + b'\x00' * (HEADER_METADATA_LEN - len(SINK_DATA_TYPE_DELTA_UNPADDED))
# indicates that the payload data is a raw pickle
SINK_DATA_TYPE_PICKLE_UNPADDED = b'\xCD'
SINK_DATA_TYPE_PICKLE = SINK_DATA_TYPE_PICKLE_UNPADDED + b'\x00' * (HEADER_METADATA_LEN - len(SINK_DATA_TYPE_PICKLE_UNPADDED))

# generic fast timeout period (s) for waiting operations
FAST_TIMEOUT = 0.1

# maximum size of the data queues
QUEUE_SIZE = 5

# custom recv_msg() and send_msg() use the following packet structure
# |                      HEADER                             | PAYLOAD
# | message length (excluding header) |      meta-data      | message
# |        HEADER_MSG_LEN             | HEADER_METADATA_LEN | variable length

def recv_msg(sock: socket.socket) -> tuple:
    """Receive a message through a socket by decoding the header then reading 
    the rest of the message"""

    # the header bytes we receive from the client should identify
    # the length of the message payload
    msg_len_bytes = sock.recv(HEADER_MSG_LEN)
    msg_len = int.from_bytes(msg_len_bytes, byteorder='little')
    
    # get the metadata
    meta_data = sock.recv(HEADER_METADATA_LEN)
    
    # get the payload
    msg = sock.recv(msg_len)

    # confirm data was actually received
    if len(msg_len_bytes) == 0 or len(meta_data) == 0 or (len(msg) == 0 and msg_len != 0):
        # the connection has closed
        raise BrokenPipeError

    logger.debug(f'{sock.getsockname()} recv: [{msg_len_bytes + meta_data + msg}]')

    return (msg, meta_data)

def send_msg(sock: socket.socket, msg: bytes, meta_data: bytes=b'\x00'*HEADER_METADATA_LEN):
    """Send a byte message through a socket interface by encoding the header 
    then sending the rest of the message"""
    
    assert len(meta_data) == HEADER_METADATA_LEN
    
    # calculate the payload length and package it into bytes
    msg_len_bytes = len(msg).to_bytes(HEADER_MSG_LEN, byteorder='little')
    
    # send the header + payload
    sock.sendall(msg_len_bytes + meta_data + msg)
    
    logger.debug(f'{sock.getsockname()} sent: [{msg_len_bytes + meta_data + msg}]')

class FIFOProcessor():
    """A class for transferring data to/from a queue"""
    def __init__(self):
        # FIFO for data that will be sent/received from the socket connection
        self.queue = queue.Queue(maxsize=QUEUE_SIZE)
        # mutex for protecting access to self.queue while it's being emptied
        self.mutex = Lock()
        # set to False to stop the data processing thread
        self.enabled = False
        # data processing thread for sending/receiving data to/from the socket
        self.thread = Thread(target=self._thread_fun)

    def start(self):
        """Start the data processing thread"""
        self.enabled = True
        self.thread.start()

    def stop_async(self):
        """Stop the data processing thread without waiting for it to finish"""
        self.enabled = False

    def stop(self):
        """Stop the data processing thread and wait for it to finish"""
        self.stop_async()
        # wait until thread exits
        self.thread.join()

    def put_nowait(self, obj):
        """Put an item onto the queue without blocking"""
        self.queue.put_nowait(obj)
        logger.debug(f'[{self}] put obj [{obj}] on queue')

    def get(self, block: bool=True, timeout: float=None):
        """Get an item from the queue"""
        self.mutex.acquire()
        try:
            obj = self.queue.get(block=block, timeout=timeout)
            logger.debug(f'[{self}] got obj [{obj}] from queue')
        except Exception as err:
            # make sure the mutex is released before reraising the error
            self.mutex.release()
            raise err
        self.mutex.release()
        return obj

    def get_nowait(self):
        """Get an item from the queue without blocking"""
        return self.get(block=False)

    def flush_and_put(self, obj=None):
        """Empty the queue then put obj on it"""
        self.mutex.acquire()
        # flush
        for i in range(QUEUE_SIZE):
            self.queue.get_nowait()
        # put the obj on
        if obj:
            self.queue.put_nowait(obj)
        self.mutex.release()
        logger.debug(f'[{self}] flushed and put obj [{obj}] on queue')

    def _thread_fun(self):
        """Override me"""
        pass

class DataServer():
    """The server has an array of DataSet objects. Each has 1 DataSourceClient,
    and unlimited DataSinkClient. Pickled object data from the source is received
    by the DataSourceClient, then transferred to the DataSet object. The DataSet 
    runs a diff algorithm (xdelta3) with the new data and previous data (if 
    available) to generate a 'delta'. If the data is stale for some reason and
    sending a delta is not possible, a raw pickle is used. The delta/pickle is 
    then transferred to each DataSinkClient, and transmitted to the corresponding 
    sockets by the DataSinkClient.

    DataSourceClient    |           DataSet         |   DataSinkClient(s)
                        |                           |
                        |                    -----> |   FIFO --------> socket
                        |                   /       |
    socket ------> FIFO | -----> diff ----> ------> |   FIFO --------> socket
                        |                   \       |
                        |                    -----> |   FIFO --------> socket
    """

    class DataSourceClient(FIFOProcessor):
        def __init__(self, conn: socket.socket):
            super().__init__()
            # socket connection
            self.conn = conn

        """Represents a client connection within the server that sources data"""
        def _thread_fun(self):
            """Thread that waits for data to be received from the source client
            then pushes it to the DataSet processor"""
            self.conn.settimeout(TIMEOUT)
            while self.enabled:
                try:
                    new_pickle,_ = recv_msg(self.conn)
                except:
                    # if there was a timeout / problem receiving the message
                    # the source client is dead and will be terminated
                    logger.warning(f'client [{self.conn.getsockname()}] hasn\'t sent any data or keepalive message - dropping connection')
                    self.stop_async()
                    continue

                if len(new_pickle):
                    try:
                        self.put_nowait(new_pickle)
                    except queue.Full:
                        # the DataSet processor thread isn't consuming data fast enough
                        # so we will empty the queue and place only this most recent
                        # piece of data on it
                        logger.debug(f'client [{self.conn.getsockname()}] dataset processor can\'t keep up with data source')
                        self.flush_and_put(new_pickle)
                else:
                    # the server just sent a keepalive signal
                    pass
            self.conn.close()

    class DataSet():
        """Class that wraps a whole pipeline consisting of a data source,
        the data itself, and a list of data sinks"""
        def __init__(self, name: str, source):
            # identifying name for this dataset
            self.name = name
            # DataSourceClient object
            self.source = source
            # most recent data (bytes)
            self.last_pickle = None
            # list of DataSinkClient objects
            self.sinks = []
            # set to False to stop the data processing thread
            self.enabled = False
            # thread for processing data coming from the source and distributing
            # it to the clients
            self.thread = Thread(target=self._thread_fun)

        def start(self):
            """Start the data processing thread"""
            self.enabled = True
            self.thread.start()

        def stop_async(self):
            """Kill the processing thread, and all sub-processing threads as well
            (source and sinks)"""
            self.enabled = False

        def add_sink(self, sink):
            """Add a new sink client to receive data updates from the source"""
            if self.last_pickle:
                # first the sink needs the full most recent pickle
                sink.put_nowait((SINK_DATA_TYPE_PICKLE, self.last_pickle))
            self.sinks.append(sink)

        def _thread_fun(self):
            """Thread that diffs the data coming from the source, then
            puts it into the queues of the data sinks"""
            while self.enabled:
                # wait until new data is available
                while self.enabled:
                    if self.source:
                        if self.source.enabled:
                            try:
                                # try to get new data from it
                                new_pickle = self.source.get(timeout=FAST_TIMEOUT)
                                break
                            except queue.Empty:
                                pass
                        else:
                            # the data source has recently disconnected
                            logger.debug(f'dataset [{self.name}] source disconnected')
                            self.source = None
                    else:
                        time.sleep(FAST_TIMEOUT)
                if not self.enabled:
                    # the dataset has been stopped
                    break

                if self.last_pickle:
                    # diff the new data
                    delta = xdelta3.encode(self.last_pickle, new_pickle)
                else:
                    delta = None

                # distribute the data to the sinks
                for idx, sink in enumerate(self.sinks):
                    if sink.enabled:
                        try:
                            if (delta is None) or (len(delta) > len(new_pickle)):
                                # in some cases we want to send the full pickle
                                # data instead of the delta
                                #   1. this is the first piece of data pushed to the server, so there is nothing to take a diff against
                                #   2. the delta would be larger than the pickle data
                                sink.put_nowait((SINK_DATA_TYPE_PICKLE, new_pickle))
                            else:
                                # the client already has a previous pickle of the object
                                # so we can just send the delta
                                sink.put_nowait((SINK_DATA_TYPE_DELTA, delta))
                        except queue.Full:
                            # the client isn't consuming data fast enough so we will
                            # empty the queue and send the pickled object
                            logger.debug(f'client [{sink.conn.getsockname()}] can\'t keep up with data source - resending full data')
                            sink.flush_and_put((SINK_DATA_TYPE_PICKLE, new_pickle))
                    else:
                        # prune dead clients
                        self.sinks.pop(idx)

                self.last_pickle = new_pickle

            logger.debug(f'dropping dataset [{self.name}]')

            # clean up all of the threads
            if self.source:
                self.source.stop_async()
            for sink in self.sinks:
                sink.stop_async()

    class DataSinkClient(FIFOProcessor):
        """Represents a client connection within the server that is a data sink"""
        def __init__(self, conn: socket.socket):
            super().__init__()
            # socket connection
            self.conn = conn

        def _thread_fun(self):
            """Thread that pops data from the queue and sends it to the sink client"""
            self.conn.settimeout(TIMEOUT)
            while self.enabled:
                try:
                    data_type, new_data = self.get(timeout=KEEPALIVE)
                except queue.Empty:
                    # this will send a keepalive message
                    data_type = b'\x00'*HEADER_METADATA_LEN
                    new_data = b''

                try:
                    send_msg(self.conn, new_data, meta_data=data_type)
                except:
                    # if there was a timeout / problem sending the message
                    # the sink client is dead and will be terminated
                    logger.warning(f'client [{self.conn.getsockname()}] didn\'t accept message - dropping connection')
                    self.stop_async()
            self.conn.close()

    def __init__(self, port: int):
        """port: TCP/IP port of the data server"""
        self.port = port
        # a dictionary with string identifiers mapping to DataSet objects
        self.datasets = {}
        # set to false to kill all of the threads
        self.enabled = False
        # start the server
        self.thread = Thread(target=self._connect_thread)
        self.start()

    def start(self):
        """Start the data processing thread"""
        self.enabled = True
        self.thread.start()

    def stop_async(self):
        """Kill the whole data server"""
        logging.debug(f'stopping server...')
        self.enabled = False

    def stop(self):
        """Stop the data processing thread and wait for it to finish"""
        self.stop_async()
        # wait until thread exits
        self.thread.join()

    def _connect_thread(self):
        """Thread that waits for clients to connect in a loop. On connection,
        a thread is spawned to handle further interaction"""

        # Create a TCP/IP socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # allow POSIX OSes to immediately reuse sockets previously bound
            # to the same address
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # timeout for accept()
            sock.settimeout(FAST_TIMEOUT)
            # accept connections from anywhere
            sock.bind( ('', self.port) )
            # listen for incoming client connections
            sock.listen(10)
            logger.info(f'started data server on port [{self.port}]')
            while self.enabled:
                # wait until a client tries to connect
                try:
                    conn, addr = sock.accept()
                except socket.timeout:
                    continue
                # spawn a thread to deal with it
                negotiation_thread = Thread(target=self._negotiation_thread,
                                            args=(conn,))
                negotiation_thread.start()

            # kill each dataset
            for dataset_name in self.datasets:
                self.datasets[dataset_name].stop_async()

    def _negotiation_thread(self, conn: socket.socket):
        """Thread that determines what kind of client has connected, and deal
        with it accordingly"""
        logger.info(f'new client connection from {conn.getsockname()}')
        conn.settimeout(NEGOTIATION_TIMEOUT)
        try:
            # the first message we receive from the client should identify
            # what kind of client it is
            client_type,_ = recv_msg(conn)
        except:
            logger.warning(f'connection with client [{conn.getsockname()}] failed before it '
                        'identified itself during the negotiation phase')
            conn.close()
            return

        # info client
        if client_type == NEGOTIATION_INFO:
            logger.info(f'client [{conn.getsockname()}] is type [info]')
            # the client is requesting general info about the server
            try:
                # tell the client which datasets are available
                data = ','.join(list(self.datasets.keys())).encode()
                send_msg(conn, data)
            except:
                logger.warning(f'failed sending server data to [info] client [{conn.getsockname()}]')
            conn.close()

        # data source client
        elif client_type == NEGOTIATION_SOURCE:
            logger.info(f'client [{conn.getsockname()}] is type [source]')
            # the client will be a data source for a dataset on the server
            # first we need know which dataset it will provide data for
            try:
                dataset_name,_ = recv_msg(conn)
                dataset_name = dataset_name.decode()
            except:
                logger.warning(f'failed getting the dataset name from client [{conn.getsockname()}]')
                conn.close()
                return

            if dataset_name in self.datasets:
                # the server already contains a dataset with this name
                if self.datasets[dataset_name].source:
                    # the dataset already has a source
                    logger.warning(f'client [{conn.getsockname()}] wants to source data '
                        f'for dataset [{dataset_name}], but it already has a source '
                        f'[{self.datasets[dataset_name].source.conn.getsockname()}] - dropping connection')
                    conn.close()
                    return
                else:
                    logger.info(f'client [{conn.getsockname()}] sourcing data for already existing dataset [{dataset_name}]')
                    # the dataset exists and it's original source is gone, so the client
                    # will act as the new source
                    data_src = self.DataSourceClient(conn)
                    data_src.start()
                    self.datasets[dataset_name].source = data_src
            else:
                # the dataset isn't already present on the server, so we will create a new one
                logger.info(f'client [{conn.getsockname()}] sourcing data for new dataset [{dataset_name}]')
                data_src = self.DataSourceClient(conn)
                dataset = self.DataSet(dataset_name, data_src)
                data_src.start()
                dataset.start()
                self.datasets[dataset_name] = dataset

        # data sink client
        elif client_type == NEGOTIATION_SINK:
            logger.info(f'client [{conn.getsockname()}] is type [sink]')
            # get the dataset name
            try:
                dataset_name,_ = recv_msg(conn)
                dataset_name = dataset_name.decode()
            except:
                logger.warning(f'failed getting the dataset name from client [{conn.getsockname()}]')
                conn.close()
                return

            if dataset_name in self.datasets:
                # add the client to the sinks for the requested dataset
                logger.info(f'client [{conn.getsockname()}] sinking data from dataset [{dataset_name}]')
                data_sink = self.DataSinkClient(conn)
                data_sink.start()
                self.datasets[dataset_name].add_sink(data_sink)
            else:
                # the requested dataset isn't available on the server
                logger.warning(f'client [{conn.getsockname()}] wants to sink data from dataset [{dataset_name}], but it doesn\'t exist - dropping connection')
                conn.close()
                return
        # unknown client type
        else:
            # the client gave an invalid connection type
            logger.error(f'client [{conn.getsockname()}] provided an invalid connection type [{client_type}] - dropping connection')
            conn.close()
            return

class DataSource(FIFOProcessor):
    """For sourcing data to a DataServer"""
    def __init__(self, name: str, addr: str, port: int):
        super().__init__()
        # name of the dataset
        self.name = name
        # IP address of the server to connect to
        self.addr = addr
        # TCP/IP port of the data server to connect to
        self.port = port
        self.start()

    def _thread_fun(self):
        """Data processing thread for sending data to the server"""
        while self.enabled:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # allow POSIX OSes to immediately reuse sockets previously bound
                # to the same address
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # connect to the DataServer
                sock.settimeout(TIMEOUT)
                try:
                    sock.connect((self.addr, self.port))
                except:
                    logger.warning(f'source couldn\'t reach server [{self.addr}] - retrying...')
                    time.sleep(FAST_TIMEOUT)
                    continue

                try:
                    # notify the server that this is a data source client
                    send_msg(sock, NEGOTIATION_SOURCE)
                    # send the dataset name to source
                    send_msg(sock, self.name.encode())
                except:
                    logger.warning(f'failed initializing source connection with server [{self.addr}] - retrying...')
                    time.sleep(FAST_TIMEOUT)
                    continue

                # retrieve data from the queue and send it to the server
                while self.enabled:
                    # retrieve data from the queue
                    try:
                        new_pickle = self.get(timeout=KEEPALIVE)
                    except queue.Empty:
                        # this will send a keepalive message
                        new_pickle = b''

                    # send the data over the socket
                    try:
                        send_msg(sock, new_pickle)
                    except:
                        # if there was a timeout / problem sending the message
                        # the server couldn't be reached
                        logger.warning(f'server [{self.addr}] didn\'t accept message - dropping connection')
                        break

    def serialize(self, obj):
        """Serialize a python object into a byte stream"""
        return pickle.dumps(obj)

    def push(self, obj):
        """Serialize and send an object to the server"""
        logger.debug(f'pushing object [{obj}]')
        # serialize the object
        new_pickle = self.serialize(obj)
        # put it on the queue
        try:
            self.put_nowait(new_pickle)
        except queue.Full:
            # the server isn't consuming data fast enough so we will empty the 
            # queue and place only this most recent piece of data on it
            logger.debug(f'server [{self.addr}] can\'t keep up with data source')
            self.flush_and_put(new_pickle)

class DataSink(FIFOProcessor):
    """For sinking data from a DataServer"""
    def __init__(self, name: str, addr: str, port: int):
        super().__init__()
        # name of the dataset
        self.name = name
        # IP address of the server to connect to
        self.addr = addr
        # TCP/IP port of the data server to connect to
        self.port = port
        # most recent version of the object as serialized raw bytes
        self.last_pickle = None
        self.start()

    def deserialize(self, obj_bytes):
        """Deserialize a python object from a byte stream"""
        return pickle.loads(obj_bytes)

    def _thread_fun(self):
        """Data processing thread for receiving data from the server"""
        while self.enabled:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # allow POSIX OSes to immediately reuse sockets previously bound
                # to the same address
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # connect to the DataServer
                sock.settimeout(TIMEOUT)
                try:
                    sock.connect((self.addr, self.port))
                except:
                    logger.warning(f'sink couldn\'t reach server [{self.addr}] - retrying...')
                    time.sleep(FAST_TIMEOUT)
                    continue

                try:
                    # notify the server that this is a data sink client
                    send_msg(sock, NEGOTIATION_SINK)
                    # send the dataset name to sink
                    send_msg(sock, self.name.encode())
                except:
                    logger.warning(f'failed initializing sink connection with server [{self.addr}] - retrying...')
                    time.sleep(FAST_TIMEOUT)
                    continue

                while self.enabled:
                    # retrieve data from the server
                    try:
                        new_data, meta_data = recv_msg(sock)
                    except:
                        # if there was a timeout / problem receiving the message
                        # the source client is dead and will be terminated
                        logger.warning(f'server [{self.addr}] hasn\'t sent any data or keepalive message - dropping connection')
                        break

                    if len(new_data):
                        # unpack the data if necessary by using the delta
                        # generated by xdelta3
                        if meta_data == SINK_DATA_TYPE_DELTA:
                            # the server sent a delta, so we have to decode it first
                            new_pickle = xdelta3.decode(self.last_pickle, new_data)
                        elif meta_data == SINK_DATA_TYPE_PICKLE:
                            # the server sent the raw pickle data
                            new_pickle = new_data
                        else:
                            # the server gave an invalid data type
                            logger.error(f'server [{self.addr}] provided an invalid connection type [{meta_data}] - dropping connection')
                            break

                        self.last_pickle = new_pickle

                        try:
                            self.put_nowait(new_pickle)
                        except queue.Full:
                            # the user isn't consuming data fast enough so we will empty the 
                            # queue and place only this most recent piece of data on it
                            logger.debug(f'user code can\'t keep up with data source')
                            self.flush_and_put(new_pickle)
                    else:
                        # the server just sent a keepalive signal
                        pass

    def pop(self, block=True, timeout=None):
        """retrieve a reconstructed object from the queue"""
        new_pickle = self.get(block=block, timeout=timeout)
        obj = self.deserialize(new_pickle)
        logger.debug(f'popping object [{obj}]')
        return obj
