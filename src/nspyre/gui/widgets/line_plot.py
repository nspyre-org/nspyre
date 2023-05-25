"""
A wrapper for pyqtgraph PlotWidget.
"""
import logging
import time
from functools import partial
from typing import Any

from pyqtgraph import mkColor
from pyqtgraph import PlotWidget
from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

from ..style._colors import colors
from ..style._colors import cyclic_colors
from ..style._style import nspyre_font
from ..threadsafe import QThreadSafeObject
from .update_loop import UpdateLoop

_logger = logging.getLogger(__name__)


class _PlotSeriesData(QtCore.QObject):
    """Container for the data of a single data series within a LinePlotWidget."""

    def __init__(self):
        super().__init__()
        self.x = []
        """X data array."""
        self.y = []
        """Y data array."""
        self.plot_data_item = None
        """pyqtgraph PlotDataItem associated with the data."""
        self.hidden = False
        """Whether the plot is hidden."""


class _LinePlotData(QThreadSafeObject):
    """Manages all plot data series for a LinePlotWidget."""

    def __init__(self, plot_widget):
        self.plots = {}
        """A dict mapping data set names (str) to a _PlotSeriesData associated with each
        line plot."""
        # for blocking set_data until the data has been processed
        self.sem = QtCore.QSemaphore(n=1)
        super().__init__()

    def add_plot(self, name: str, callback=None, **kwargs):
        """Add a new plot.

        Args:
            name: Name for the plot.
            callback: Callback function to run (blocking) in the main thread.
            kwargs: Additional keyword args to pass to :code:`callback`.
        """
        with QtCore.QMutexLocker(self.mutex):
            if name in self.plots:
                _logger.info(
                    f'A plot with the name [{name}] already exists. Ignoring add_plot '
                    'request.'
                )
                return
            self.plots[name] = _PlotSeriesData()
            if callback is not None:
                self.run_main(callback, name, self.plots[name], kwargs, blocking=True)

    def remove_plot(self, name: str, callback=None):
        """Remove a plot from the display and delete it's associated data.

        Args:
            name: Name of the plot.
            callback: Callback function to run (blocking) in the main thread.
        """
        with QtCore.QMutexLocker(self.mutex):
            if name not in self.plots:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring '
                    'remove_plot request.'
                )
                return

            if callback is not None:
                self.run_main(callback, name, self.plots[name], blocking=True)

            # remove the plot from internal plot storage
            del self.plots[name]

    def clear_plots(self, callback=None):
        """Remove all plots and delete their associated data.

        Args:
            callback: Callback function to run (blocking) in the main thread.
        """
        with QtCore.QMutexLocker(self.mutex):
            self.plots = {}
            if callback is not None:
                self.run_main(callback, blocking=True)

    def hide_plot(self, name: str, callback=None):
        """Hide a plot.

        Args:
            name: Name of the plot.
            callback: Callback function to run (blocking) in the main thread.
        """
        with QtCore.QMutexLocker(self.mutex):
            if name not in self.plots:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring hide_plot '
                    'request.'
                )
                return

            self.plots[name].hidden = True

            if callback is not None:
                self.run_main(callback, name, self.plots[name], blocking=True)

    def show_plot(self, name: str, callback=None):
        """Show a previously hidden plot.

        Args:
            name: Name of the plot.
            callback: Callback function to run (blocking) in the main thread.
        """
        with QtCore.QMutexLocker(self.mutex):
            if name not in self.plots:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring show_plot '
                    'request.'
                )
                return

            self.plots[name].hidden = False

            if callback is not None:
                self.run_main(callback, name, self.plots[name], blocking=True)

    def set_data(self, name: str, xdata: Any, ydata: Any, callback=None):
        """Queue up x/y data to update a plot series.

        Args:
            name: Name of the plot.
            xdata: Array-like of data for the x-axis.
            ydata: Array-like of data for the y-axis.
            callback: Callback function to run (blocking) in the main thread.
        """
        # block until any previous calls to set_data have been fully processed
        self.sem.acquire()

        with QtCore.QMutexLocker(self.mutex):
            if name not in self.plots:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring set_data '
                    'request.'
                )
                self.sem.release()
                return

            # set the new x and y data
            self.plots[name].x = xdata
            self.plots[name].y = ydata

            if callback is not None:
                self.run_main(callback, name, self.plots[name], blocking=True)


class LinePlotWidget(QtWidgets.QWidget):
    """Qt widget that generates a pyqtgraph 1D line plot with some reasonable default \
    settings and a variety of added features."""

    def __init__(
        self,
        *args,
        title: str = '',
        xlabel: str = '',
        ylabel: str = '',
        font: QtGui.QFont = nspyre_font,
        legend: bool = True,
        downsample: bool = True,
        **kwargs,
    ):
        """
        Args:
            args: passed to the QWidget init, like
                :code:`super().__init__(*args, **kwargs)`
            title: Plot title.
            xlabel: Plot x-axis label.
            ylabel: Plot y-axis label.
            font: Font to use in the plot title, axis labels, etc., although
                the font type may not be fully honored.
            legend: If True, display a figure legend.
            downsample: If True, utilize the pyqtgraph 'auto' downsampling in
                the 'mean' mode (see `PlotItem docs <https://pyqtgraph.readthedocs.io\
                /en/latest/api_reference/graphicsItems/plotitem.html\
                #pyqtgraph.PlotItem.setDownsampling>`__).
            kwargs: passed to the QWidget init, like
                :code:`super().__init__(*args, **kwargs)`
        """
        super().__init__(*args, **kwargs)

        self.font = font

        # layout for storing plot
        self.layout = QtWidgets.QVBoxLayout()

        self.plot_widget = PlotWidget()
        # TODO can't figure out how to generate a hyperlink in the docs for this
        """pyqtgraph PlotWidget for displaying the plot."""

        if downsample:
            self.plot_widget.getPlotItem().setDownsampling(
                ds=True, auto=True, mode='mean'
            )

        self.layout.addWidget(self.plot_widget)

        # plot settings
        self.set_title(title)
        self.plot_widget.enableAutoRange(True)
        # colors
        self.current_color_idx = 0
        self.plot_widget.setBackground(colors['black'])
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # x axis
        self.xaxis = self.plot_widget.getAxis('bottom')
        self.xaxis.setLabel(text=xlabel)
        self.xaxis.label.setFont(font)
        self.xaxis.setTickFont(font)
        self.xaxis.enableAutoSIPrefix(False)
        # y axis
        self.yaxis = self.plot_widget.getAxis('left')
        self.yaxis.setLabel(text=ylabel)
        self.yaxis.label.setFont(font)
        self.yaxis.setTickFont(font)
        self.yaxis.enableAutoSIPrefix(False)

        if legend:
            self.plot_widget.addLegend(labelTextSize=f'{font.pointSize()}pt')

        self.setLayout(self.layout)

        self.stopped = False
        # clean up when the widget is destroyed
        self.destroyed.connect(partial(self._stop))

        self.plot_data = _LinePlotData(self.plot_widget)
        self.plot_data.start()

        # for updating the plot data
        self.update_loop = UpdateLoop(self.update)

        # plot setup code
        self.setup()

        # start the updating
        self.update_loop.start()

    def _stop(self):
        """Stop the plot updating and data management threads, and run the
        :py:meth:`~nspyre.gui.widgets.line_plot.LinePlotWidget.teardown` code."""
        self.stopped = True
        self.update_loop.stop()
        self.plot_data.stop()
        self.teardown()

    def plot_item(self):
        """Return the pyqtgraph `PlotItem <https://pyqtgraph.readthedocs.io/en/latest/\
        api_reference/graphicsItems/plotitem.html#pyqtgraph.PlotItem>`__."""
        return self.plot_widget.getPlotItem()

    def set_title(self, title: str):
        """Set the plot title.

        Args:
            title: The new plot title.
        """
        self.plot_widget.setTitle(title, size=f'{self.font.pointSize()}pt')

    def setup(self):
        """Subclasses should override this function to perform any setup code
        before the :py:meth:`~nspyre.gui.widgets.line_plot.LinePlotWidget.update`
        function is called from a new thread."""
        pass

    def update(self):
        """Subclasses should override this function to update the plot. This
        function will be called repeatedly from a new thread."""
        time.sleep(1)

    def teardown(self):
        """Subclasses should override this function to perform any teardown code.
        The thread calling
        :py:meth:`~nspyre.gui.widgets.line_plot.LinePlotWidget.update` isn't guaranteed
        to have exited yet."""
        pass

    def _next_color(self):
        """Cycle through a set of colors"""
        idx = self.current_color_idx % len(cyclic_colors)
        color = mkColor(cyclic_colors[idx])
        self.current_color_idx += 1
        return color

    def add_plot(
        self,
        name: str,
        pen: QtGui.QColor = None,
        symbolBrush=(255, 255, 255, 100),
        symbolPen=(255, 255, 255, 100),
        symbol: str = 's',
        symbolSize: int = 5,
        **kwargs,
    ):
        """Add a new plot to the PlotWidget. Thread safe.

        Args:
            name: Name of the plot.
            pen: See `PlotDataItem docs <https://pyqtgraph.readthedocs.io/\
                en/latest/graphicsItems/plotdataitem.html>`__.
            symbolBrush: See `PlotDataItem docs <https://pyqtgraph.readthedocs.io/\
                en/latest/graphicsItems/plotdataitem.html>`__.
            symbolPen: See `PlotDataItem docs <https://pyqtgraph.readthedocs.io/\
                en/latest/graphicsItems/plotdataitem.html>`__.
            symbol: See `PlotDataItem docs <https://pyqtgraph.readthedocs.io/\
                en/latest/graphicsItems/plotdataitem.html>`__.
            symbolSize: See `PlotDataItem docs <https://pyqtgraph.readthedocs.io/\
                en/latest/graphicsItems/plotdataitem.html>`__.
            kwargs: Additional keyword arguments to pass to :code:`PlotWidget.plot`.
        """
        if not pen:
            pen = self._next_color()
        self.plot_data.run_safe(
            self.plot_data.add_plot,
            name,
            callback=self._add_plot_callback,
            pen=pen,
            symbolBrush=symbolBrush,
            symbolPen=symbolPen,
            symbol=symbol,
            symbolSize=symbolSize,
            **kwargs,
        )

    def _add_plot_callback(self, name: str, plot_series_data: _PlotSeriesData, kwargs):
        """Helper for add_plot."""
        plot_series_data.plot_data_item = self.plot_widget.plot(name=name, **kwargs)

    def remove_plot(self, name: str):
        """Remove a plot from the display and delete it's associated data. Thread safe.

        Args:
            name: Name of the plot.
        """
        self.plot_data.run_safe(
            self.plot_data.remove_plot, name, callback=self._hide_plot_callback
        )

    def clear_plots(self):
        """Remove all plots and delete their associated data. Thread safe."""
        self.plot_data.run_safe(
            self.plot_data.clear_plots, callback=self._clear_plots_callback
        )

    def _clear_plots_callback(self):
        """Helper for clear_plots."""
        self.plot_widget.getPlotItem().clear()

    def hide_plot(self, name: str):
        """Remove a plot from the display, keeping its data. Thread safe.

        Args:
            name: Name of the plot.
        """
        self.plot_data.run_safe(
            self.plot_data.hide_plot, name, callback=self._hide_plot_callback
        )

    def _hide_plot_callback(self, name: str, plot_series_data: _PlotSeriesData):
        """Callback to remove a plot from PlotWidget display."""
        self.plot_widget.removeItem(plot_series_data.plot_data_item)

    def show_plot(self, name: str):
        """Display a previously hidden plot. Thread safe.

        Args:
            name: Name of the plot.
        """
        self.plot_data.run_safe(
            self.plot_data.show_plot, name, callback=self._show_plot_callback
        )

    def _show_plot_callback(self, name: str, plot_series_data: _PlotSeriesData):
        """Callback to add a plot to PlotWidget display."""
        self.plot_widget.addItem(plot_series_data.plot_data_item)

    def set_data(self, name: str, xdata: Any, ydata: Any, blocking: bool = True):
        """Queue up x/y data to update a line plot. Thread safe.

        Args:
            name: Name of the plot.
            xdata: Array-like of data for the x-axis.
            ydata: Array-like of data for the y-axis.
            blocking: Whether this method should block until the data has been plotted.
        """
        self.plot_data.run_safe(
            self.plot_data.set_data,
            name,
            xdata,
            ydata,
            blocking=blocking,
            callback=self._set_data_callback,
        )

    def _set_data_callback(self, name: str, plot_series_data: _PlotSeriesData):
        """Update a line plot triggered by set_data. Runs in the main thread.

        Args:
            name: Name of plot series.
            plot_series_data: _PlotSeriesData to update the plot for.
        """
        try:
            plot_series_data.plot_data_item.setData(
                plot_series_data.x, plot_series_data.y
            )
        except Exception as err:
            if self.stopped:
                return
            else:
                raise err
        self.plot_data.sem.release()

    # TODO
    # def add_zoom_region(self):
    #     """Create a GUI element for selecting a plot subregion. Returns a new
    #     PlotWidget that contains a view with it's x span linked to the area selected
    #     by the plot subregion."""
    #     # current display region
    #     plot_xrange, plot_yrange = self.plot_widget.viewRange()
    #     xmin, xmax = plot_xrange
    #     center = (xmax + xmin) / 2
    #     span = (xmax - xmin) / 20
    #     # create GUI element for subregion selection
    #     linear_region = LinearRegionItem(values=[center - span, center + span])
    #     self.plot_widget.addItem(linear_region)

    #     # p9 = win.addPlot(title="Zoom on selected region")
    #     # p9.plot(data2)
    #     # def updatePlot():
    #     #     p9.setXRange(*lr.getRegion(), padding=0)
    #     # def updateRegion():
    #     #     lr.setRegion(p9.getViewBox().viewRange()[0])
    #     # lr.sigRegionChanged.connect(updatePlot)
    #     # p9.sigXRangeChanged.connect(updateRegion)
    #     # updatePlot()
