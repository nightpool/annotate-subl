
import sublime
import string

from .lib import plist_parser as parser

annotation_view = string.Template("""
    <style>
        body {
            background-color: $bg_color;
            color: $fg_color;
            margin: 0;
        }
        #container {
            margin: 1em;
        }
        #annotation {
            margin-bottom: 1em;
        }
        #controls {
            margin-top: 0.3em;
        }
        a {
            color: $fg_color;
        }
        p {
            margin-top: 0;
        }
    </style>
    <div id="container">
        <div id="annotation"> $annotation_html </div>
        <div id="seperator"> $dashes </div>
        <div id="controls">
            annotation by <a id="user_link" href="user/$user">$user</a>&nbsp;&nbsp;&nbsp;&nbsp;
            <a href="edit">edit</a>&nbsp;
            <a href="delete">delete</a>&nbsp;
            <a href="replies">replies</a>&nbsp;
        </div>
    </div>
""")
def annotation_dashes(n): return '-'*len("annotation by {}     edit  delete  replies".format(n))

error_view = string.Template("""
    <style>
        body {
            background-color: $bg_color;
            color: $fg_color;
            margin: 0;
        }
        #container {
            margin: 1em;
        }
        #annotation {
            margin: 1em 0;
        }
        #controls {
            margin-top: 0.3em;
        }
        a {
            color: $fg_color;
        }
    </style>
    <div id="container">
        <div id="seperator"> $dashes </div>
        <div id="annotation"> $error </div>
        <div id="seperator"> $dashes </div>
    </div>""")

sgnarly_view = string.Template("""
<style>
    html {
        background-color:black;
        margin:0;
    }
    body {margin:5px}
</style>
<a href="annotate">
    <img src="res://Packages/annotate/sgnarly-large.png">
</a>""")

annotate_view = string.Template("""
<style>
    html {
        background-color: black;
        margin: 0;
    }
    a {
        color: yellow;
        display: block;
        padding: 5px;
    }
    body {margin:0}
</style>
<a href="annotate">
    annotate!
</a>""")

def center(st, n): return st.center(n, " ").replace(" ","&nbsp;")

def show_popup(view, name, location = -1,
        max_width = 500, max_height = 500,
        on_navigate = None, on_hide = None, template_args=None, **kwargs):
    if name not in globals() or not isinstance(globals()[name], string.Template): raise ValueError("{} is not a template".format(name))
    template = globals()[name]
    if not template_args: template_args = {}
    template_args.update(kwargs)
    args = {
        'bg_color': theme_colors()[0],
        'fg_color': theme_colors()[1]
    }
    args.update(template_args)
    content = template.substitute(args)
    view.show_popup(content, 0, location, max_width, max_height, on_navigate, on_hide)

_theme_colors = None
def theme_colors():
    global _theme_colors
    if not _theme_colors:
        _theme_colors = parser.get_colors(sublime.load_settings("Preferences.sublime-settings").get("color_scheme"))
    return _theme_colors

def plugin_loaded():
    def clear_colors():
        global _theme_colors
        _theme_colors = None
    sublime.load_settings("Preferences.sublime-settings").add_on_change("color_scheme", clear_colors)