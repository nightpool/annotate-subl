
import os, os.path, re

from ..lib import utils

def git_path_url(file_path):
    git_path = find_git(file_path)
    if not git_path:
        return # TODO: probably could do something better here but whatever.

    try:
        remote_hash, remote_order = read_config(os.path.join(git_path, 'config'))
    except IOError:
        return
    
    if not remote_hash:
        return

    url = None
    for i in ('github', 'origin'): # in order of most-to-least unique
        if i in remote_hash:
            url = normalize_url(remote_hash[i])
            break
    else:
        url = normalize_url(remote_hash[remote_order[0]])

    # print(url)
    return git_path, url

def find_git(file_path):
    git_path = None
    for path, folders, _ in utils.walk_up(os.path.dirname(file_path)):
        if '.git' in folders:
            git_path = os.path.join(path, '.git')
            break
    return git_path

re_config_remote = re.compile(r'\[remote "(.*)"\]')
re_config_url = re.compile(r'\s*url\s*=\s*(.*)')
re_config_non_remote = re.compile(r'\s*\[.*\]')
def read_config(config_path):
    config = open(config_path)
    in_remote = None
    remote_hash = {}
    remote_order = []
    for i in config:
        remote_m = re_config_remote.match(i)
        if remote_m:
            in_remote = remote_m.group(1)
            continue

        non_remote_m = re_config_non_remote.match(i)
        if non_remote_m:
            in_remote = None
            continue

        if in_remote:
            url_m = re_config_url.match(i)
            if url_m:
                remote_hash[in_remote] = url_m.group(1)
                remote_order.append(in_remote)
    config.close()
    return remote_hash, remote_order

def normalize_url(url):
    url = re.sub(r'//.*@', '//', url) # strip out a user (i.e. git@github.com)
    url = re.sub(r'.*://', '', url) # strip out the protocol
    return "http://annotate-subl.herokuapp.com/ref/{}".format(url) # TODO: better to redirect to something like nightpool.me/??