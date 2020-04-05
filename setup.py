from setuptools import setup

setup(
    name="nspyre",
    version="0.1.0",
    author="Alexandre Bourassa",
    author_email="abourassa@uchicago.edu",
    description="Networked Scientific Python Research Environment",
    packages=['nspyre',],
    install_requires=[
        # New
        'numpy>=1.16.4',
        'pyqt5==5.13.2',
        'msgpack>=0.6.2',
        'msgpack-numpy>=0.4.4.3',
        # 'pyzmq>=18.0.2', #Use conda for this one
        'pymongo>=3.9.0',
        'pandas>=0.25.2',
        # 'lantz', #This should probably be a seperate install
        'QScintilla==2.11.3',
        # 'pyqtgraph>=0.11.0', #For now this will need to be install from git, until v11 is released
        'pyyaml>=5.1.2',
        'scipy>=1.2.1',
        'tqdm>=4.32.2'
    ],
    dependency_links = ['https://github.com/pyqtgraph/pyqtgraph.git'],
)
