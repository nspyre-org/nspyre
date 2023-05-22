class StreamingList(list):
    """List-like object that can be streamed efficiently through the \
    :py:class:`~nspyre.data.server.DataServer`.
    :py:class:`StreamingList` is meant to act as a drop-in replacement for a python
    list. When this object is pushed to the data server using a call to
    :py:meth:`~nspyre.data.source.DataSource.push`, instead of sending the whole
    contents of :py:class:`StreamingList`, only the differences since the last
    :py:meth:`~nspyre.data.source.DataSource.push` are sent. This allows
    for much higher data throughput for larger data sets.

    Although :py:class:`StreamingList` is typically able to automatically calculate the
    differences since the last :py:meth:`~nspyre.data.source.DataSource.push`, there is
    one situation where this is not possible: if a mutable object that is contained
    somewhere inside the :py:class:`StreamingList` is modified, it cannot be detected.
    In this situation, the :py:class:`StreamingList` must be manually notified that
    one of its items has been updated, e.g.:

    .. code-block:: python

        import numpy as np
        from nspyre import DataSource
        from nspyre import StreamingList

        with DataSource('my_dataset') as src:
            sl = StreamingList()
            a = np.array([1, 2, 3])
            b = np.array([4, 5, 6])
            c = np.array([7, 8, 9])

            # these StreamingList calls will automatically calculate diffs
            sl.append(a)
            sl.append(b)
            sl.append(c)

            src.push(sl)

            # here we are modifying a mutable object inside of the StreamingList,
            # which it cannot detect
            a[1] = 10

            # we can manually tell the StreamingList that its object 'a' was modified
            sl.updated_item(0)

            src.push(sl)

    """

    def __init__(self, iterable=None):
        """
        Args:
            iterable: iterable object to initialize the contents of the list
                with, e.g. :code:`sl = StreamingList([1, 2, 3])`.
        """
        super().__init__()
        # A list of operations that have been performed on the list since the
        # last update. A list of tuples where the first tuple element is the
        # operation type, and the subsequent elements are (optional) objects
        # for that operation.
        self.diff_ops = []
        # initialize the list contents
        if iterable is not None:
            for i in iterable:
                self.append(i)

    def updated_item(self, idx):
        """The item at the given index was modified, and, therefore, its cached
        value is no longer valid and must be updated.

        Args:
            idx: index that was modified
        """
        try:
            self[idx]
        except IndexError as err:
            raise ValueError(f'Invalid index [{idx}].') from err
        self._diff_op('u', idx, self[idx])

    def _diff_op(self, op, *args):
        """Add an entry to the diff_ops list."""
        self.diff_ops.append((op,) + tuple(args))

    def _clear_diff_ops(self):
        """Reset the record of operations that have been performed on the list."""
        self.diff_ops.clear()

    def _regenerate_diffops(self):
        """Generate a new diffops array."""
        self._clear_diff_ops()
        for idx, val in enumerate(self):
            self._diff_op('i', idx, val)

    def _merge(self, diff_ops):
        """Merge the changes given by diff_ops into the list."""
        if self.diff_ops != []:
            raise ValueError("can't merge because there are local changes.")
        for i, op in enumerate(diff_ops):
            if op[0] == 'i':
                self.insert(op[1], op[2], register_diff=False)
            elif op[0] == 'd':
                self.__delitem__(op[1], register_diff=False)
            elif op[0] == 'u':
                self.__setitem__(op[1], op[2], register_diff=False)
            else:
                raise ValueError(f'unrecognized operation [{op}] at index [{i}]')

    def __add__(self, val):
        """See docs for Python list."""
        new_sl = self.copy()
        new_sl.extend(val)
        return new_sl

    def __mul__(self, repeats):
        """See docs for Python list."""
        if not isinstance(repeats, int):
            raise ValueError(
                f"can't multiply sequence by non-int of type {type(repeats)}"
            )
        if repeats > 0:
            new_sl = self.copy()
            for _ in range(repeats - 1):
                new_sl.extend(self)
            return new_sl
        else:
            return StreamingList()

    def __setitem__(self, idx, val, register_diff=True):
        """See docs for Python list."""
        super().__setitem__(idx, val)
        if register_diff:
            self._diff_op('u', idx, val)

    def __delitem__(self, idx, register_diff=True):
        """See docs for Python list."""
        super().__delitem__(idx)
        if register_diff:
            self._diff_op('d', idx)

    def insert(self, idx, val, register_diff=True):
        """See docs for Python list."""
        super().insert(idx, val)
        if register_diff:
            self._diff_op('i', idx, val)

    def remove(self, val):
        """See docs for Python list."""
        idx = super().index(val)
        self.__delitem__(idx)

    def pop(self, idx):
        """See docs for Python list."""
        val = self[idx]
        self.__delitem__(idx)
        return val

    def append(self, val):
        """See docs for Python list."""
        self.insert(len(self), val)

    def extend(self, val):
        """See docs for Python list."""
        for o in val:
            self.append(o)

    def clear(self):
        """See docs for Python list."""
        for i in range(len(self)):
            self.__delitem__(i)

    def sort(self, *args, **kwargs):
        """See docs for Python list."""
        super().sort(*args, **kwargs)
        for i in range(len(self)):
            self.updated_item(i)

    def reverse(self):
        """See docs for Python list."""
        super().reverse()
        for i in range(len(self)):
            self.updated_item(i)

    def copy(self):
        """See docs for Python list."""
        return StreamingList(super().copy())

    def __reduce__(self):
        """Custom pickling method. Required because this is a list subclass,
        which seems to be handled differently."""
        return (StreamingList, (super().copy(),))
