import sublime_plugin, sublime

import os, os.path, re, webbrowser
from urllib.parse import quote as url_quote
from itertools import chain

from annotate.lib import git
from annotate.lib import plist_parser as parser

files = {}

class GeniusBuffer(object):
    def __init__(self, url):
        self.url = url
    def id(self):
        if "dummy" in url: return -1
        if not hasattr(self, '_id'):
            resp = api().get(api_url("/web_pages/lookup",
                {"canoncial_url": url}))
            self._id = None
    @property
    def referents(self):
        if hasattr(self, '_referents'):
            return self._referents
        else:
             return []

region_flags = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SOLID_UNDERLINE
class Referent(object):
    def __init__(self, **args):
        self.id = args["id"]
        self.fragment = args["fragment"]
        self.range = args["range"]
        self.pos = (self.range.begin(), self.range.end())
    def contains(self, point):
        return point >= self.pos[0] and point <= self.pos[1]

class ClickHandler(sublime_plugin.EventListener):
    def __init__(self):
        self.click_sel = None
    def on_post_text_command(self, view, name, args):
        if name == "drag_select":
            event = args['event']
            if event['button'] == 1 and len(args) == 1:
                click_sel = view.sel()[0]
                if len(click_sel) == 0:
                    self.click_sel = click_sel
                    def clear():
                        self.click_sel = None
                    sublime.set_timeout(clear, 3000)
    def on_selection_modified(self, view):
        # print(type(self.click_sel))
        # if self.click_sel is not None: print(len(view.sel()[0]),view.sel()[0].contains(self.click_sel))
        if self.click_sel is not None and len(self.click_sel) == 0 and view.sel()[0] == self.click_sel:
            sublime.set_timeout(lambda: self.click(view, view.sel()[0].a))
            self.click_sel = None
    def click(self, view, sel):
        buf = files.get(view.buffer_id())
        if buf:
            n = None
            for i in buf.referents:
                n = i if i.contains(sel) else n
            if n:
                view.show_popup('Hello, <b>World!</b><br><a href="moo">Click Me</a>', on_navigate=print)

annotation_view = """
    <div id="container">
        <div id="byline>
"""

class BufferTestCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.new_file()
        view.set_name("Annotate Subl")
        view.set_scratch(True)
        s = sublime.load_resource("Packages/annotate/lib/test_template")
        files[view.buffer_id()] = GeniusBuffer("dummy_url")
        referents = []
        for match in re.finditer(r'\[(.*?)\]\(\)', s):
            print(match.group(1))
            x, y = match.span()
            n = 4*len(referents)
            ref = Referent(id = len(referents), fragment = match.group(1), range = sublime.Region(x-n, y-n-4))
            referents.append(ref)
        files[view.buffer_id()]._referents = referents
        text = re.sub(r'\[(.*?)\]\(\)', r'\1', s)
        view.run_command('genius_write', {"text": text})
        for i in referents:
            view.add_regions('genius#{}'.format(i.id), [i.range], "comment", "bookmark", region_flags)

class GeniusWriteCommand(sublime_plugin.TextCommand):
    def run(self, edit, text):
        self.view.insert(edit, 0, text)

class LoadBuffer(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        if not view.file_name():
            return

        if view.buffer_id() in files:
            return

        self.load_buffer(view)
    
    def on_load_async(self, view):
        self.load_buffer(view)

    def load_buffer(self,view):
        buffer_path = view.file_name()

        out = git.git_path_url(buffer_path)

        if not out: return

        git_path, git_url = out

        git_path = os.path.dirname(git_path)
        path = os.path.relpath(buffer_path, git_path)
        url = "{}/{}".format(git_url, path)
        print(url)
        files[view.buffer_id()] = GeniusBuffer(url)

        flash(view, str(url))

class GeniusAuthorizeCommand(sublime_plugin.WindowCommand):
    def run(self):
        settings = get_settings()

        client_id = settings.get("client-id")
        redirect_uri = settings.get("redirect-uri")
        
        params = {"client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "me create_annotation", 
            "state": "install",
            "response_type": "code"}

        print(api_url("oauth/authorize"))
        # webbrowser.open(api("oauth/authorize"))

        def done(str):
            settings.set("oauth-token", str)
            save_settings()
            # sublime.set_timeout(lambda: sublime.active_window().run_command("verify_oauth"), 0)
        def cancel():
            res = sublime.ok_cancel_dialog("The Genius plugin will run in read-only mode until you log in.\
                \n\nYou may re-authenticate at any time from the command pallet.", "Log-in")
            if res:
                sublime.set_timeout(lambda: sublime.active_window().run_command("genius_authorize"), 0)
            else:
                settings.set("canceled-auth", True)
                save_settings()
        self.window.show_input_panel("OAuth Token: ", "", done, None, cancel)

# class VerifyOauthCommand(sublime_plugin.WindowCommand):
#     def run(self):
#         resp = requests.get(api("account"), headers=)

def plugin_loaded():
    settings = get_settings()
    
    if not (settings.has("oauth-token") or settings.has("canceled-auth")):
        sublime.active_window().run_command("genius_authorize")
    elif not settings.has("oauth-token"):
        for i in chain.from_iterable(j.views() for j in sublime.windows()):
            # print(i)
            flash(i, "[Genius] Warning: Not logged in!", 5000)

def flash(view, msg, timeout=3000):
    import random; n = str(random.getrandbits(20))
    sublime.set_timeout(lambda: view.set_status(n, msg), 0)
    sublime.set_timeout(lambda: view.erase_status(n), timeout)

def get_settings():
    return sublime.load_settings("Annotate.sublime-settings")

def save_settings():
    return sublime.save_settings("Annotate.sublime-settings")

def api_url(path, query=None):
    api_path = get_settings().get("api-path").rstrip('/')
    path = path.lstrip('/')
    query_str = "&".join( "{}={}".format(url_quote(k, safe=''), url_quote(v, safe='')) for k,v in query.items()) if query else None
    url = "{}/{}?{}".format(api_path, path, query_str) if query_str else "{}/{}".format(api_path, path)
    return url

_session = None
_session_has_token = False
def api():
    global _session, _session_has_token
    if not _session:
        _session = requests.Session()
    if not _session_has_token and get_settings().has("oauth-token"):
        _session.headers.update({
            "Authorization":"Bearer {}".format(get_settings().get("oauth-token"))
        })
        _session_has_token = True
    return _session

