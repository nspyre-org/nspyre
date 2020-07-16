############
Contributing
############

If you’re reading this, you probably want to contribute to NSpyre — great! This project has taken a lot of work and still has big strides to take to continue making it a flexible, extensive, and sustainable experimentation platform. Any and all support is greatly appreciated.

This document lays out guidelines and advice for contributing to this project. If you’re thinking of contributing, please start by reading the immediate info below detailing project specifics to get a feel for how contributing to this project works. If you have any questions, feel free to reach out to one of the primary maintainers. *(Need link/contact info)*

The guide is split into sections based on the type of contribution you’re thinking of making, with a section that covers general guidelines for all contributors.

Quick Facts
===========

For this project, we use a standard *fork & pull* model to collaborate, common practice for open source projects. If you are interested in helping maintain the platform, send us a message after getting involved and we’ll be happy to bring you onboard. Our code follows the Google Style Guide for docstrings, with standard `PEP 8 <https://pep8.org>`_ formatting, and some of our own caveats as detailed :ref:`here <Code Style>`. For documentation, we write in `reStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_, using `Sphinx <https://www.sphinx-doc.org/en/master/>`_ to generate files and `ReadTheDocs <https://docs.readthedocs.io/en/stable/intro/getting-started-with-sphinx.html>`_ for site hosting. We follow the philosophy of `WriteTheDocs <https://www.writethedocs.org>`_ -- that is, we subscribe to *Docs as Code*. If the above remarks don’t make sense to you, or you simply want a more detailed description of how to do things, continue reading below.

Philosophy
==========

As `WriteTheDocs <https://www.writethedocs.org/guide/writing/beginners-guide-to-docs/>`_ eloquently states,

   | If people don’t know *why your project exists*, they won’t use it.
   | If people can’t figure out *how to install your code*, they won’t use it.
   | If people can’t figure out *how to use your code*, they won’t use it.

If you’ve made it this far, then presumably we’ve satisfied the first two criteria (although we are still working on making the second easier!), and this site is the reason for the third. The key to good software development is good documentation. Along with that is the need to strike a balance between efficiency and complexity. Because this is a scientific and an experimentation platform, certain requirements with speed and structure are necessary. We try to keep things as simple as possible, but we are flexible in approach when necessary. Most importantly, we strive for *sustainable* code.

Code Contributions
==================


We understand that for a lot of people using this project, it might be their first time contributing to an open source project. And getting started on any new project can be intimidating, especially for newcomers. So along with information about our workflow in this project, our style guides, and particular information on how to get involved, we've included some basic information, collated from various sources on a number of important topics. We hope this helps you on your journey. (If you are already a pro, we're happy to have you -- you can skip to our style guide :ref:`here <Code Style>`.)

Version Control
---------------

First thing’s first — *Git*. `Git <https://git-scm.com>`_ is an example of a *distributed version control system* (DVCS) commonly used for open source and commercial software development. A *version control system* (VCS) tracks the history of changes as people and teams collaborate on projects together. As the project evolves, teams can run tests, fix bugs, and contribute new code with the confidence that any version can be recovered at any time. Developers can review project history to find out:

* Which changes were made?
* Who made the changes?
* When were the changes made?
* Why were changes needed?

Git grew out of the needs of the developers of the Linux kernel and is one of the most widely-used VCS tools available. `GitHub <https://github.com>`_ is a Git hosting repository that builds collaboration directly into the development process by providing developers with tools to ship better code through command line features, issues (threaded discussions), pull requests, code review, and more. If all this information is new, then please read this: `Understanding the GitHub flow <https://guides.github.com/introduction/flow/>`_  — it’s a 5min read and will make your life a lot easier going forward. (If you want a much deeper explanation and a good reference source to get up to speed on the basics of using Git and GitHub, go to the `Git Handbook <https://guides.github.com/introduction/git-handbook/>`_.)

How to Contribute: Forking & Pull Requests
------------------------------------------

Great, now that you understand the *why* and *how* of Git & Github, let’s explain the workflow to contribute. We use the **fork & pull** model to collaborate. This means that to contribute to the project, you first need to **Fork** the project on GitHub. A Github fork is just a copy of a repository. When you *fork* a repo, you are storing a copy of that repo on your personal account. Doing so grants you full *write* access to edit files and develop the code on your version of it. After making changes to the codebase -- squashing bugs, adding features, writing docs -- make a **Pull Request**. When you ``git pull`` on a codebase, that's the git term for *pulling* updated and/or new files from one version of a repo to another; you are simply updating files in a particular direction. Thus, *pulling* applies in many different contexts (more info :ref:`below <push pull>`). A *pull request*, therefore, is a request you make for the maintainers, of the original repo you forked, to *review & merge* your edits into their version of the code stored on their repo.

To make things concrete, but let’s do an actual example of this on the command line to give you some reference steps.

.. tip::
   
   In addition to performing the following steps on the command line, as shown below, these steps can be carried out directly on GitHub.com, and many popular text editors and IDEs have integrated tools for using git/github directly within their environments.

.. code-block:: console

   # first you need to fork the repository of interests (NSpyre obviously). To do so, click the Fork button in the header of the repository.
   
.. image:: images/Bootcamp-Fork.png

.. code-block:: console

   # sit back and watch the forking magic. When it’s finished, you’ll be taken to your copy of the NSpyre repository.

.. code-block:: console
   
   # navigate to the directory you want to store your local copy of the repo
   cd ~/SourceCode

   # download the repository on GitHub.com to your machine
   git clone https://github.com/[your-username]/nspyre.git
   
   # change into the `nspyre` directory that was created for you
   cd nspyre
   
   # create a new branch to store any new changes
   git branch descriptive-branch-title
   
   # switch to that branch (line of development)
   git checkout descriptive-branch-title
   
   # make changes, for example, edit `contributors.md` and create `my-spyrelet.py`

   # stage the changed files
   git add contributors.md my-spyrelet.py
   
   # take a snapshot of the staging area (anything that's been added)
   # the -m flag adds a comment to the commmit
   git commit -m "my snapshot"
   
   # push changes to github
   git push --set-upstream origin descriptive-branch-title

.. _push pull:

You will notice the addition of two new terms -- *branch* and *push*. Each repository can have multiple versions of it's codebase that are under development. The ``master`` *branch* is the main version of the code on the repository and is the one from which all other branches originate. This is the official working version that is used out in the wild and the one you eventually want your changes to appear on. When forking a repo, you also get all the different branches at the time of copying. When contributing on an issue, you first want to search for a **branch** to check if someone has already started work on that issue of interest. If not, start a new one; make sure to give it a descriptive title so people easily understand what's being worked on (e.g. refactoring-pep8, awg-spyrelet, driver-gui-bug, etc).

Finally, the *push* command updates files from one location to another, but in the opposite direction as *pull*. ``git pull`` brings any changes from the target repo on the servers and updates them into the version/branch that you currently have checked out on your local copy. ``git push`` does the opposite. It takes any changes on your local copy of the branch you have checked out and reflects those changes on the repository. If you don't ``git push`` your commits then they will not be uploaded to the repo; similarly, this means they won't be backed up so it is good practice to push your progress so it is saved centrally and not on your machine least anything happens to it.

Creating a Pull Request
^^^^^^^^^^^^^^^^^^^^^^^

Once you've vetted your code for errors, checked to make sure you've followed all the project guidelines, and most importantly, *documented* your code, you have make a pull request.

.. code-block:: console
   
   # either click the Pull Request tab, then from the Pull Request page, click the green New pull request button,
   # or, navigate to the branch you made edits to in the drop-down box on the repository homepage, and click the green Compare & pull request button.
   
   # then, look over your changes in the diffs on the Compare page, make sure they’re what you want to submit.
   
   # give your pull request a title and write a brief description of your changes.
   # when you’re satisfied, click the big green Create pull request button.
   
   # Congrats, you've submitted your first contributon for merging!

.. image:: images/create-pr.png

That’s the gist on the workflow!

.. important::
   
   People save there code everywhere, in there documents folder, on their desktop, in a hidden folder. Not having a system to managing code is BAD. That's why git exists after all. Similarly, you want your code to be in a unified location on your local machine. Where it isn't in a place that someone will easily tamper with it, but in a location that is still easily accessible if you know where it is. To that end, we *highly* recommend that you create a directory at the root level of your local machine called ``SourceCode`` (or with whatever camalcase formatting your prefer). Create a new subdirectory for every project going forward.

.. warning::
   
   So for NSpyre, if you call ``git clone https://github.com/[username]/nspyre.git`` inside SourceCode, you will get a new directory called nspyre, containing your repo.

.. note:: Virutal Environments
   
   Making sure you have some sort of virtual environment implied in your workflow. The built in management of Anaconda is great if you are already using Anaconda for your scientific packages. If you are just using pip, then check out venv -- it have a lot of improvements over virtualenv.




You can *pull* a branch you are working on from the github repo to get the most up-to-date copy locally, pull one branch into another to take certain *commits*, or pull in the reverse direction to bring your updates into the main repo.

(As this is a GitHub specific step and not a git step, it can’t
   be completed with the git tool. However, checkout the **hub command line tool** for this and
   other useful extensions of the git tool https://hub.github.com).

.. _Code Style:

Code Style
----------

There are many different frameworks for styling. The NSpyre codebase uses the Python standard for styling — `PEP 8 <https://pep8.org>`_. In addition, we have adopted the Google Style Guide for both code and our docstrings. In brief, this follows PEP 8 with some leniences in the spirit of legibility.

Additionally, we strongly encourage the use of the new PEP ### standard for constructors in all but the most obvious cases.

All functions, methods, and classes are to contain docstrings. Object data model methods (e.g. ``__repr__``) are typically the exception to this rule.


Documentation Contributions
===========================

Documentation Style
-------------------

When contributing documentation, please do your best to follow the style of the documentation files. This means a soft-limit of 79 characters wide in your text files and a semi-formal, yet friendly and approachable, prose style.

When presenting Python code, use single-quoted strings (``'hello'`` instead of ``"hello"``); this applies to code as well!


Writing Docs
------------

The project uses `reStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_ as the markup language for writing documentation. `Sphinx <https://www.sphinx-doc.org/en/master/>`_ is then used to generate documentation and the is hosted on `ReadTheDocs <https://docs.readthedocs.io/en/stable/intro/getting-started-with-sphinx.html>`_. Documentation improvements are always welcome! The documentation files live in the docs/ directory of the codebase. They’re written in reStructuredText, and use Sphinx to generate the full suite of documentation. Writing documentation is a great way to start contributing, especially if you are new, and will help get you familiar with the codebase.

reStructuredText is an easy-to-read, what-you-see-is-what-you-get plaintext markup syntax and parser system. It is useful for inline program documentation (such as Python docstrings), for quickly creating simple web pages, and for standalone documents. Markdown is another, slightly simpler alternative. reStructuredText is a bit harder to use, but is more powerful and is widely used for Python documentation.

The reasons for using a markup language is straight-forward:

* easy to write and maintain (strong semantic markup tools and well-defined markup standards)
* still makes sense as plain text (easily legible in raw form)
* renders nicely into HTML (this looks nice, doesn't it?)

Don’t believe me? Then go .rst file for this webpage and see for yourself.



reStructuredText
^^^^^^^^^^^^^^^^

There are many resources on rST syntax, but we've found it helpful to know these basic things when starting out (and as a quick refresher!).

Paragraphs in reStructuredText are blocks of text separated by at least one blank line. All lines in the paragraph must be indented by the same amount.

Indentation is important and mixing spaces and tabs causes problems. So just like Python, it's best to just use spaces. And typically, you want to **use three spaces**. Yes, you read that correctly. (A standard tab is equivalent to 4 spaces.)

Inline markup for font styles is similar to MarkDown:

* Use one asterisk (``*text*``) for *italics*.
* Use two asterisks (``**text**``) for **bolding**.
* Use two backticks (````text````) for ``code samples``.
* Use an underscore (``reference_``) for reference_.
* Use one backtick (```reference with whitespace`_``) for `reference with whitespace`_.
* | Links to external sites contain the link text and a bracketed URL in backticks, followed by an underscore:
  | ```Link to Write the Docs <https://www.writethedocs.org/>`_``.
.. _Cross-referencing arbitrary locations:
* To support cross-referencing to arbitrary locations in any document, the standard **reST** labels are used. For this to work, label names must be unique throughout the entire documentation. There are two ways in which you can refer to labels:
  
  - If you place a label directly before a section title, you can reference to it with :ref:`label-name`. For example:
    
    .. code-block:: console
       
       .. _my-reference-label:
       
       Section to cross-reference
       --------------------------
       
       This is the text of the section.
       
       It refers to the section itself, see :ref:`my-reference-label`.
    
    The ``:ref:`` role would then generate a link to the section, with the link title being “Section to cross-reference”. This works just as well when section and reference are in different source files.
    | Labels that aren’t placed before a section title can still be referenced, but you must give the link an explicit title, using this syntax: :ref:`Link title <label-name>`.
    | Note: Reference labels must start with an underscore. When referencing a label, the underscore must be omitted (see examples above).

:ref:`A title <Cross-referencing arbitrary locations>`

If asterisks \* or backquotes \\ appear in running text and could be confused with inline markup delimiters, they have to be escaped with a backslash .

Headers
~~~~~~~

Section Headers are demarcated by underlining (or over- and underlining) the section title using non-alphanumeric characters like dashes, equal signs, or tildes. The row of non-alphanumeric characters must be at least as long as the header text. Use the same character for headers at the same level. The following creates a header

.. code-block:: console

   =========
   Chapter 1    while this creates a header at a different level:    Section 1.1
   =========                                                         -----------

If you use the same non-alphanumeric character for underline-only and underline-and-overline headers, they will be considered to be at *different* levels.


+----------------------------------------------------------+--------------------------------------------------------+
| ::                                                       | ..                                                     |
|                                                          |                                                        |
|    Title                                                 |   Title                                                |
|    =====                                                 |   =====                                                |
|                                                          |                                                        |
|    A lone top-level section is lifted up to be the       |   A lone top-level section is lifted up to be the      |
|    document's title.                                     |   document's title.                                    |
|                                                          |                                                        |    
|    Any non-alphanumeric character can be used, but       |   Any non-alphanumeric character can be used, but      |
|    Python convention is:                                 |   Python convention is:                                |
|                                                          |                                                        |
|    * ``#`` with overline, for parts                      |   * ``#`` with overline, for parts                     |
|    * ``*`` with overline, for chapters                   |   * ``*`` with overline, for chapters                  |
|    * ``=``, for sections                                 |   * ``=``, for sections                                |
|    * ``-``, for subsections                              |   * ``-``, for subsections                             |
|    * ``^``, for subsubsections                           |   * ``^``, for subsubsections                          |
|    * ``"``, for paragraphs                               |   * ``"``, for paragraphs                              |
+----------------------------------------------------------+--------------------------------------------------------+



Lists
~~~~~

For enumerated lists, use a number or letter followed by a period, or followed by a right-bracket, or surrounded by brackets

.. code-block:: console

  1. Use this to format the items in your list like 1., 2., etc.

  A. To make items in your list go like A., B., etc. Both uppercase and lowercase letters are acceptable.

  I. Roman numerals are also acceptable, uppercase or lowercase.

  (1) Numbers in brackets are acceptable.

  1) So are numbers followed by a bracket.

For bulleted lists, use indentation to indicate the level of nesting of a bullet point. You can use ``-``, ``+``, or ``*`` as a bullet point character

.. code-block:: console

  * Bullet point
    
    - nested bullet point
      
      + even more nested bullet point

Code Samples
~~~~~~~~~~~~~~~~~~~

There are many different ways using reST to display code samples, or any text that should not be formatted, but we explicity use the ``code-block`` directive for simplicity. Here's an example

.. code-block:: rst

   This is the paragraph preceding the code sample::
   
   .. code-block:: python
      
      #some sample code
      print('Hello, World!')

The doctest block must end
with a blank line and should *not* end with an unused prompt::

    >>> 1 + 1
    2
    
    
Doctest blocks are text blocks which begin with ">>> ", the Python interactive interpreter main prompt, and end with a blank line. Doctest blocks are treated as a special case of literal blocks, without requiring the literal block syntax. If both are present, the literal block syntax takes priority over Doctest block syntax:

This is an ordinary paragraph.

>>> print 'this is a Doctest block'
this is a Doctest block

The following is a literal block::

    >>> This is not recognized as a doctest block by
    reStructuredText.  It *will* be recognized by the doctest
    module, though!
Indentation is not required for doctest blocks.






Again, there is a lot that can be said about markup languages, and many resources already available online; avail yourself of whatever helps best.

Resources:

* `reStructuredText Primer <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_
* `Cheatsheet <https://github.com/ralsina/rst-cheatsheet>`_
* `A ReStructuredText Primer <https://docutils.sourceforge.io/docs/user/rst/quickstart.html>`_


There are plenty of good resources online, and cheat sheets to get you started:

* `An Introduction to reStructuredText <https://docutils.readthedocs.io/en/sphinx-docs/ref/rst/introduction.html>`_
* `A ReStructuredText Primer <https://docutils.readthedocs.io/en/sphinx-docs/user/rst/quickstart.html>`_

https://www.writethedocs.org/guide/writing/reStructuredText/

.. attention:: Virtual Environments
   
   Making sure you have some sort of virtual environment implied in your workflow. The built in management of Anaconda is great if you are already using Anaconda for your scientific packages. If you are just using pip, then check out venv -- it have a lot of improvements over virtualenv.

.. caution:: Virtual Environments
   
   Making sure you have some sort of virtual environment implied in your workflow. The built in management of Anaconda is great if you are already using Anaconda for your scientific packages. If you are just using pip, then check out venv -- it have a lot of improvements over virtualenv.

.. danger:: Virtual Environments
   
   Making sure you have some sort of virtual environment implied in your workflow. The built in management of Anaconda is great if you are already using Anaconda for your scientific packages. If you are just using pip, then check out venv -- it have a lot of improvements over virtualenv.

.. error:: Virtual Environments
   
   Making sure you have some sort of virtual environment implied in your workflow. The built in management of Anaconda is great if you are already using Anaconda for your scientific packages. If you are just using pip, then check out venv -- it have a lot of improvements over virtualenv.
   
.. hint:: Virtual Environments
   
   Making sure you have some sort of virtual environment implied in your workflow. The built in management of Anaconda is great if you are already using Anaconda for your scientific packages. If you are just using pip, then check out venv -- it have a lot of improvements over virtualenv.
   
.. important:: Virtual Environments
   
   Making sure you have some sort of virtual environment implied in your workflow. The built in management of Anaconda is great if you are already using Anaconda for your scientific packages. If you are just using pip, then check out venv -- it have a lot of improvements over virtualenv.
   
.. note:: Virtual Environments
   
   Making sure you have some sort of virtual environment implied in your workflow. The built in management of Anaconda is great if you are already using Anaconda for your scientific packages. If you are just using pip, then check out venv -- it have a lot of improvements over virtualenv.
   
.. tip:: Virtual Environments
   
   Making sure you have some sort of virtual environment implied in your workflow. The built in management of Anaconda is great if you are already using Anaconda for your scientific packages. If you are just using pip, then check out venv -- it have a lot of improvements over virtualenv.
   
.. warning:: Virtual Environments
   
   Making sure you have some sort of virtual environment implied in your workflow. The built in management of Anaconda is great if you are already using Anaconda for your scientific packages. If you are just using pip, then check out venv -- it have a lot of improvements over virtualenv.
   
.. admonition:: Virtual Environments
   
   Making sure you have some sort of virtual environment implied in your workflow. The built in management of Anaconda is great if you are already using Anaconda for your scientific packages. If you are just using pip, then check out venv -- it have a lot of improvements over virtualenv.








Resources
---------

There’s a lot of online resources available for various aspects of software development. Below is a collection of the most useful as they pertain to development in this project. Hopefully they are useful to you as you get up to speed.

* https://guides.github.com
* https://cheat.readthedocs.io/en/latest/git.html
* https://dont-be-afraid-to-commit.readthedocs.io/en/latest/contributing.html
* https://gist.github.com/RichardBronosky/454964087739a449da04

