import sublime_plugin, sublime

import os, os.path, re, webbrowser, string, random, difflib
import requests
from urllib.parse import quote as url_quote
from itertools import chain

from .lib import git
from .lib.utils import debounce
from . import views, lorem

files = {}

class GeniusBuffer(object):
    def __init__(self, url, view, title):
        self.url = url
        self.view = view
        self.title = title
        self.referents = []
    def id(self):
        if not hasattr(self, '_id'):
            resp = api().get(api_url("/web_pages/lookup",
                {"canoncial_url": self.url,
                 "raw_annotatable_url": self.url}))
            print(resp.json())
            self._id = resp.json()['response']['web_page']['id']
        return self._id
    def fetch_referents(self):
        page = 1
        if not self.id():
            return
        while True:
            res = api().get(api_url("/referents",
             query={"web_page_id": self.id(), "text_format": "html", "per_page":20, "page":page}))
            _ref = res.json()['response']['referents']
            if not _ref:
                break
            for i in _ref:
                self.referents.append(Referent.from_json(self, i))
            page += 1
        self.anchor_referents()
    def add_referent(self, referent):
         self.referents.append(referent)
         self.anchor_referents()
    def anchor_referents(self):
        lines = self.view.substr(sublime.Region(0, self.view.size())).splitlines()
        # matchers = [difflib.SequenceMatcher(lambda x: x in " \t", b=i) for i in lines]
        for i in self.referents:
            if not i.anchored_range:
                line = i.context[0] + i.fragment + i.context[1]
                reg = self.view.find(line, 0, sublime.LITERAL | sublime.IGNORECASE)
                if reg:
                    i.anchored_range = sublime.Region(
                        reg.begin() + len(i.context[0]), reg.end() - len(i.context[1]))
                    continue
                # else:
                #     for i in matchers: i.set_seq1(line)

        self.view.add_regions('genius:anchored', [i.anchored_range for i in self.referents if i.anchored_range], "comment", "bookmark", region_flags)

region_flags = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SOLID_UNDERLINE
class Referent(object):
    def __init__(self, **args):
        self.buffer = args['buffer']
        self.fragment = args["fragment"]
        self.annotation = args.get("annotation")

        self.anchored_range = args.get("anchored_range")
        self.id = args.get("id")
    def contains(self, point):
        return self.anchored_range.contains(point) if self.anchored_range else None
    @property
    def context(self):
        if hasattr(self, '_context'):
            return self._context
        if not self.anchored_range:
            return None
        a, b = self.anchored_range.begin(), self.anchored_range.end()
        view = self.buffer.view
        start_of_line = view.classify(a) == CLASS_LINE_START
        end_of_line = view.classify(b) == CLASS_LINE_END
        before_region = (sublime.Region(view.find_by_class(a, False, sublime.CLASS_LINE_START), a) 
            if not start_of_line else sublime.Region(a,a))
        after_region = (sublime.Region(b, view.find_by_class(b, True, sublime.CLASS_LINE_END))
            if not end_of_line else sublime.Region(b,b))
        self._context = (view.substr(before_region), view.substr(after_region))
        return self._context
    def to_payload(self):
        return {"raw_annotatable_url": self.buffer.url,
                "fragment": self.fragment,
                "context_for_display": {
                    "before_html": self.context[0],
                    "after_html": self.context[1]},
                "range": {
                    "before": self.context[0],
                    "after": self.context[1]}}
    @staticmethod
    def from_json(buffer, json):
        print(json)
        fragment = json['range']['content']
        id = json['id']
        self = Referent(buffer=buffer, fragment=fragment, id=id)
        self.annotation = Annotation.from_json(self, json['annotations'][0])
        self._context = (json['range']['before'], json['range']['after'])
        return self

class Annotation(object):
    def __init__(self, **args):
        self.referent = args['referent']
        self.user = args['user']
        self.id = args.get('id')
        self.body = args.get('body')
        self.html = args.get('html')
        if not (self.body or self.html): raise ValueError("need one of body or html")
    def user_login(self):
        if hasattr(self, 'json'):
            return self.json['verified_by']['login']
        return self.user
    def show(self, view):
        def navigate(link):
            if "user/" in link:
                webbrowser.open("http://genius.com/{}".format(self.user_login()))
            elif link == "edit":
                sublime.error_message("not yet implemented")
            elif link == "delete":
                sublime.error_message("not yet implemented")
            elif link == "replies":
                sublime.error_message("not yet implemented")
        views.show_popup(view, "annotation_view",
            user = self.user,
            annotation_html = self.html if self.html else self.body,
            dashes = views.annotation_dashes(self.user), on_navigate=navigate)
    def publish(self):
        payload = {
            "annotation": {"body": {"markdown": self.body}},
            "referent": self.referent.to_payload(),
            "web_page": {"canoncial_url": self.referent.buffer.url, "title":self.referent.buffer.title}
        }
        print(repr(payload))
        resp = api().post(api_url("/annotations"), {'text_format':'html'}, json=payload)
        print(resp.json())
        self.id = resp.json()['response']['annotation']['id']
        self.html = resp.json()['response']['annotation']['body']['html']
    @staticmethod
    def from_json(referent, json):
        html = json['body']['html']
        user = json['authors'][0]['user']['name']
        id = json['id']
        self = Annotation(referent=referent, id=id, user=user, html=html)
        self.json = json
        return self

class ClickHandler(sublime_plugin.EventListener):
    def __init__(self):
        self.click_sel = None
        self.annotate_open = False
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
        elif len(view.sel()) == 1 and view.sel()[0]:
            if get_settings().get("show-popup") and view.buffer_id() in files:
                self.show_annotate(view)
        elif self.annotate_open:
            view.hide_popup()
    @debounce(1)
    def show_annotate(self, view):
        if len(view.sel()) == 1 and view.sel()[0]:
            self.annotate_open = True
            views.show_popup(view, "annotate_view", on_navigate=self.annotate(view), on_hide=self.clear_open)
    def clear_open(self):
        self.annotate_open = False
    def annotate(self, view):
        def nav(link):
            view.hide_popup()
            view.run_command("genius_annotate")
        return nav
    def click(self, view, sel):
        buf = files.get(view.buffer_id())
        if buf:
            for i in buf.referents:
                if i.contains(sel):
                    i.annotation.show(view)
                    break

class GeniusAnnotateCommand(sublime_plugin.TextCommand):
    text = "Write your annotation below (press esc when done):\n--------------------------------------------------\n"
    def run(self,edit):
        n = self.view.sel()
        if not n or not n[0]:
            views.show_popup(self.view, "error_view", 
                error=views.center("You must to select something to begin annotating!",55), dashes="-"*55)
            return
        if len(n) > 1:
            views.show_popup(self.view, "error_view", 
                error=views.center("Annotation referents need to be continuous!",50), dashes="-"*50)
            return
        if self.view.buffer_id() not in files:
            print("not a genius file")
            return
        window = self.view.window()
        annotation_panel = window.create_output_panel("genius:create")
        annotation_panel.run_command("genius_write",
         {"text":self.text})
        self.sel = n[0]
        self.view.sel().clear()
        window.run_command("show_panel",{"panel":"output.genius:create"})
        window.focus_view(annotation_panel)
        new_callback(annotation_panel.id(), self.finish_create)
    def finish_create(self, view):
        text = view.substr(sublime.Region(0, view.size()))
        text = text.replace(self.text, '').strip()
        if not text:
            views.show_popup(self.view, "error_view",
                error=views.center("Annotation cancelled",20), dashes="-"*20)
            sublime.set_timeout(lambda: self.view.hide_popup(), 2000)
            return
        ref = Referent(buffer=files[self.view.buffer_id()],
            fragment=self.view.substr(self.sel), anchored_range=self.sel)
        anno = Annotation(referent=ref, body=text, user=get_settings().get("login"))
        ref.annotation = anno
        ref.context
        sublime.set_timeout_async(lambda: anno.publish())
        ref.buffer.add_referent(ref)

callbacks = {}
def new_callback(id, callback):
    global callbacks
    l = callbacks.get(id, [])
    l.append(callback)
    callbacks[id] = l
def pop_callbacks(id):
    global callbacks
    l = callbacks[id]
    del callbacks[id]
    return l
class PanelEvents(sublime_plugin.EventListener):
    def on_deactivated(self, view):
        if view.id() in callbacks:
            for i in pop_callbacks(view.id()):
                i(view)

class BufferTestCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.new_file()
        view.set_name("Annotate Subl")
        view.set_scratch(True)
        s = sublime.load_resource("Packages/annotate/templates/test_template")
        buf = GeniusBuffer("http://dummy.url/{}".format(random.randint(0,100000)),
                            view, title="dummy test file")
        print(buf.url)
        files[view.buffer_id()] = buf
        referents = []
        for match in re.finditer(r'\[(.*?)\]\(\)', s):
            x, y = match.span()
            n = 4*len(referents)
            ref = Referent(buffer = buf, fragment = match.group(1),
                anchored_range = sublime.Region(x-n, y-n-4))
            anno = Annotation(user = "nightpool", body = lorem.ipsum(), referent=ref)
            ref.annotation = anno
            referents.append(ref)
        files[view.buffer_id()].referents = referents
        text = re.sub(r'\[(.*?)\]\(\)', r'\1', s)
        view.run_command('genius_write', {"text": text})
        files[view.buffer_id()].anchor_referents()

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
        files[view.buffer_id()] = GeniusBuffer(url, view, title=path)
        sublime.set_timeout_async(lambda: files[view.buffer_id()].fetch_referents())
        flash(view, str(url))

class GeniusAuthorizeCommand(sublime_plugin.WindowCommand):
    def run(self):
        settings = get_settings()

        client_id = settings.get("client-id")
        redirect_uri = settings.get("redirect-uri")
        
        params = {"client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "me create_annotation manage_annotation vote", 
            "state": "install",
            "response_type": "code"}

        print(api_url("oauth/authorize", params))
        webbrowser.open(api_url("oauth/authorize", params))

        def done(str):
            def verify():
                resp = requests.get(api_url("account"), params={"access_token": str})
                if not resp:
                    sublime.set_timeout(retry)
                    return
                login = resp.json()['response']['user']['login']
                settings.set("login", login)
                settings.set("oauth-token", str)
                settings.set("canceled-auth", False)
                save_settings()
            sublime.set_timeout_async(verify)
        def retry():
            res = sublime.ok_cancel_dialog("Unfortunately, that OAuth code doesn't seem to work\n\nTry again?", "Log-in")
            if not res:
                cancel()
            else:
                sublime.set_timeout(lambda: sublime.active_window().run_command("genius_authorize"), 0)
        def cancel():
            res = sublime.ok_cancel_dialog("The Genius plugin will run in read-only mode until you log in.\
                \n\nYou may re-authenticate at any time from the command pallet.", "Log-in")
            if res:
                sublime.set_timeout(lambda: sublime.active_window().run_command("genius_authorize"), 0)
            else:
                settings.set("canceled-auth", True)
                save_settings()
        self.window.show_input_panel("OAuth Token: ", "", done, None, cancel)

    def is_visible(self):
        return not get_settings().has("oauth-token")

# class VerifyOauthCommand(sublime_plugin.WindowCommand):
#     def run(self):
#         resp = requests.get(api("account"), headers=)

def plugin_loaded():
    settings = get_settings()
    
    if not (settings.has("oauth-token") or settings.get("canceled-auth", False)):
        sublime.active_window().run_command("genius_authorize")
    elif not settings.has("oauth-token"):
        for i in chain.from_iterable(j.views() for j in sublime.windows()):
            # print(i)
            flash(i, "[Genius] Warning: Not logged in!", 5000)

def flash(view, msg, timeout=3000):
    n = str(random.getrandbits(20))
    sublime.set_timeout(lambda: view.set_status(n, msg), 0)
    sublime.set_timeout(lambda: view.erase_status(n), timeout)

def get_settings():
    return sublime.load_settings("Annotate.sublime-settings")

def save_settings():
    return sublime.save_settings("Annotate.sublime-settings")

def api_url(path, query=None):
    api_path = get_settings().get("api-path").rstrip('/')
    path = path.lstrip('/')
    query_str = "&".join( "{}={}".format(url_quote(str(k), safe=''), url_quote(str(v), safe='')) for k,v in query.items()) if query else None
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
