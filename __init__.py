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
from mercurial import ui
from mercurial import extensions
from mercurial.hgweb import hgweb_mod
from mercurial.hgweb import hgwebdir_mod

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
    time.sleep(3)
    server.close()
    for v in l.found.values():
        n = v.name[:v.name.index('.')]
        n.replace(" ", "-")
        u = "%s" % (v.properties.get("uri", None))
        yield "bjr-" + n, u

def config(orig, self, section, key, default=None, untrusted=False):
    if section == "paths" and key.startswith("bjr-"):
        for n, p in getzcpaths():
            if n == key:
                return p
    return orig(self, section, key, default, untrusted)

def configitems(orig, self, section, untrusted=False):
    r = orig(self, section, untrusted)
    if section == "paths":
        r += getzcpaths()
    return r

extensions.wrapfunction(ui.ui, 'config', config)
extensions.wrapfunction(ui.ui, 'configitems', configitems)
