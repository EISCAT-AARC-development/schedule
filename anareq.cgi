#!/usr/bin/env python
from common import *
import cgi,os
print "Content-type: text/html\n"
params=cgi.FieldStorage()
gfd='datapath t resultpath maxfsize name_expr expver siteid intper extra'
QUERY=''
dup='\''
special='\"\\\"!{&()\'; '
nl=chr(10)+chr(13)
htref=os.environ['HTTP_REFERER']
method=os.environ['REQUEST_METHOD']
if method=='POST' and htref.count('://www.eiscat.') and htref.count('/schedule/download.cgi'):
	for par in gfd.split():
		try:
			val=params.getvalue(par)
			for s in dup:
				val=val.replace(s,s+s)
			for s in special:
				val=val.replace(s,'\\'+s)
			for s in nl:
				val=val.replace(s,'#')
			val=val.replace('##','#')
			QUERY=QUERY+par+'='+val+' '
		except:
			QUERY=QUERY+par+'= '
	QUERY=QUERY+'REMOTE_ADDR='+raddr()
	if su(raddr()):
		print QUERY+'<br>'
	#else:
	#	req=open('ananew.txt','a')
	req=open('anareg.txt','a')
	req.write('%s\n'%QUERY)
	req.close
	print "Your request have been noted.<br>"
	print "The result will be sent to the mail address you provided, when the analysis is finished."
else:
	print "Bad request."
