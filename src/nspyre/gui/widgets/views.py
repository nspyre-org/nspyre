class View:
    """Some Views for plotting."""

    def __init__(self, f, plot_type):
        self.update_fun = f
        self.type = plot_type
        self.init_formatters = dict()
        self.update_formatters = dict()

    def add_formatter(self, formatter):
        if formatter.type == 'init':
            self.init_formatters[formatter.handled_class] = formatter.format_fun
        elif formatter.type == 'update':
            self.update_formatters[formatter.handled_class] = formatter.format_fun

    def get_formatter(self, plot, formatter_type):
        formatters = (
            self.init_formatters if formatter_type == 'init' else self.update_formatters
        )
        for c in formatters:
            if issubclass(type(plot), c):
                return formatters[c]


class Formatter:
    def __init__(self, f, formatter_type, handled_class, view_list):
        self.format_fun = f
        self.type = formatter_type
        self.handled_class = handled_class
        self.view_list = view_list


def Plot1D(fun):
    """Functions marked with this decorators should take a single argument (beyond self) which will be the dataframe representing the data
    The function marked must return a dict with the following format {'trace_name_1':[x1, y1], 'trace_name_2':[x2, y2], ...}"""
    return View(fun, '1D')


def Plot2D(fun):
    """Functions marked with this decorators should take a single argument (beyond self) which will be the dataframe representing the data
    The function marked must return a 2D ndarray to be plotted"""
    return View(fun, '2D')


def PlotFormatInit(class_type_handled, view_list):
    """Functions marked with this decorators will be called once when initializing the views.
    They should declare in the decorators argument what type of class they will handle.
    For example, if a function wants to do some extra formatting on any subclass of BasePlotWidget from nspyre.widgets.plotting then:

    @Plot1D()
    def my_plot(self, df):
        return {'trace1':[df.x.values, df.y1.values],  'trace2':[df.x.values, df.y2.values]}

    @PlotFormat(BasePlotWidget, ['my_plot'])
    def my_formating_function(self, plot):
        plot.xlabel = 'x axis (in a.u.)'

     There can only be one one PlotFormatInit function associated with a given plotting function
    """

    def PlotFormatInit_Decorator(fun):
        return Formatter(fun, 'init', class_type_handled, view_list)

    return PlotFormatInit_Decorator


def PlotFormatUpdate(class_type_handled, view_list):
    """Same idea as PlotFormatUpdate, but functions marked with this decorators will be called every time the plot is updated."""

    def PlotFormatUpdate_Decorator(fun):
        return Formatter(fun, 'update', class_type_handled, view_list)

    return PlotFormatUpdate_Decorator
