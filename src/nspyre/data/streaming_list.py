class StreamingList(list):
    """List-like object that can be streamed efficiently through the data server."""

    def __init__(self, iterable):
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
