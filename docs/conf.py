# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.abspath('../'))

project = u''
copyright = u''
author = u''
version = u''
release = u''
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
]
source_suffix = '.rst'
master_doc = 'index'
language = None
exclude_patterns = [u'_build', 'Thumbs.db', '.DS_Store']
pygments_style = None
html_theme = 'sphinx_rtd_theme'
todo_include_todos = True
autodoc_default_options = { 
    'undoc-members': True,
    'private-members': False,
}
def setup(app):
    app.add_css_file('cleep.css')
    
