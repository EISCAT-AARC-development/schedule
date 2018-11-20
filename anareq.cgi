#!/usr/bin/env python
import cgi,os
from eiscat_auth import is_admin, current_user

print "Content-type: text/html\n"
params=cgi.FieldStorage()
gfd='datapath t resultpath maxfsize name_expr expver siteid intper extra'
QUERY=''
dup='\''
special='\"\\\"!{&()\'; '
nl="\n\r"
htref=os.environ['HTTP_REFERER']
method=os.environ['REQUEST_METHOD']

if method=='POST' and '://www.eiscat.' in htref and '/schedule/download.cgi' in htref:
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

	QUERY=QUERY+'REMOTE_USER='+current_user()

	if is_admin(current_user()):
		print QUERY+'<br>'
	#else:
	#	req=open('ananew.txt','a')
	req=open('anareg.txt','a')
	req.write('%s\n'%QUERY)
	req.close()
	print "Your request have been noted.<br>"
	print "The result will be sent to the mail address you provided, when the analysis is finished."
else:
	print "Bad request."
