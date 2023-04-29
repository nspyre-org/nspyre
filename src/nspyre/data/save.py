import json
import pickle
from typing import Union
from pathlib import Path
from typing import Any

import numpy as np


class _NumpyEncoder(json.JSONEncoder):
    """For converting numpy arrays to python lists so that they can be written to JSON:
    https://stackoverflow.com/questions/26646362/numpy-array-is-not-json-serializable
    """
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def save_json(filename: Union[str, Path], data: Any):
    """Save data to a json file.

    Args:
        filename: File to save to.
        data: Python object to save.
    """
    with open(filename, 'w') as f:
        json.dump(data, f, cls=_NumpyEncoder, indent=4)


def save_pickle(filename: Union[str, Path], data: Any):
    """Save data to a python pickle file.

    Args:
        filename: File to save to.
        data: Python object to save.
    """
    with open(filename, 'wb') as f:
        pickle.dump(data, f)

class AutoSaver:
    """Automatically save data in the data server to a file."""
    def __init__(self, data_set: str, filename: Union[str, Path], min_interval: float = 30):
        """
        Args:
            data_set: Data set name in the data server to save.
            filename: File to save to.
            min_interval: Minimum time (s) interval to save data.
        """
        pass