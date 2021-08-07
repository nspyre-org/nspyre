#######
Install
#######

The recommended way to install NSpyre is to **install the latest stable release** from `conda-forge <https://conda-forge.org/docs/>`_ (more info below).

.. code-block:: bash
   
   $ conda install -c conda-forge nspyre

Conda
=====

If you do not already have conda installed, we recommend using the Miniconda distribution (instead of the Anaconda distribution) because it contains fewer default packages, many of which are unnecessary for the vast majority of users. The latest release of Miniconda for your platform is available here: `Miniconda installers <https://docs.conda.io/en/latest/miniconda.html>`__. The default installation options are appropriate for most users:

* Install for *Just Me* (gives full control over install and doesn't require admin privileges)
* Default file location (e.g. C:\\Users\\<UserName>\\Miniconda3)
* **DO** *Register Anaconda as my default Python*. This will make conda available
  to other programs for integration, such as setting up a development environment
  in **PyCharm**.

Once conda is installed, you'll want to add the conda-forge channel as a repository and rebuild/update conda with the latest packages from conda-forge:

.. code-block:: bash

   $ conda activate
   (base) $ conda config --add channels conda-forge
   (base) $ conda config --show channels
   channels:
     - conda-forge
     - defaults
   (base) $ conda update -n base conda

Notice that you now have two channels from which conda will search for packages: *conda-forge* and *defaults*. The channels are listed in order of priority - conda will search the first repository when updating or installing a package unless explicitly told otherwise. The *defaults* channel is the one conda is bundled with and from which the initial set of packages are installed; this is the *Anaconda* channel for their managed repository of curated packages. However, this is non-exhaustive and *conda-forge* is an open-source alternative of community maintained packages (and the channel on which nspyre is published). Running the update command above reinstalls the core packages from conda-forge. You can confirm this by running the following:

.. code-block:: bash

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

You will see that everything is installed from *conda-forge*. It is desirable to have all the packages come from the same repository due to compiling complexities, ABI compatibility, and consistent build environments (beyond the scope of discussion). The ``channel_priority`` can be set to ``strict`` so that only the highest priority channel is even searched when updating or installing; however, there are a few exceptions where a package is needed from *defaults* so this config parameter should not be modified.

Finally, by default the base environment will always be active upon opening the terminal (you probably didn't need to run ``conda activate`` above). Typically, this isn't good practice and it's better to explicitly activate the environment. To change conda’s configuration settings so that it does not automatically activate the base environment upon opening of the terminal run:

.. code-block:: bash

   $ conda config --set auto_activate_base false

If you already have conda installed and/or you use conda for managing environments for other projects in which the above configuration settings aren't ideal, then simply make sure to add the *conda-forge* channel to whatever environments you want to install nspyre in.

Once you have conda setup, it's trivial to install nspyre. Make sure to create and activate a new conda environment for running nspyre so you don't mess with your base environment:

.. code-block:: bash

   (base) $ conda env create --name nspyre-env
   (base) $ conda activate nspyre-env
   ([nspyre-env]) $ conda install nspyre

PyPI (aka using pip)
====================

NSpyre is also available from PyPI:

.. code-block:: bash

   $ pip install nspyre
