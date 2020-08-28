#!/usr/bin/env python
from common import *
import cgi,os
print "Content-type: text/html\n"
print "<!DOCTYPE html>"
print "<HTML lang=\"en\">"
print "<HEAD>"
print "<META charset=\"utf-8\">"
print "<TITLE>EISCAT rtg movie request</TITLE>"
print "</HEAD>"
print "<BODY>"

params=cgi.FieldStorage()
gfd='dirs ndumps maxfsize resultpath rtgdef selfig selsub'
gfl='selfun'
QUERY=''
special='\"\\\"!{&()\'; '
nl=chr(10)+chr(13)
htref=os.environ['HTTP_REFERER']
method=os.environ['REQUEST_METHOD']
if method=='POST' and htref.count('//data.eiscat.se/schedule/download.cgi'):
	for par in gfd.split():
		try:
			val=params.getvalue(par)
			for s in special:
				val=val.replace(s,'\\'+s)
			for s in nl:
				val=val.replace(s,'#')
			val=val.replace('##','#')
			QUERY=QUERY+par+'='+val+' '
		except:
			QUERY=QUERY+par+'= '
	for par in gfl.split():
		val=params.getvalue(par)
                if not val is None:
                        if len(val):
                                import base64	
			        valc=base64.b64encode(val)
			        valn=params[par].filename
			        QUERY=QUERY+par+'='+valc+' '+par+'n='+valn+' '
	QUERY=QUERY+'REMOTE_ADDR='+raddr()
	if su(raddr()):
		print QUERY+'<br>'
	req=open('rtgreg.txt','a')
	req.write('%s\n'%QUERY)
	req.close
        print "<h1>Request submitted</h1>"
	print "<p>Your request has been noted.<br>"
	print "The result will be sent to the email address you provided.</p>"
else:
	print "<p>Bad request.</p>"
print "</BODY>"
print "</HTML>"
