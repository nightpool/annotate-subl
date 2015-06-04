
# Annotate Sublime

Annotate Sublime requires [sublime package control](https://packagecontrol.io/installation) and [sublime 3](http://www.sublimetext.com/3). Install those first.

To add this package to sublime, first select "`Package Control: Add Repository`", and then paste the link to this github repo.

After you've added the repository, select "`Package Control: Install Package`", and select "`annotate-subl`" from the list. After installing, Sublime will prompt you to authorize annotate-subl with Genius.

**caveat emptor!** current weird memes:

 - Right now annotate-subl figures out which text document is which using git remotes. So, to be able to annotate your file, it needs to be controlled by git and contain a git remote point to *somewhere*.
 - Multi-line annotations don't anchor right now for some reason.

# todo:

 - make multi-line annotations work!
 - get edit/delete/replies implemented
 - some url-like indentifier embedded in the file so you don't have to use git!
 - maybe some sort of summary like meme at annotate-subl.herokuapp.com/ref/*? can I just redirect to genius.com/summary? that seems like the right idea.
 - fuzzy string matching in anchoring!
 - some sort of introductory meme/explanatory page

# Oauth server

if you want to set up your own heroku server and API client, push the oauth server to heroku using a subtree push:

    git subtree push --prefix oauth-server heroku master
