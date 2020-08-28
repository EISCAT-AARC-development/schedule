# -*- coding: utf-8 -*-
# site configuration options
from conf import *

# some common used cgi routines

import os, sys, time, re

os.umask(002)

#when testing from commandline
if sys.argv[0][0] == '.':
	os.environ['QUERY_STRING'] = sys.argv[1]

sys.stderr = sys.stdout 	# dump errors to browser
os.environ['TZ'] = 'UTC'	# deal only with Universal Time

english_weekdays = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
english_months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct","Nov", "Dec")

def rfc1123(date):
	date = time.gmtime(date)
	return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (english_weekdays[date[6]], date[2], english_months[date[1] - 1], date[0], date[3], date[4], date[5])

import rfc822, httplib, socket

def update_file(local, net):
	"check if an update is needed and in such case, download a new copy"
	"The copy is downloaded to {local}.new, before it is copied to the"
	"real position"
	now = time.time()
	tmpfile = local+".new"
	showfile = os.path.basename(local)
	try:
		# it is stalled in 5 minutes, assume previous download was killed
		if now - os.path.getmtime(tmpfile) < 300:
			print "<p>Downloading of a new", showfile, "is in progress"
			return
	except EnvironmentError:
		pass

	try:
		timestamp = os.path.getmtime(local)
	except EnvironmentError:
		timestamp = 0
	else:
		if now - timestamp < 7200:	# two hours
			return

	print "<p>Checking for updates of ",showfile+"..."
	sys.stdout.flush()
	# Last-Modified: Thu, 20 Jun 2002 10:23:54 GMT
	# Content-Length: 234255
	host, path = net.split('/', 1)
	try:
		conn = httplib.HTTPConnection(host)
		conn.putrequest("GET", "/"+path)
		conn.putheader("Cache-Control", "no-cache")
		if timestamp:
			conn.putheader("If-Modified-Since", rfc1123(timestamp))
		conn.endheaders()
		response = conn.getresponse()
		if response.status <> 200:
			# file is not available on server
			print response.reason
			os.utime(local, None)	# touch file
			return
		if timestamp:
			# check the timestamp
			netdate = rfc822.mktime_tz(rfc822.parsedate_tz(response.getheader("Last-Modified")))
			netsize = int(response.getheader("Content-Length"))
			# also check size
			if netsize == os.path.getsize(local) and netdate <= timestamp:
				print "no update"
				os.utime(local, None)	# touch file
				return
	except (EnvironmentError, socket.error), why:
		print why
		return

	print "Starting download of new version of "+showfile+"<br>"
	# fork and do the download in background
	if os.fork(): return
	#open('errors','a').write('starting '+net+'->'+tmpfile+'->'+local+'\n')
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

		os.rename(tmpfile, local)
		#open('errors','a').write(net+'->'+tmpfile+'->'+local+' complete\n')
	except Exception, why:
		import traceback
		f = open('errors','a')
		traceback.print_exc(f)
		f.write(str(why)+'\n')
		f.close()
		try: os.remove(tmpfile)
		except EnvironmentError: pass
	#finally:
	os._exit(0)

def print_copyright():
	print "<!--Last modified "+time.ctime(os.path.getmtime(sys.argv[0]))+"-->"
	print "<!--Copyright EISCAT Scientific Association "+time.strftime("%Y")+" -->"

# CFE 20200826: need logout link
def showLogout():
        print("<a href=\"/Shibboleth.sso/Logout\">Log out</a>")

from urllib import quote_plus as quote
from urllib import unquote_plus as unqoute
