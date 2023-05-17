import codecs
import re
from pathlib import Path

from setuptools import find_packages
from setuptools import setup


here = Path(__file__).parent.resolve()


def read(*parts):
    """
    Build an absolute path from *parts* and and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
    with codecs.open(Path(here, *parts), 'rb', 'utf-8') as f:
        return f.read()


def find_version(*file_paths):
    """
    Build a path from *file_paths* and search for a ``__version__``
    string inside.
    """
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


meta_path = Path('src', 'nspyre', '__init__.py')
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
    author='Jacob Feder, Michael Solomon, Jose A. Mendez, Alexandre Bourassa',
    author_email='jfed@uchicago.edu, msolo@uchicago.edu, mendez99@uchicago.edu, '
    'abourassa@uchicago.edu',
    maintainer='Jacob Feder, Michael Solomon',
    maintainer_email='jfed@uchicago.edu, msolo@uchicago.edu',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: System :: Distributed Computing',
    ],
    keywords='nspyre, physics, science, research',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    zip_safe=False,
    python_requires='>=3.7',
    install_requires=[
        # you know it, you love it
        'numpy >=1.23.1',
        # instrument server proxying
        'rpyc >=5.2.3',
        # Qt/GUI (won't install on ARM)
        'pyqt6 ==6.2.3; platform_machine != "aarch64" and '
        'platform_machine != "armv7l"',
        'pyqt6-qt6 ==6.2.3; platform_machine != "aarch64" and '
        'platform_machine != "armv7l"',
        'pyqtgraph >=0.13.1; platform_machine != "aarch64" and '
        'platform_machine != "armv7l"',
    ],
    extras_require={
        'dev': [
            'pre-commit',
            'sphinx',
            'sphinx-copybutton',
            'sphinx_rtd_theme',
            'sphinx-autoapi',
        ],
        'tests': [
            'pytest',
            'pytest-cov',
            'psutil',
            'lantz',
            'pint',
        ],
    },
    test_suite='tests',
    entry_points={
        'console_scripts': [
            'nspyre-inserv=nspyre.cli.inserv:_main',
            'nspyre-dataserv=nspyre.cli.dataserv:_main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/nspyre-org/nspyre/issues',
        'Source': 'https://github.com/nspyre-org/nspyre/',
    },
    include_package_data=True,
    options={'bdist_wheel': {'universal': '1'}},
)
