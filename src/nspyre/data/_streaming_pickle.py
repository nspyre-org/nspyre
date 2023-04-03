"""Implement special Pickling functions that can be used for streaming data.
Instead of serializing and deserializing an entire object, pickle operations
will only serialize/deserialize the differences since the most recent pickle.
This can be used to efficiently stream data e.g. over a network connection.
"""
import io
import pickle
from typing import Any
from typing import Dict

from .streaming_list import StreamingList


def streaming_pickle_diff(obj: Any) -> tuple:
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
    return (file.getvalue(), pickler.diff_stream_data)


def streaming_serialize(pickle_diffs: tuple) -> bytes:
    """Serialize the pickle + diffs tuple.

    Args:
        pickle_diffs: Dictionary containing the differences since the last pickle.

    Returns:
        Serialized pickle, diffs.
    """
    return pickle.dumps(pickle_diffs)


def streaming_deserialize(pickle_diffs: bytes) -> Any:
    """Deserialize the pickle + diffs tuple.

    Args:
        pickle_diffs: Dictionary containing the differences since the last pickle.

    Returns:
        Dictionary containing the differences since the last pickle.
    """
    return pickle.loads(pickle_diffs)


def streaming_load_pickle_diff(
    stream_obj_db: Dict, obj_pickle: bytes, diffs: Dict
) -> Any:
    """Special streaming unpickle function. For special Streaming objects, only
    the differences since the last pickle will be unpickled, then the objects
    will be updated.

    Args:
        stream_obj_db: Dictionary for storing the special streaming objects.
            The keys are an object uid and the value is a Streaming object.
            This will be populated automatically. It must persist between
            unpickling operations in order to perform the updating.
        obj_pickle: Bytes array containing the pickled object.
        diffs: Dictionary of diffs.

    Returns:
        Unpickled object.
    """
    file = io.BytesIO(obj_pickle)
    unpickler = StreamingUnpickler(file, stream_obj_db, diffs)
    return unpickler.load()


class StreamingPickler(pickle.Pickler):
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


class StreamingUnpickler(pickle.Unpickler):
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
                self.stream_obj_db[uid] = StreamingList([])  # TODO
            diff_ops = self.diff_stream_data[uid]
            self.stream_obj_db[uid]._merge(diff_ops)
            return self.stream_obj_db[uid]
        else:
            # Always raises an error if you cannot return the correct object.
            # Otherwise, the unpickler will think None is the object referenced
            # by the persistent ID.
            raise pickle.UnpicklingError(
                f'Persistent object type [{type_tag}] is not supported.'
            )
