from PyQt5.Qsci import QsciScintilla, QsciLexerPython
from PyQt5 import QtWidgets, QtGui, QtCore

class Scintilla_Code_Editor(QsciScintilla):
    request_run_signal = QtCore.pyqtSignal()

    def keyPressEvent(self, ev):
        if ev.modifiers() & QtCore.Qt.ControlModifier and ev.key() == QtCore.Qt.Key_Slash:
            # Commenting/Uncommenting on Ctr+/
            if self.hasSelectedText():
                isSelection = True
                selection = list(self.getSelection())
                start, _, end, _ = selection
                end += 1
            else:
                isSelection = False
                cursor_pos = list(self.getCursorPosition())
                start, _ = cursor_pos
                end = start + 1
            self.setSelection(start,0,end,0)
            text = self.selectedText()
            split = text.split('\n')
            if all([line=='' or line[0]=='#' for line in split]): #Need to uncomment if line starts with '#'
                new_split = ['' if line=='' else line[1:] for line in split]
            else: #Need to comment
                new_split = ['' if line=='' else '#'+line for line in split]
            new_text = '\n'.join(new_split)
            self.removeSelectedText()
            self.insert(new_text)

            if isSelection:
                selection[3] += len(new_text)-len(text)
                self.setSelection(*selection)
            else:
                cursor_pos[1] += len(new_text)-len(text)
                self.setCursorPosition(*cursor_pos)
            ev.accept()
        elif ev.modifiers() & QtCore.Qt.ShiftModifier and ev.key() == QtCore.Qt.Key_Return:
            self.request_run_signal.emit()
            
        else:
            super().keyPressEvent(ev)

class Monokai_Python_Lexer(QsciLexerPython):
    def __init__(self, editor, *args):
        super().__init__(editor, *args)

        #Margins
        editor.setMarginLineNumbers(1, True)
        editor.setMarginWidth(1, '99999')
        editor.setMarginsBackgroundColor(QtGui.QColor("#272822"))
        editor.setMarginsForegroundColor(QtGui.QColor('#75715e'))

        #Cursor
        editor.ensureCursorVisible()
        editor.setCaretForegroundColor(QtGui.QColor('white'))
        editor.setCaretWidth(2)

        #Indentation
        editor.setAutoIndent(True)
        editor.setIndentationsUseTabs(False)
        editor.setTabWidth(4)


        self.setDefaultPaper(QtGui.QColor("#272822"))
        font = QtGui.QFont('Courier New',12)
        self.setFont(font)

        self.setIndentationWarning(QsciLexerPython.Inconsistent)
        self.setHighlightSubidentifiers(False)

        self.setColor(QtGui.QColor('#9081ff'), QsciLexerPython.Number) ## Purple
        self.setColor(QtGui.QColor('#66d9ef'), QsciLexerPython.HighlightedIdentifier )## Blue
        self.setColor(QtGui.QColor('#e2266d'), QsciLexerPython.Keyword) ## keyword red
        self.setColor(QtGui.QColor('white'), QsciLexerPython.Operator) ## White
        self.setColor(QtGui.QColor('#75715e'), QsciLexerPython.Comment) ## Comment Gray

        self.setColor(QtGui.QColor('#e6db5a'), QsciLexerPython.DoubleQuotedString) ## String Yellow
        self.setColor(QtGui.QColor('#e6db5a'), QsciLexerPython.SingleQuotedString) ## String Yellow
        self.setColor(QtGui.QColor('#e6db5a'), QsciLexerPython.TripleSingleQuotedString) ## String Yellow
        self.setColor(QtGui.QColor('#e6db5a'), QsciLexerPython.TripleDoubleQuotedString) ## String Yellow
        
        self.setColor(QtGui.QColor('#a6e22e'), QsciLexerPython.ClassName) ## Green
        self.setColor(QtGui.QColor('#a6e22e'), QsciLexerPython.FunctionMethodName) ## Green
        self.setColor(QtGui.QColor('#a6e22e'), QsciLexerPython.Decorator) ## Green

    def keywords(self, s):
        # if s == 1:
        #     return super().keywords(s) + '+ - * / =='
        if s == 2:
            special_func = '__abs__ __add__ __and__ __call__ __class__ __cmp__ __coerce__ __complex__ __contains__ __del__ __delattr__ __delete__ __delitem__ __delslice__ __dict__ __div__ __divmod__ __eq__ __float__ __floordiv__ __ge__ __get__ __getattr__ __getattribute__ __getitem__ __getslice__ __gt__ __hash__ __hex__ __iadd__ __iand__ __idiv__ __ifloordiv__ __ilshift__ __imod__ __imul__ __index__ __init__ __instancecheck__ __int__ __invert__ __ior__ __ipow__ __irshift__ __isub__ __iter__ __itruediv__ __ixor__ __le__ __len__ __long__ __lshift__ __lt__ __metaclass__ __mod__ __mro__ __mul__ __ne__ __neg__ __new__ __nonzero__ __oct__ __or__ __pos__ __pow__ __radd__ __rand__ __rcmp__ __rdiv__ __rdivmod__ __repr__ __reversed__ __rfloordiv__ __rlshift__ __rmod__ __rmul__ __ror__ __rpow__ __rrshift__ __rshift__ __rsub__ __rtruediv__ __rxor__ __set__ __setattr__ __setitem__ __setslice__ __slots__ __str__ __sub__ __subclasscheck__ __truediv__ __unicode__ __weakref__ __xor__'
            built_in = 'abs divmod input open staticmethod all enumerate int ord str any eval isinstance pow sum basestring execfile issubclass print super bin file iter property tuple bool filter len range type bytearray float list raw_input unichr callable format locals reduce unicode chr frozenset long reload vars classmethod getattr map repr xrange cmp globals max reversed zip compile hasattr memoryview round __import__ complex hash min set  delattr help next setattr  dict hex object slice  dir id oct sorted'
            return "class def lambda None True False " + special_func + built_in 
        else:
            return super().keywords(s)