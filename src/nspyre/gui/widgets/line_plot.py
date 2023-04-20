"""
A wrapper for pyqtgraph PlotWidget.
"""
import logging
import time
from functools import partial
from typing import Any
from typing import Dict

from pyqtgraph import mkColor
from pyqtgraph import PlotDataItem
from pyqtgraph import PlotWidget
from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

from ..style._colors import colors
from ..style._colors import cyclic_colors
from ..style._style import nspyre_font
from ..threadsafe_data import QThreadSafeData
from ._widget_update_thread import WidgetUpdateThread

_logger = logging.getLogger(__name__)


class PlotSeriesData(QtCore.QObject):
    """Container for the data of a single data series within a LinePlotWidget."""
    def __init__(self):
        super().__init__()
        self.x = []
        """X data array."""
        self.y = []
        """Y data array."""
        self.plot_data_item: PlotDataItem = None
        """pyqtgraph PlotDataItem associated with the data."""
        self.hidden: bool = False
        """Whether the plot is hidden."""


class LinePlotData(QThreadSafeData):
    """Manages all plot data series for a LinePlotWidget."""

    added_plot = QtCore.Signal(str, PlotSeriesData)
    removed_plot = QtCore.Signal(str, PlotSeriesData)
    cleared_plots = QtCore.Signal()
    hid_plot = QtCore.Signal(str, PlotSeriesData)
    showed_plot = QtCore.Signal(str, PlotSeriesData)

    def __init__(self, plot_widget):
        super().__init__()
        self.plot_widget = plot_widget
        self.plots: Dict[str, PlotSeriesData] = {}
        """A dict mapping data set names (str) to a PlotSeriesData associated with each line plot."""
        # for blocking set_data until the data has been processed
        self.sem = QtCore.QSemaphore(n=1)

    def add_plot(self, name: str, **kwargs):
        """Add a new plot.

        Args:
            name: Name for the plot.
            kwargs: Additional keyword args to pass to PlotDataItem().
        """
        with self.mutex:
            if name in self.plots:
                _logger.info(
                    f'A plot with the name [{name}] already exists. Ignoring add_plot request.'
                )
                return
            self.plots[name] = PlotSeriesData()
            self.run_main(self._add_plot, name, kwargs, blocking=True)
            self.added_plot.emit(name, self.plots[name])

    def _add_plot(self, name, kwargs):
        """Helper for add_plot."""
        self.plots[name].plot_data_item = self.plot_widget.plot(name=name, **kwargs)

    def remove_plot(self, name: str):
        """Remove a plot from the display and delete it's associated data.

        Args:
            name: Name of the plot.
        """
        with self.mutex:
            if name not in self.plots:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring remove_plot request.'
                )
                return

            # remove the plot from internal plot storage
            del self.plots[name]

            self.removed_plot.emit(name, self.plots[name])

    def clear_plots(self):
        """Remove all plots and delete their associated data."""
        with self.mutex:
            self.plots = {}
            self.cleared_plots.emit()

    def hide_plot(self, name: str):
        """Hide a plot.

        Args:
            name: Name of the plot.
        """
        with self.mutex:
            if name not in self.plots:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring hide_plot request.'
                )
                return

            self.plots[name].hidden = True
            self.hid_plot.emit(name, self.plots[name])

    def show_plot(self, name: str):
        """Show a previously hidden plot.

        Args:
            name: Name of the plot.
        """
        with self.mutex:
            if name not in self.plots:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring show_plot request.'
                )
                return

            self.plots[name].hidden = False
            self.showed_plot.emit(name, self.plots[name])

    def set_data(self, name: str, xdata: Any, ydata: Any, signal: QtCore.Signal):
        """Queue up x/y data to update a plot series.

        Args:
            name: Name of the plot.
            xdata: Array-like of data for the x-axis.
            ydata: Array-like of data for the y-axis.
            signal: signal to emit when the data is ready. Will emit() the associated PlotSeriesData.
        """
        # block until any previous calls to set_data have been fully processed
        self.sem.acquire()

        with self.mutex:
            if name not in self.plots:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring set_data request.'
                )
                self.sem.release()
                return

            # set the new x and y data
            self.plots[name].x = xdata
            self.plots[name].y = ydata

            # signal that new data is ready
            signal.emit(name, self.plots[name])


class LinePlotWidget(QtWidgets.QWidget):
    """Qt widget that generates a pyqtgraph 1D line plot with some reasonable default settings and a variety of added features."""

    new_data = QtCore.Signal(str, PlotSeriesData)
    """Qt Signal emitted when new data is available."""

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
            args: passed to the QWidget init, like :code:`super().__init__(*args, **kwargs)`
            title: Plot title.
            xlabel: Plot x-axis label.
            ylabel: Plot y-axis label.
            font: Font to use in the plot title, axis labels, etc., although
                the font type may not be fully honored.
            legend: If True, display a figure legend.
            downsample: If True, utilize the pyqtgraph 'auto' downsampling in
                the 'mean' mode (see https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/plotitem.html#pyqtgraph.PlotItem.setDownsampling).
            kwargs: passed to the QWidget init, like :code:`super().__init__(*args, **kwargs)`
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

        self.plot_data = LinePlotData(self.plot_widget)
        """Instance of LinePlotData to manage plot data in a thread-safe way."""

        # take appropriate actions when the plot data is changed
        self.plot_data.showed_plot.connect(self._showed_plot)
        self.plot_data.cleared_plots.connect(self._cleared_plots)
        self.plot_data.hid_plot.connect(self._hid_plot)
        self.plot_data.removed_plot.connect(self._hid_plot)

        self.setLayout(self.layout)

        # clean up when the widget is destroyed
        self.destroyed.connect(partial(self.stop))

        # thread for updating the plot data
        self.update_thread = WidgetUpdateThread(self.update)
        # process new data when a signal is generated by the update thread
        self.new_data.connect(self._process_data)
        # start the thread
        self.update_thread.start()

        # plot setup code
        self.setup()

    def plot_item(self):
        """Return the pyqtgraph `PlotItem <https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/plotitem.html#pyqtgraph.PlotItem>`__."""
        return self.plot_widget.getPlotItem()

    def set_title(self, title: str):
        """Set the plot title.

        Args:
            title: The new plot title.
        """
        self.plot_widget.setTitle(title, size=f'{self.font.pointSize()}pt')

    def setup(self):
        """Subclasses should override this function to perform any setup code \
        before the :py:meth:`~nspyre.gui.widgets.line_plot.LinePlotWidget.update` \
        function is called from a new thread."""
        pass

    def update(self):
        """Subclasses should override this function to update the plot. This \
        function will be called repeatedly from a new thread."""
        time.sleep(1)

    def teardown(self):
        """Subclasses should override this function to perform any teardown code. \
        The thread calling :py:meth:`~nspyre.gui.widgets.line_plot.LinePlotWidget.update` \
        isn't guaranteed to have exited yet."""
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
        """Add a new plot to the PlotWidget. Thread-safe.

        Args:
            name: Name of the plot.
            pen: See https://pyqtgraph.readthedocs.io/en/latest/graphicsItems/plotdataitem.html.
            symbolBrush: See https://pyqtgraph.readthedocs.io/en/latest/graphicsItems/plotdataitem.html.
            symbolPen: See https://pyqtgraph.readthedocs.io/en/latest/graphicsItems/plotdataitem.html.
            symbol: See https://pyqtgraph.readthedocs.io/en/latest/graphicsItems/plotdataitem.html.
            symbolSize: See https://pyqtgraph.readthedocs.io/en/latest/graphicsItems/plotdataitem.html.
            kwargs: Additional keyword args to pass to PlotDataItem().
        """
        if not pen:
            pen = self._next_color()
        self.plot_data.run_safe(self.plot_data.add_plot, name, pen=pen, symbolBrush=symbolBrush, symbolPen=symbolPen, symbol=symbol, symbolSize=symbolSize, **kwargs)

    def remove_plot(self, name: str):
        """Remove a plot from the display and delete it's associated data. Thread-safe.

        Args:
            name: Name of the plot.
        """
        self.plot_data.run_safe(self.plot_data.remove_plot, name)

    def clear_plots(self):
        """Remove all plots and delete their associated data. Thread-safe."""
        self.plot_data.run_safe(self.plot_data.clear_plots)

    def _cleared_plots(self):
        """Callback to remove all plots from PlotWidget display."""
        self.plot_item().clear()

    def hide_plot(self, name: str):
        """Remove a plot from the display, keeping its data. Thread-safe.

        Args:
            name: Name of the plot.
        """
        self.plot_data.run_safe(self.plot_data.hide_plot, name)

    def _hid_plot(self, name: str, plot_series_data: PlotSeriesData):
        """Callback to remove a plot from PlotWidget display."""
        self.plot_widget.removeItem(plot_series_data.plot_data_item)

    def show_plot(self, name: str):
        """Display a previously hidden plot. Thread-safe.

        Args:
            name: Name of the plot.
        """
        self.plot_data.run_safe(self.plot_data.show_plot, name)

    def _showed_plot(self, name: str, plot_series_data: PlotSeriesData):
        """Callback to add a plot to PlotWidget display."""
        self.plot_widget.addItem(plot_series_data.plot_data_item)

    def set_data(self, name: str, xdata: Any, ydata: Any, blocking: bool = True):
        """Queue up x/y data to update a line plot. Thread-safe.

        Args:
            name: Name of the plot.
            xdata: Array-like of data for the x-axis.
            ydata: Array-like of data for the y-axis.
            blocking: Whether this method should block until the data has been queued.
        """
        self.plot_data.run_safe(
            self.plot_data.set_data, name, xdata, ydata, self.new_data, blocking=blocking
        )

    def _process_data(self, name: str, plot_series_data: PlotSeriesData):
        """Update a line plot triggered by set_data.

        Args:
            name: Name of plot series.
            plot_series_data: PlotSeriesData to update the plot for.
        """
        try:
            with self.plot_data.mutex:
                if name in self.plot_data.plots:
                    plot_series_data.plot_data_item.setData(plot_series_data.x, plot_series_data.y)
                else:
                    _logger.debug(f'Not updating [{name}] because the plot does not exist.')
        except Exception as exc:
            raise exc
        finally:
            self.plot_data.sem.release()

    def stop(self):
        """Stop the plot updating thread and run the
        :py:meth:`~nspyre.gui.widgets.line_plot.LinePlotWidget.teardown` code."""
        self.update_thread.update_func = None
        self.teardown()

    # TODO
    # def add_zoom_region(self):
    #     """Create a GUI element for selecting a plot subregion. Returns a new PlotWidget that contains a view with it's x span linked to the area selected by the plot subregion."""
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
