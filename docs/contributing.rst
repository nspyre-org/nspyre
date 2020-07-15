############
Contributing
############

If you’re reading this, you probably want to contribute to NSpyre — great! This project has taken a lot of work and still has big strides to take to continue making it a flexible, extensive, and sustainable experimentation platform. Any and all support is greatly appreciated.

This document lays out guidelines and advice for contributing to this project. If you’re thinking of contributing, please start by reading the immediate info below detailing project specifics to get a feel for how contributing to this project works. If you have any questions, feel free to reach out to one of the primary maintainers. *(Need link/contact info)*

The guide is split into sections based on the type of contribution you’re thinking of making, with a section that covers general guidelines for all contributors.

Quick Facts
===========

For this project, we use a standard *fork & pull* model to collaborate, common practice for open source projects. If you are interested in helping maintain the platform, send us a message after getting involved and we’ll be happy to bring you onboard. Our code follows the Google Style Guide for docstrings, with standard `PEP 8 <https://pep8.org>`_ formatting, which has some caveats as detailed :ref:`here <Code Style>`. For documentation, we write in `reStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_, using `Sphinx <https://www.sphinx-doc.org/en/master/>`_ to generate files and `ReadTheDocs <https://docs.readthedocs.io/en/stable/intro/getting-started-with-sphinx.html>`_ for site hosting. We follow the philosophy of `WriteTheDocs <https://www.writethedocs.org>`_ -- that is, we subscribe to *Docs as Code*. If the above remarks don’t make sense to you, or you simply want a more detailed description of how to do things, continue reading below.

Philosophy
==========

As `WriteTheDocs <https://www.writethedocs.org/guide/writing/beginners-guide-to-docs/>`_ eloquently states,

   | If people don’t know *why your project exists*, they won’t use it.
   | If people can’t figure out *how to install your code*, they won’t use it.
   | If people can’t figure out *how to use your code*, they won’t use it.

If you’ve made it this far, then presumably we’ve satisfied the first two criteria (although we are still working on making the second easier!), and this site is the reason for the third. The key to good software development is good documentation. Along with that is the need to strike a balance between efficiency and complexity. Because this is a scientific and an experimentation platform, certain requirements with speed and structure are necessary. We try to keep things as simple as possible, but we are flexible in approach when necessary. Most importantly, we strive for *sustainable* code.

Code Contributions
==================


We understand that for a lot people using this project, it might be their first time contributing to an open source project. And getting started on any new project can be intimidating, especially for newcomers. So along with information about our workflow in this project, our style guides, and particular information on how to get involved, we've included some basic information, collated from various sources on a number of important topics. We hope this helps you on your journey. (If you are already a pro, we're happy to have you -- you can skip to our style guide :ref:`here <Code Style>`.)

Version Control
---------------

First thing’s first — `*Git* <https://git-scm.com>`_. A *version control system* (VCS) tracks the history of changes as people and teams collaborate on projects together. As the project evolves, teams can run tests, fix bugs, and contribute new code with the confidence that any version can be recovered at any time. Developers can review project history to find out:

* Which changes were made?
* Who made the changes?
* When were the changes made?
* Why were changes needed?

Git grew out of the needs of the developers of the Linux kernel and is one of the most widely-used VCS tools available. `GitHub <https://github.com>`_ is a Git hosting repository that builds collaboration directly into the development process by providing developers with tools to ship better code through command line features, issues (threaded discussions), pull requests, code review, and more. If all this information is new, then please read this: `Understanding the GitHub flow <https://guides.github.com/introduction/flow/>`_  — it’s a 5min read and will make your life a lot easier going forward. (If you want a much deeper explanation and a good reference source to get up to speed on the basics of using git and GitHub, go here: `Git Handbook <https://guides.github.com/introduction/git-handbook/>`_.)

How to Contribute: Forking & Pull Requests
------------------------------------------

Great, now that you understand the *why* and *how* of Git & Github, let’s explain how to get involved. We use the **Fork & Pull** model for open-source development. This means that to contribute to the project, you first need to *fork* the project to a repository on GitHub. A Github fork is just a copy of a repository. When you fork a repo, you are storing a copy of that repo on your personal account. This means you now have *write* access to edit files and develop the code. After making changes to the codebase -- squashing bugs, adding features, writing docs -- make a **Pull Request**. When you *pull* a branch, that's the git term for updating one set of code with more recently updated and/or new files. You can *pull* a branch you are working on from the github repo to get the most up-to-date copy locally, pull one branch into another to take certain *commits*, or pull in the reverse direction to bring your updates into the main repo. A pull request, therefore, is a request for the maintainers of the original repo to *review & merge* your edits into their version of the code on their repo.

But let’s do an actual example of this on the command line for reference.

.. note::
   
   In addition to performing the following steps on the commandline, as shown below, these steps to be carried out directly on Github.com and many popular text editors and IDEs have integrated tools to push & pull updates from the same environment you edit in.)

   Fork the repository.
   
   To fork the NSpyre repository, click the Fork button in the header of the repository.
   
   .. image:: images/Bootcamp-Fork.png
   
   Sit back and watch the forking magic. When it’s finished, you’ll be taken to your copy
   of the NSpyre repository. (As this is a GitHub specific step and not a git step, it can’t
   be completed with the git tool. However, checkout the hub command line tool for this and
   other useful extensions of the git tool https://hub.github.com).

.. code-block:: console

   # download a repository on GitHub.com to our machine
   git clone https://github.com/me/repo.git
   
   # change into the `repo` directory
   cd repo
   
   # create a new branch to store any new changes
   git branch my-branch
   
   # switch to that branch (line of development)
   git checkout my-branch
   
   # make changes, for example, edit `file1.md` and `file2.md` using the text editor

   # stage the changed files
   git add file1.md file2.md
   
   # take a snapshot of the staging area (anything that's been added)
   git commit -m "my snapshot"
   
   # push changes to github
   git push --set-upstream origin my-branch


That’s the gist on the workflow!

.. important::
   
   People save there code everywhere, in there documents folder, on their desktop, in a hidden folder. Not having a system to managing code is BAD. That's why git exists after all. Similarly, you want your code to be in a unified location on your local machine. Where it isn't in a place that someone will easily tamper with it, but in a location that is still easily accessible if you know where it is. To that end, we *highly* recommend that you create a directory at the root level of your local machine called ``SourceCode`` (or with whatever camalcase formatting your prefer). Create a new subdirectory for every project going forward. So for NSpyre, if you call ``git clone https://github.com/[username]/nspyre.git`` inside SourceCode, you will get a new directory called nspyre, containing your repo.

Next, search for a **branch** to check if someone has already started work on the issue of interest. If not, start one; make sure to give it a descriptive title so people easily understand what's being worked on (e.g. refactoring-pep8, awg-spyrelet, driver-gui-bug, etc).
A pull is the git term for pulling updated and/or new files from one version of a repo to another.

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

reStructuredText is an easy-to-read, what-you-see-is-what-you-get plaintext markup syntax and parser system. It is useful for inline program documentation (such as Python docstrings), for quickly creating simple web pages, and for standalone documents. Markdown is another, slightly simpler alternative. reStructuredText is a bit harder to use, but is more powerful.

There are plenty of good resources online, and cheat sheets to get you started:

* `An Introduction to reStructuredText <https://docutils.readthedocs.io/en/sphinx-docs/ref/rst/introduction.html>`_
* `A ReStructuredText Primer <https://docutils.readthedocs.io/en/sphinx-docs/user/rst/quickstart.html>`_

https://www.writethedocs.org/guide/writing/reStructuredText/



The reasons for using a markup language is straight-forward:

* easy to write and maintain
* still makes sense as plain text
* renders nicely into HTML

Don’t believe me? Then go .rst file for this webpage and see for yourself.

reStructuredText
^^^^^^^^^^^^^^^^

How to use reStructuredText

Formatting the main text
~~~~~~~~~~~~~~~~~~~~~~~~

There are many resources on rST syntax, but we've found it helpful to know these basic things when starting out (and as a quick refresher!).

Paragraphs in reStructuredText are blocks of text separated by at least one blank line. All lines in the paragraph must be indented by the same amount.

Indentation is important and mixing spaces and tabs causes problems. So just like Python, it's best to just use spaces. And typically, you want to **use three spaces**. Yes, you read that correctly. (A standard tab is equivalent to 4 spaces.)

Inline markup for font styles is similar to MarkDown:

* Use one asterisk (``*text*``) for *italics*.
* Use two asterisks (``**text**``) for **bolding**.
* Use two backticks (````text````) for ``code samples``.
* Use an underscore (``reference_``) for reference_.
* Use one backtick (```reference with whitespace`_``) for `reference with whitespace`_.
* Links to external sites contain the link text and a bracketed URL in backticks, followed by an underscore:
  ```Link to Write the Docs <https://www.writethedocs.org/>`_``.

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

  1. Use this format the numbers in your list like 1., 2., etc.

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

To display code samples, or any text that should not be formatted, end the paragraph prior to the code sample with two colons (``::``) and indent the code sample::

  This is the paragraph preceding the code sample::

    #some sample code

The is a lot that can be said about markdown, and many resources already available online (listed below). But here are some basics to get started.

Resources:

* `reStructuredText Primer <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_
* `Cheatsheet <https://github.com/ralsina/rst-cheatsheet>`_









Resources
---------

There’s a lot of online resources available for various aspects of software development. Below is a collection of the most useful as they pertain to development in this project. Hopefully they are useful to you as you get up to speed.

* https://guides.github.com
* https://cheat.readthedocs.io/en/latest/git.html
* https://dont-be-afraid-to-commit.readthedocs.io/en/latest/contributing.html
* https://gist.github.com/RichardBronosky/454964087739a449da04

