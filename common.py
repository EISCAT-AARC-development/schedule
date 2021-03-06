#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# site configuration options

import socket
import http.client
from email.utils import parsedate_tz, mktime_tz
from urllib.parse import unquote_plus as unqoute
from urllib.parse import quote_plus as quote
from conf import *
import os
import sys
import time
import re

os.umask(0o02)


sys.stderr = sys.stdout         # dump errors to browser
os.environ['TZ'] = 'UTC'        # deal only with Universal Time

english_weekdays = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
english_months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

def rfc1123(date):
    date = time.gmtime(date)
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (english_weekdays[date[6]], date[2], english_months[date[1] - 1], date[0], date[3], date[4], date[5])


def update_file(loc, net):
    '''check if an update is needed and in such case, download a new copy.
    The copy is downloaded to {loc}.new, before it is copied to the
    real position'''
    now = time.time()
    tmpfile = loc + ".new"
    showfile = os.path.basename(loc)
    try:
        # it is stalled in 5 minutes, assume previous download was killed
        if now - os.path.getmtime(tmpfile) < 300:
            print("<p>Downloading of a new" + showfile + "is in progress")
            return
    except EnvironmentError:
        pass
    try:
        timestamp = os.path.getmtime(loc)
    except EnvironmentError:
        timestamp = 0
    else:
        if now - timestamp < 7200:      # two hours
            return
    print("<p>Checking for updates of " + showfile + "...")
    sys.stdout.flush()
    # Last-Modified: Thu, 20 Jun 2002 10:23:54 GMT
    # Content-Length: 234255
    host, path = net.split('/', 1)
    try:
        conn = http.client.HTTPConnection(host)
        conn.putrequest("GET", "/"+path)
        conn.putheader("Cache-Control", "no-cache")
        if timestamp:
            conn.putheader("If-Modified-Since", rfc1123(timestamp))
        conn.endheaders()
        response = conn.getresponse()
        if response.status != 200:
            # file is not available on server
            print((response.reason))
            os.utime(loc, None)   # touch file
            return
        if timestamp:
            # check the timestamp
            netdate = mktime_tz(parsedate_tz(response.getheader("Last-Modified")))
            netsize = int(response.getheader("Content-Length"))
            # also check size
            if netsize == os.path.getsize(loc) and netdate <= timestamp:
                print("no update")
                os.utime(loc, None)   # touch file
                return
    except (EnvironmentError, socket.error) as why:
        print(why)
        return

    print("Starting download of new version of " + showfile + "<br>")
    # fork and do the download in background
    if os.fork(): return
    try:
        # "disconnect" from parent
        os.setsid()
        # close streams
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()
        # retrieve document
        outf = open(tmpfile, 'w')
        while 1:
            chunk = response.read(8192)
            if not chunk: break
            outf.write(chunk)
        outf.close()
        os.rename(tmpfile, loc)
    except Exception as why:
        import traceback
        f = open('errors', 'a')
        traceback.print_exc(f)
        f.write(str(why) + '\n')
        f.close()
        try: os.remove(tmpfile)
        except EnvironmentError: pass
    os._exit(0)

def print_copyright():
    print("<!--Last modified " + time.ctime(os.path.getmtime(sys.argv[0])) + "-->")
    print("<!--Copyright EISCAT Scientific Association " + time.strftime("%Y") + " -->")

# CFE 20200826: need logout link
def showLogout():
    print("<a href=\"/Shibboleth.sso/Logout\">Log out</a>")

if __name__ == '__main__':
    #when testing from commandline
    if sys.argv[0][0] == '.':
        os.environ['QUERY_STRING'] = sys.argv[1]
