from setuptools import setup, find_packages
import codecs
import pathlib
import re


here = pathlib.Path(__file__).parent.resolve()


def read(*parts):
    """
    Build an absolute path from *parts* and and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
    with codecs.open(pathlib.PurePath(here, *parts), "rb", "utf-8") as f:
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


meta_path = pathlib.PurePath('src', 'nspyre', '__init__.py')
version = find_version(meta_path)

long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='nspyre',
    version=version,
    license='BSD 3-Clause License',
    description='Networked Scientific Python Research Environment',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/nspyre-org/nspyre',
    author='Alexandre Bourassa',
    author_email='abourassa@uchicago.edu',
    maintainer='Michael Solomon',
    maintainer_email='msolo@uchicago.edu',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: IPython',
        'Framework :: Jupyter',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Logging',
    ],
    keywords='nspyre, measurement toolkit, experimentation platform, physics, science, research',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    zip_safe=False,
    python_requires='>=3.8, <4',
    install_requires=[
        # SciPy
        'numpy>=1.19.1',
        'scipy>=1.5.2',
        'pandas>=1.1.2',
        # MongoDB
        'pymongo>=3.10.1',
        # Qt
        'pyqt5>=5.12.3',
        'pyqtgraph>=0.11.0',
        'qscintilla>=2.11.2',
        # VISA
        'pyvisa>=1.10.1',
        # Lantz
        'pint>=0.15',
        'lantzdev>=0.5.2',
        # Utilities
        'parse>=1.18.0',
        'tqdm>=4.49.0',
        'rpyc>=4.1.5',
    ],
    entry_points={
        'console_scripts': [
            'nspyre=nspyre.gui:main',
            'nspyre-config=nspyre.config:main',
            'nspyre-mongodb=nspyre.mongodb:main',
            'nspyre-inserv=nspyre.inserv:main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/nspyre-org/nspyre/issues',
        'Source': 'https://github.com/nspyre-org/nspyre/',
    },
    include_package_data=True,
    options={'bdist_wheel': {'universal': '1'}},
)
