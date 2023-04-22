"""Implement special Pickling functions that can be used for streaming data.
Instead of serializing and deserializing an entire object, pickle operations
will only serialize/deserialize the differences since the most recent pickle.
This can be used to efficiently stream data e.g. over a network connection.
"""
import io
from pickle import dumps
from pickle import loads
from pickle import Pickler
from pickle import Unpickler
from pickle import UnpicklingError
from typing import Any
from typing import Dict

from .streaming_list import StreamingList

# maximum length of a diff
_MAX_DIFF = 10e3


class PickleDiff:
    """Represents a serialized object, where some of sub-objects are special
    streaming-capable objects. For streaming objects, a set of diffs is used
    to reconstruct the object."""

    def __init__(self, pkl: bytes = None, diffs: Dict = None):
        """
        Args:
            pkl: Byte string from pickle operation.
            diffs: Dict where keys are uid and values are lists of diffs as
                dictated by the corresponding class-specific code in
                :py:meth:`~nspyre.data._streaming_pickle.StreamingPickler.persistent_id`.
        """
        if pkl is None:
            self.pkl = b''
        else:
            self.pkl = pkl

        if diffs is None:
            self.diffs = {}
        else:
            self.diffs = diffs

    def squash(self, pd):
        """Merge the given (more recent) PickleDiff into this PickleDiff.

        Args:
            pd: PickleDiff object to squash into this one.
        """
        self.pkl = pd.pkl
        # squashed diff operations
        for uid in pd.diffs:
            if uid in self.diffs:
                # self.diffs already has a record for the streaming object given
                # by uid, so we will combine their diffs
                self.diffs[uid].extend(pd.diffs[uid])
            else:
                # there is a new streaming object entry, so add it to the self.diffs
                self.diffs[uid] = pd.diffs[uid]

    def __len__(self):
        total = 0
        for d in self.diffs:
            total += len(self.diffs[d])
        return total

    def __str__(self):
        return f'PickleDiff pkl: {self.pkl} diffs: {self.diffs}'


def _squash_pickle_diff_queue(queue, item, MAX_DIFF=_MAX_DIFF):
    """Combine all PickleDiff entries in an asyncio queue into a single entry.

    Args:
        queue: Asyncio queue.
        item: PickleDiff to be squashed with the rest of the entries in the queue.
        MAX_DIFF: maximum length for the squashed diff object.

    Returns:
        True on success, False if MAX_DIFF is exceeded.
    """
    # collect all of the items to be squashed
    queue_entries = []
    for _ in range(queue.qsize()):
        queue_entries.append(queue.get_nowait())
        queue.task_done()
    queue_entries.append(item)
    # squashed diff operations
    new_pd = PickleDiff()
    for pd in queue_entries:
        new_pd.squash(pd)
    if len(new_pd) > MAX_DIFF:
        return False
    # place the squashed item onto the queue
    queue.put_nowait(new_pd)
    return True


class StreamingPickler(Pickler):
    """Special pickler for streamed objects."""

    def __init__(self, file):
        """
        Args:
            file: file-like object where the pickle will be saved.
        """
        super().__init__(file)
        # dictionary where the keys are an object uid and the value is a list
        # containing all of the operations that have been performed on the
        # object since the last pickling operation
        self.diff_stream_data = {}

    def persistent_id(self, obj):
        # unique hash for this object
        uid = id(obj)
        if isinstance(obj, StreamingList):
            # update the internal diffs dictionary
            self.diff_stream_data[uid] = obj.diff_ops.copy()
            # reset the object's diffs
            obj._clear_diff_ops()
            # return the uid of the object
            return ('StreamingList', uid)
        else:
            # return None so obj is pickled as usual
            return None


class StreamingUnpickler(Unpickler):
    """Special unpickler for streamed objects."""

    def __init__(self, file, stream_obj_db, diff):
        """
        Args:
            file: File-like object where the pickle will be saved.
            stream_obj_db: Dictionary where the keys are an object uid and the
                value is a Streaming object.
            diff: Dictionary of diffs.
        """
        super().__init__(file)
        self.stream_obj_db = stream_obj_db
        self.diff_stream_data = diff

    def persistent_load(self, pid):
        # this method is invoked whenever a persistent ID is encountered
        type_tag, uid = pid
        if type_tag == 'StreamingList':
            if uid not in self.stream_obj_db:
                self.stream_obj_db[uid] = StreamingList([])
            diff_ops = self.diff_stream_data[uid]
            self.stream_obj_db[uid]._merge(diff_ops)
            return self.stream_obj_db[uid]
        else:
            # Always raises an error if you cannot return the correct object.
            # Otherwise, the unpickler will think None is the object referenced
            # by the persistent ID.
            raise UnpicklingError(
                f'Persistent object type [{type_tag}] is not supported.'
            )


def streaming_pickle_diff(obj: Any) -> PickleDiff:
    """Special streaming pickle function. For special Streaming objects,
    extract the differences since the last pickle. These differences are
    returned separately from the main pickle data.

    Args:
        obj: The object to pickle.

    Returns:
        Tuple of the form (obj pickled, diffs dictionary)
    """
    file = io.BytesIO()
    pickler = StreamingPickler(file)
    # pickle the given object
    pickler.dump(obj)
    return PickleDiff(file.getvalue(), pickler.diff_stream_data)


def streaming_load_pickle_diff(stream_obj_db: Dict, pickle_diff: PickleDiff) -> Any:
    """Special streaming unpickle function. For special Streaming objects, only
    the differences since the last pickle will be unpickled, then the objects
    will be updated.

    Args:
        stream_obj_db: Dictionary for storing the special streaming objects.
            The keys are an object uid and the value is a Streaming object.
            This will be populated automatically. It must persist between
            unpickling operations in order to perform the updating.
        pickle_diff: PickleDiff object.

    Returns:
        Unpickled object.
    """
    file = io.BytesIO(pickle_diff.pkl)
    unpickler = StreamingUnpickler(file, stream_obj_db, pickle_diff.diffs)
    return unpickler.load()


def serialize_pickle_diff(pickle_diffs: PickleDiff) -> bytes:
    """Serialize the PickleDiff object.

    Args:
        pickle_diffs: The differences since the last pickle.

    Returns:
        Serialized pickle, diffs.
    """
    return dumps(pickle_diffs)


def deserialize_pickle_diff(pickle_diffs: bytes) -> Any:
    """Deserialize the PickleDiff object.

    Args:
        pickle_diffs: Dictionary containing the differences since the last pickle.

    Returns:
        Dictionary containing the differences since the last pickle.
    """
    return loads(pickle_diffs)
