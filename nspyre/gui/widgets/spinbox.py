# 3rd party

from pyqtgraph import SpinBox as _SpinBox
from PyQt5 import QtCore
from pint.util import infer_base_unit

# nspyre
from nspyre.definitions import Q_

class SpinBox(_SpinBox):

    def __init__(self, parent=None, value=1.0, unit=None, **kwargs):
        self.unit = unit
        self.base_unit = None
        kwargs['dec'] = kwargs.pop('dec', True)
        kwargs['minStep'] = kwargs.pop('minStep', 0.1)
        kwargs['decimals'] = kwargs.pop('decimals', 8)
        # kwargs['compactHeight'] = False
        if self.unit is not None:
            q = Q_(unit)
            base_units = infer_base_unit(q)
            base_unit = '*'.join('{} ** {}'.format(u, p) for u, p in base_units.items())
            self.base_unit = base_unit if not base_unit == '' else 'dimensionless'
            q_base = Q_(self.base_unit)
            factor = (q / q_base).to_base_units().m
            opts = {
                'suffix': '{0.units:~}'.format(q_base),
                'siPrefix': True,
            }
            kwargs.update(opts)
            value *= factor
        super().__init__(parent=parent, value=value, **kwargs)
        self.setMaximumHeight(1e6)
        return

    def getValue(self):
        if self.base_unit is None:
            return super().value()
        else:
            return Q_(super().value(), self.base_unit)

    def unit_value(self):
        val = super().value()
        uval = Q_(val, self.base_unit) if self.base_unit is not None else val
        return uval

    def setValue(self, value=None, **kwargs):
        if isinstance(value, Q_):
            value = value.to_base_units().m
        super().setValue(value=value, **kwargs)
