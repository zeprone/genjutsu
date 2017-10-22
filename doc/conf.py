#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys

import sphinx_bootstrap_theme
from recommonmark.parser import CommonMarkParser
from recommonmark.transform import AutoStructify

sys.path.extend((Path(__file__).parent / path).resolve() for path in ('..', '../genjutsu', '../msbuild_gen'))

from genjutsu import __version__ as genjutsu_version


# -- General configuration ------------------------------------------------

extensions = ['sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
    'breathe']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

source_suffix = ['.md']

source_parsers = {
    '.md': CommonMarkParser
}

master_doc = 'index'

project = 'genjutsu'
version = genjutsu_version
release = '20170304'
author = 'ligne-R'
copyright = '2017, ligne-R'

language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'vim'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'bootstrap'
html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()

# (Optional) Logo. Should be small enough to fit the navbar (ideally 24x24).
# Path should be relative to the ``_static`` files directory.
html_logo = 'my_logo.png'

# Theme options are theme-specific and customize the look and feel of a
# theme further.
html_theme_options = {
    # Navigation bar title. (Default: ``project`` value)
    'navbar_title': 'Genjutsu / 幻術',

    # Tab name for entire site. (Default: 'Site')
    'navbar_site_name': 'Site',

    # A list of tuples containing pages or urls to link to.
    # Valid tuples should be in the following forms:
    #    (name, page)                 # a link to a page
    #    (name, '/aa/bb', 1)          # a link to an arbitrary relative url
    #    (name, 'http://example.com', True) # arbitrary absolute url
    # Note the '1' or 'True' value above as the third argument to indicate
    # an arbitrary url.
    'navbar_links': [
        ('API', 'genjutsu'),
        ('Github', 'http://github.com/ligne-r/genjutsu', True),
    ],

    # Tab name for the current pages TOC. (Default: 'Page')
    'navbar_pagenav_name': 'Page',

    # Global TOC depth for 'site' navbar tab. (Default: 1)
    # Switching to -1 shows all levels.
    'globaltoc_depth': 2,

    # Include hidden TOCs in Site navbar?
    #
    # Note: If this is 'false', you cannot have mixed ``:hidden:`` and
    # non-hidden ``toctree`` directives in the same page, or else the build
    # will break.
    #
    # Values: 'true' (default) or 'false'
    'globaltoc_includehidden': 'true',

    # HTML navbar class (Default: 'navbar') to attach to <div> element.
    # For black navbar, do 'navbar navbar-inverse'
    'navbar_class': 'navbar navbar-inverse',

    # Location of link to source.
    # Options are 'nav' (default), 'footer' or anything else to exclude.
    'source_link_position': 'nav',

    # Bootswatch (http://bootswatch.com/) theme.
    #
    # Options are nothing (default) or the name of a valid theme
    # such as 'amelia' or 'cosmo'.
    'bootswatch_theme': 'readable',

    # https://pikock.github.io/bootstrap-magic/
}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named 'default.css' will overwrite the builtin 'default.css'.
html_static_path = ['static_html']

# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'genjutsudoc'

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, project, 'genjutsu Documentation',
     [author], 1)
]

breathe_projects = { 'genjutsu': 'xml' }
breathe_projects_source = {
     'genjutsu': ('../genjutsu', ['genjutsu.py'])
     }
breathe_default_project = 'genjutsu'

napoleon_use_admonition_for_examples = True

github_doc_root = 'https://github.com/rtfd/recommonmark/tree/master/docs/'

def setup(app):
    app.add_config_value('recommonmark_config', {
            'url_resolver': lambda url: github_doc_root + url,
            'auto_toc_tree_section': 'Contents',
            }, True)
    app.add_transform(AutoStructify)