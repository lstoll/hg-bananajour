# zeroconf.py - zeroconf support for Mercurial
#
# Copyright 2005-2007 Matt Mackall <mpm@selenic.com>
# Portions Copyright 2009 Lincoln Stoll <lstoll@lstoll.net>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2, incorporated herein by reference.

'''discover and advertise repositorys in git format with bananajour

You can discover banajour repositories by running "hg paths".

 $ hg paths
 bjr-repo1 = git://linc.local/repo1.git
 
This can then be cloned

 $ hg clone bjr-repo1

'''

import Zeroconf, socket, time, os
from mercurial import ui, hg
from mercurial import extensions
from mercurial.hgweb import hgweb_mod
from mercurial.hgweb import hgwebdir_mod
from mercurial.i18n import _
from dulwich.repo import Repo

hg_bananajour_curr_repo = None
hg_bananajour_reponame = None

def getip():
    # finds external-facing interface without sending any packets (Linux)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('1.0.0.1', 0))
        ip = s.getsockname()[0]
        return ip
    except:
        pass

    # Generic method, sometimes gives useless results
    try:
        dumbip = socket.gethostbyaddr(socket.gethostname())[2][0]
        if not dumbip.startswith('127.') and ':' not in dumbip:
            return dumbip
    except socket.gaierror:
        dumbip = '127.0.0.1'

    # works elsewhere, but actually sends a packet
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('1.0.0.1', 1))
        ip = s.getsockname()[0]
        return ip
    except:
        pass

    return dumbip

# listen

class listener(object):
    def __init__(self):
        self.found = {}
    def removeService(self, server, type, name):
        if repr(name) in self.found:
            del self.found[repr(name)]
    def addService(self, server, type, name):
        self.found[repr(name)] = server.getServiceInfo(type, name)

def getzcpaths():
    ip = getip()
    if ip.startswith('127.'):
        return
    server = Zeroconf.Zeroconf(ip)
    l = listener()
    Zeroconf.ServiceBrowser(server, "_git._tcp.local.", l)
    # for some reason bananjour is slower here - so we wait for 3 seconds.
    # Todo - why does it need to be this long?
    time.sleep(5)
    server.close()
    for v in l.found.values():
        n = v.name[:v.name.index('.')]
        n.replace(" ", "-")
        u = "%s" % (v.properties.get("uri", None))
        yield "bjr-" + n, u

def config(orig, self, section, key, default=None, untrusted=False):
    # one of the discovered paths
    if section == "paths" and key.startswith("bjr-"):
        for n, p in getzcpaths():
            if n == key:
                return p
    if bjrepo():
        if section == "paths" and key == "bananajour":
            # we are currently in a repo, and the path for banajour is 
            # being requested. so return it.
            return bjrepo()
    return orig(self, section, key, default, untrusted)

def configitems(orig, self, section, untrusted=False):
    r = orig(self, section, untrusted)
    if section == "paths":
        r += getzcpaths()
        # check ~/.bananajour/repositories for a repo with the same name as
        # ours. if it is, list that as a path
        if bjrepo():
          r += [('banajour', bjrepo())]
    return r
    
def bjrepo():
    if hg_bananajour_curr_repo:
        bjrepo = os.path.expanduser('~/.bananajour/repositories/') + hg_bananajour_reponame + '.git'
        if os.path.isdir(bjrepo):
          return bjrepo
        # try again, this time assume we already have the .git
        bjrepo = os.path.expanduser('~/.bananajour/repositories/') + hg_bananajour_reponame
        if os.path.isdir(bjrepo):
          return bjrepo

def bjadd(ui, repo):
    # we need to do whatever it is bananjour add does. i suspect
    # it's just a git init. if so, do the same, and print a message
    if hg_bananajour_curr_repo:
        bj_repo_dir = os.path.expanduser('~/.bananajour/repositories/')
        repo_dir = bj_repo_dir + hg_bananajour_reponame + '.git'
        if os.path.isdir(repo_dir):
            ui.write ("This repository already exists!")
            ui.write ("If you want to push to this repository, try hg push bananajour")
            ui.write ("Otherwise, delete it before re-creating")
            exit()
        else:
            os.makedirs(repo_dir)
            Repo.init_bare(repo_dir)
            ui.write ("Repository added to bananajour")
            ui.write ("Run hg push bananajour to add your commits, and to update!")
    else:
        ui.write("You need to run this command from within a repository")
        exit()

extensions.wrapfunction(ui.ui, 'config', config)
extensions.wrapfunction(ui.ui, 'configitems', configitems)

# We need to hook in here to get a repo for later.
def reposetup(ui, repo):
  global hg_bananajour_curr_repo, hg_bananajour_reponame
  if hasattr(repo, 'root'):
      hg_bananajour_curr_repo = repo
      hg_bananajour_reponame = os.path.basename(repo.root)

cmdtable = {
  "bananajour-add":
        (bjadd, [], _('hg bananajour-add')),
}
