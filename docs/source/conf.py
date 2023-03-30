# Configuration file for the Sphinx documentation builder.
import codecs
import re
import sys
from pathlib import Path

# root
root = '../../'
# location of the source code root directory relative to this directory
source_root = root + 'src/'
# location of the file containing the '__version__' string relative to this directory
source_version_file = source_root + 'nspyre/__init__.py'

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


# -- Project information -----------------------------------------------------

project = 'nspyre'
copyright = '2023, Jacob Feder, Michael Solomon, Alexandre Bourassa'
author = 'Jacob Feder, Michael Solomon, Alexandre Bourassa'

# The source version
release = find_version(source_version_file)

# -- General configuration ---------------------------------------------------

# Sphinx extension module names
extensions = [
    'autoapi.extension',
    'sphinx.ext.napoleon',  # for numpy and google style docstrings
    'sphinx_copybutton',  # for adding 'copy to clipboard' buttons to all text/code boxes
]

# autoapi config
# https://sphinx-autoapi.readthedocs.io/en/latest/reference/config.html
autoapi_type = 'python'
autoapi_dirs = [source_root]
autoapi_options = [
    'members',
    'inheritted-members',
    'undoc-members',
    'show-module-summary',
    'imported-members',
]
autoapi_keep_files = True
autodoc_typehints = 'description'
autoapi_python_class_content = 'both'

napoleon_include_init_with_doc = True

# Configure copybutton to ignore console prompts
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
source_suffix = ['.rst', '.md']

# The master toctree document.
master_doc = 'index'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'friendly'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.

html_theme_options = {
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'top',
    'style_external_links': False,
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
