# Configuration file for the Sphinx documentation builder.
import codecs
import re
import sys
from pathlib import Path

# location of the source code root directory relative to this directory
source_root = '../../src/nspyre/'
# location of the file containing the '__version__' string relative to this directory
source_version_file = '../../src/nspyre/__init__.py'

# resolve the source absolute path
HERE = Path(__file__).parent
source_path = (HERE / source_root).resolve()

# add the source to sys path so autodoc can import it
sys.path.insert(0, str(source_path))


def find_version(file_path):
    """
    Search for a ``__version__`` string.
    """
    with codecs.open(file_path, 'rb', 'utf-8') as f:
        version_file = f.read()
        version_match = re.search(
            r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M
        )
        if version_match:
            return version_match.group(1)
        raise RuntimeError('Unable to find version string.')


def skip(app, what, name, obj, would_skip, options):
    if name == '__init__':
        return False
    return would_skip


def setup(app):
    app.connect('autodoc-skip-member', skip)


# -- Project information -----------------------------------------------------

project = 'nspyre'
copyright = '2021, Alexandre Bourassa, Michael Solomon, Jacob Feder'
author = 'Alexandre Bourassa, Michael Solomon, Jacob Feder'

# The source version
release = find_version(source_version_file)

# -- General configuration ---------------------------------------------------

needs_sphinx = '3.1.2'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',  # for generating API from docstrings
    'sphinx.ext.mathjax',  # for math formulas
    'sphinx.ext.napoleon',  # for numpy and google style docstrings
    'sphinx_copybutton',  # for adding 'copy to clipboard' buttons to all text/code boxes
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Configure copybutton to ignore console prompts
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.

html_theme_options = {
    # 'canonical_url': '',
    # 'analytics_id': 'UA-XXXXXXX-1',  #  Provided by Google in your dashboard
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'top',
    'style_external_links': False,
    # 'vcs_pageview_mode': '',
    'style_nav_header_background': '#2b2b2b',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': False,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = ['custom.css']

# html_logo = 'images/logo.png'
# html_favicon = 'images/favicon.ico'

html_last_updated_fmt = '%b %d, %Y'
# '%Y/%m/%d'
