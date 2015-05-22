import sublime_plugin, sublime

import os, os.path, re, webbrowser
from urllib.parse import quote as url_quote

from annotate import git

files = {}

class GeniusBuffer(object):
    def __init__(self, url):
        self.url = url

class ShowRemotes(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        if not view.file_name():
            return

        if view.buffer_id() in files:
            return

        self.load_buffer(view)
    
    def on_load_async(self, view):
        self.load_buffer(view)

    def load_buffer(self, view):
        buffer_path = view.file_name()

        url = git.git_url(buffer_path)

        if not url: return

        files[view.buffer_id()] = GeniusBuffer(url)

        flash(view, str(url))

class GeniusAuthorizeCommand(sublime_plugin.WindowCommand):
    def run(self):
        settings = sublime.load_settings("Annotate.sublime-settings")

        api_path = settings.get("api-path")
        client_id = settings.get("client-id")
        redirect_uri = settings.get("redirect-uri")
        
        params = {"client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "me create_annotation", 
            "state": "install",
            "response_type": "code"}

        query = "&".join( "{}={}".format(url_quote(k), url_quote(v)) for k,v in params.items())
        
        url = "{}/oauth/authorize?{}".format(api_path, query)

        # print(url)
        webbrowser.open(url)
        

region_flags = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SOLID_UNDERLINE

def plugin_loaded():
    settings = sublime.load_settings("Annotate.sublime-settings")
    print(settings.get("api-path"))
    if not settings.has("oauth-token"):
        sublime.active_window().run_command("genius_authorize")

def flash(view, msg, timeout=3000):
    import random; n = str(random.getrandbits(20))
    sublime.set_timeout(lambda: view.set_status(n, msg), 0)
    sublime.set_timeout(lambda: view.erase_status(n), timeout)
