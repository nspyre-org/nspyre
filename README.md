# nspyre
[![GitHub license](https://img.shields.io/github/license/nspyre-org/nspyre)](https://github.com/nspyre-org/nspyre/blob/master/LICENSE)
[![Documentation Status](https://readthedocs.org/projects/nspyre/badge/?version=latest)](https://nspyre.readthedocs.io/en/latest/?badge=latest)

Pythonic Networked Scientific Experimentation Toolkit

See https://nspyre.readthedocs.io/

# What is NSpyre?

NSpyre is a Python Framework for conducting physics experiments. It uses a
networked approach to allow for the running of experiments using distributed
equipment over many networked systems. The experimental hardware being controlled
can thus be connected to different computers, which can in turn be controlled by
another machine running the *experimental* commands. This allows for the easy
integration of shared resources in a research environment.

It's built on top of the Lantz (instrumentation communication toolkit) module
for interfacing with equipment using a variety of protocols and uses the RPyC
module to implement remote procedure calls for server communication. NSpyre grew
out of many years of development in the Awschalom Group and others — first from
many years of LabView and Matlab code into an original *proto-spyre* in python,
and finally into it’s fully realized networked form.

# How is it used?

The beauty of NSpyre is that many operations can be performed in multiple ways,
allowing for maximum flexibility. This includes both command line, GUI, and
Jupyter interfaces. Experiments and analyses can be written in detailed
*spyrelets* or added in-situ in a scripting style fashion. This
*plug-and-play* fashion allows for many modalities, but to get up to speed quickly,
here is some quickstart information:

Start the main GUI menu:

```
$ nspyre
```

Add the configuration file for your experiment:

```
$ nspyre-config client -a path/to/client_config.yaml
$ nspyre-config -l
* 0: client_default_config.yaml
  1: path/to/client_config.yaml
```

Set the activate configuration file to your experiment configuration:

```
$ nspyre-config client -s 1
$ nspyre-config -l
  0: client_default_config.yaml
* 1: path/to/client_config.yaml
```

Start (or restart) the MongoDB server:

```
$ nsypre-mongodb
```

Start an instrument server for running hardware:

```
$ nspyre-inserv
```

Run nspyre using a jupyter notebook:

```python
%gui qt5
from nspyre.inserv.gateway import InservGateway
from nspyre.widgets.launcher import SpyreletLauncherWidget, Combined_Launcher
```

```python
%gui qt5 #Sometimes jupyters needs a few runs of this commands for some weird reason
```

```python
%gui qt5
# Add all the instruments
with InservGateway() as isg:
    sg_loc = 'local1/fake_sg'
    isg.devs[sg_loc].amplitude = Q_(2.0, 'volt')

    locals().update(m.get_devices())
    print('Available devices: ', list(isg.get_devices().keys()))

    # Add all the spyrelets
    all_spyrelets = load_all_spyrelets()
    locals().update(all_spyrelets)
    print('Available spyrelets: ', list(all_spyrelets.keys()))

    # Clean up the mongo database if desired
    # unload_all_spyrelets(except_list=list(all_spyrelets.keys()))

    # Make a launcher
    launcher = Combined_Launcher(spyrelets=all_spyrelets)
```

# Who uses it? (And who are we)

Primarily developed out of the Awschalom Group at the University of Chicago PME,
we are an experimental quantum physics research lab with a focus on *Spin Dynamics
and Quantum Information Processing in the Solid State*. There has been growing
adoption of nspyre in the immediate surroundings outside our doors, but there is
hope that this software can be adopted by more and more people from different
institutions and we can all benefit from these shared resources to lower the
development time for writing code and foster exchange to improve our research
and maximize our productivity. Anyone in the research or industrial spaces using
electrical or other computer controlled equipment with a programming interface
(or an already written Lantz driver) can benefit from these resources.
