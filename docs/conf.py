# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import codecs
import os
import pathlib
import re
import sys
sys.path.insert(0, os.path.abspath('.'))


def read(*parts):
    """
    Build an absolute path from *parts* and and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
    here = pathlib.Path(__file__).parent.resolve()
    with codecs.open(os.path.join(here, *parts), "rb", "utf-8") as f:
        return f.read()


def find_version(*file_paths):
    """
    Build a path from *file_paths* and search for a ``__version__``
    string inside.
    """
    version_file = read(*file_paths)
    version_match = re.search(
        r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M
    )
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


# -- Project information -----------------------------------------------------

project = 'nspyre'
copyright = '2020, Alexandre Bourassa'
author = 'Alexandre Bourassa'

# The full version, including alpha/beta/rc tags
meta_path = os.path.join('..', 'src', 'nspyre', '__init__.py')
release = find_version(meta_path)


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.

needs_sphinx = '3.1.2'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.mathjax', # for math formulas
    'sphinx.ext.napoleon', # for numpy and google style docstrings
    #'sphinx_autodoc_typehints',
    #'sphinx.ext.viewcode',
    #'sphinx.ext.extlinks',
    #'sphinx_tabs.tabs',
    #'sphinx_automodapi.automodapi',
    #'jupyter_sphinx',
    'nbsphinx', # for .ipynb file support (i.e. jupyter notebooks)
    #'sphinxcontrib.bibtex', # for bibliographic references
    'sphinx.ext.imgconverter',
    'sphinxcontrib.rsvgconverter', # for SVG->PDF conversion in LaTeX output
    'sphinx_copybutton' # for adding 'copy to clipboard' buttons to all text/code boxes
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.

html_theme_options = {
    #'canonical_url': '',
    #'analytics_id': 'UA-XXXXXXX-1',  #  Provided by Google in your dashboard
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    #'vcs_pageview_mode': '',
    'style_nav_header_background': '#2b2b2b',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': False,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = ['custom.css']

#html_logo = 'images/logo.png'
#html_favicon = 'images/favicon.ico'

html_last_updated_fmt = '%b %d, %Y'
#'%Y/%m/%d'
