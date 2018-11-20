#!/usr/bin/env python
import cgi
import os

from eiscat_auth import is_admin, current_user

print "Content-type: text/html\n"
params=cgi.FieldStorage()
gfd='dirs ndumps maxfsize resultpath rtgdef selfig selsub'
gfl='selfun'
QUERY=''
special='\"\\\"!{&()\'; '
nl="\n\r"
htref=os.environ['HTTP_REFERER']
method=os.environ['REQUEST_METHOD']

if method=='POST' and '//www.eiscat.se/schedule/download.cgi' in htref:
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
		if val:
			import base64	
			valc=base64.b64encode(val)
			valn=params[par].filename
			QUERY=QUERY+par+'='+valc+' '+par+'n='+valn+' '

	QUERY=QUERY+'REMOTE_USER='+current_user()

	if is_admin(current_user()):
		print QUERY+'<br>'

	req=open('rtgreg.txt','a')
	req.write('%s\n'%QUERY)
	req.close()
	print "Your request have been noted.<br>"
	print "The result will be sent to the mail address you provided."
else:
	print "Bad request."
