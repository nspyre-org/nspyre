#######
Install
#######

The recommended way to install NSpyre is to **install the latest stable release**
from `conda-forge <https://conda-forge.org/docs/>`_ (more info below). We
currently support **Python 3.8+**. If you already have conda installed and know how to use it, 
you can install nspyre with:

.. code-block:: console

   conda install -c conda-forge nspyre

Conda
=====

NSpyre is not a pure-python module because it relies on MongoDB to handle its
measurement database — a dependency that cannot be easily
packaged by PyPI. In addition, the large volume of deployments made in a research
setting makes it desirable to have a consistent, reproducible programming
environment. To this end, conda is a suitable solution for both requirements and is
the **recommended** way to install NSpyre.

If you do not already have conda installed, we recommend using the Miniconda distribution
(instead of the Anaconda distribution) because it contains fewer default packages, many
of which are unnecessary for the vast majority of users. The latest release
of Miniconda is available here:
`Miniconda installers <https://docs.conda.io/en/latest/miniconda.html>`_. Choose 
the Python 3.x 64-bit distribution for your platform.

Once conda is installed, you'll want to add the conda-forge channel as a repository
and rebuild/update conda with the latest packages from conda-forge:

.. code-block:: console

   $ conda activate
   (base) $ conda config --add channels conda-forge
   (base) $ conda config --show channels
   channels:
     - conda-forge
     - defaults
   (base) $ conda update -n base conda

Notice that you now have two channels from which conda will search for packages:
*conda-forge* and *defaults*. The channels are listed in order of priority - conda will
search the first repository when updating or installing a package unless explicitly told
otherwise. The *defaults* channel is the one conda is bundled with and from which the initial
set of packages are installed; this is the *Anaconda* channel for their managed repository
of curated packages. However, this is non-exhaustive and *conda-forge* is an open-source
alternative of community maintained packages (and the channel on which nspyre is published).
Running the update command above reinstalls the core packages from conda-forge. You can confirm
this by running the following:

.. code-block:: console

   (base) $ conda list
   # packages in environment at /path/to/base/env/miniconda3:
   #
   # Name                    Version                   Build    Channel
   anaconda-client           1.7.2                      py_0    conda-forge
   anaconda-project          0.8.3                      py_0    conda-forge
   attrs                     20.2.0             pyh9f0ad1d_0    conda-forge
   beautifulsoup4            4.9.2                      py_0    conda-forge
   ...
   zipp                      3.2.0                      py_0    conda-forge
   zlib                      1.2.11            h7795811_1009    conda-forge
   zstd                      1.4.5                h289c70a_2    conda-forge

You will see that everything is installed from *conda-forge*. It is desirable to have all the
packages come from the same repository due to compiling complexities, ABI compatibility, and
consistent build environments (beyond the scope of this discussion).

Finally, by default the base environment will always be active upon opening the terminal (you
probably didn't need to run ``conda activate`` above). Specifically, the ``miniconda3/bin``
directory will be added to your path and allow you to start python and all the other programs
in ``bin``. Typically, this isn't good practice and it's better to explicitly activate the
environment. To change conda’s configuration settings so that it does not automatically activate
the base environment upon opening of the terminal run:

.. code-block:: console

   $ conda config --set auto_activate_base false

If you already have conda installed and/or you use conda for managing environments for other
projects in which the above configuration settings aren't ideal, then simply make sure to add
the *conda-forge* channel to whatever environments you want to install nspyre in.

Once you have conda setup, make a new environment:

.. code-block:: console

   (base) $ conda create --name <your-env-name>

And install nspyre:

.. code-block:: console

   (base) $ conda activate <your-env-name>
   (<your-env-name>) $ conda install nspyre

PyPI (aka using pip)
====================

Although it is highly recommended to install NSpyre using conda, it is also available from PyPI. However, MongoDB must be installed separately. The latest
release of MongoDB for your platform can be obtained here:
`MongoDB downloads <https://www.mongodb.com/download-center/community>`_ (v4.4.1 or greater
required). The MongoDB binaries also need to be added to your PATH. In Windows, this can be accomplished with:

.. code-block:: console

   $ ``C:\Program Files\MongoDB\Server\4.4\bin``

NSpyre itself can then be installed:

.. code-block:: console

   $ pip install git+https://github.com/lantzproject/lantz-core.git#egg=lantzdev git+https://github.com/lantzproject/lantz-drivers.git#egg=lantz-drivers git+https://github.com/lantzproject/lantz-ino.git#egg=lantz-ino git+https://github.com/lantzproject/lantz-sims.git#egg=lantz-sims git+https://github.com/lantzproject/lantz-qt.git#egg=lantz-qt
   $ pip install nspyre

.. attention::

   If installing NSpyre with PyPi, be aware that the distribution of `Lantz <https://github.com/lantzproject/lantz-core>`_ available on PyPI
   is currently outdated and needs to be installed directly from GitHub as shown in the commands above
