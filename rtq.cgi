#!/usr/bin/env python
from common import *
import cgi,os
print "Content-type: text/html\n"
params=cgi.FieldStorage()
gfd='dirs ndumps maxfsize resultpath rtgdef selfig selsub'
gfl='selfun'
QUERY=''
special='\"\\\"!{&()\'; '
nl=chr(10)+chr(13)
htref=os.environ['HTTP_REFERER']
method=os.environ['REQUEST_METHOD']
if method=='POST' and htref.count('//www.eiscat.se/schedule/download.cgi'):
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
	print "Your request have been noted.<br>"
	print "The result will be sent to the mail address you provided."
else:
	print "Bad request."
