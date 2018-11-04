#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     Direct a download request to the RAID servers
#
#--------------------------------------------------------------------------
#     Copyright 1998 EISCAT Scientific Association. 
#     Permission to use, copy, and distribute, for non-commercial purposes, 
#     is hereby granted without fee, provided that this license information 
#     and copyright notice appear in all copies.
#--------------------------------------------------------------------------

from common import *

import os, sys, cgi

sys.path.append(tape_db_dir)
import tapelib
from serve_files import permitted, portno

if portno==37009:
    import ssl


print "Content-type: text/html\n"
print "<HTML>"
print_copyright()

params = cgi.FieldStorage()

submit = params.getvalue('submit')
format = params.getvalue('format')
assert format in ('tar', 'tgz', 'zip')
maxtar = int(params.getvalue('maxtar'))
if submit=='Analyse' or submit=='Plot': maxtar=63
if maxtar==2: maxtar=31
elif maxtar==4: maxtar=32
else: maxtar=63
value = params.getvalue("r")
if not value:
	print "No data sets were chosen."
	sys.exit()
if not isinstance(value, list): value = [value]
ids = map(int, value)
filename = params.getvalue('filename', 'data')

sql = tapelib.opendefault()
#sql = tapelib.openzfs()

def not_permitted():
	print """According to our <a href="../disclaimer.html#rules">rules</a> you are not permitted to download some of the marked sets.<br>"""
	print '(the decision is based on your ip number, '+raddr()+' and your hostname)'
	sys.exit()

if submit=='Quota' and not su(raddr()): not_permitted()
locs = {}
for id in ids:
	url = tapelib.create_raidurl('%', '%')
	ls = sql.select_experiment_storage("resource.resource_id = %s AND location LIKE %s", (id, url), what="account, country, location, UNIX_TIMESTAMP(start) AS date, bytes, type")
	if len(ls):
		l = ls[0]
		if (submit!='Analyse' or submit!='Plot') and not su(raddr()) and not permitted(raddr(), (l.account or l.country), l.date, l.type):
			not_permitted()
		for l in ls:
			machine, path = tapelib.parse_raidurl(l.location)[:2]
			locs.setdefault(machine,[]).append((id, path, l.bytes))

if len(locs)==0:
	print "Could not find the data in the data base"
	sys.exit()

def clever_split(locs, ids, maxtar):
	# determine which ids should be downloaded from which host.
	# if possible, download everything from one host.
	# otherwise, split as even as possible
#	import sets
#	ids = sets.Set(ids)
	ids = set(ids)
	locs = locs.items()
	locs.sort(lambda y, x: cmp(len(x[1]), len(y[1])))
	res = {}
	max_size=(1L<<maxtar) #2Gig
	for machine, provides in locs:
		for id, path, bytes in provides:
			if id in ids:
				ids.remove(id)
				if machine in res and res[machine][1] + bytes > max_size:
					machine += " "
				#res.setdefault(machine, [[], 0])[0].append(id)
				res.setdefault(machine, [[], 0, []])[0].append(id)
				res[machine][1] += bytes
				res[machine][2].append(path)
	if len(res)==0:
		print "No data sets can be reached.<br>"
	elif ids:
		print "Warning: some data sets was dropped.<br>"
	return res

if submit!='Quota':
#	ping machines
	for machine in locs.keys():
		print "Checking "+machine+" availability..."
		sys.stdout.flush()
		import socket
                if (portno==37009):
                    rawsocket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    rawsocket.settimeout(5)
                    s=ssl.wrap_socket(rawsocket)
                else:   
        	    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	    	    s.settimeout(5)
		try:
		    if machine=='data1':
                        s.connect(('localhost',portno))
                    else: 
                        s.connect((machine,portno))
		    s.send("PING / HTTP/1.0\n\n")
		    if s.recv(4) != "PONG": raise IOError
		except (socket.error, IOError):
		    print "down<br>"
		    del locs[machine]
		else:
		    print "up<br>"
		try:
		    s.close()
		except:
		    pass
                try:
                    rawsocket.close()
                except:
                    pass
	        big_tars=0

if 0:
	print 'Archive down for maintanance.'
	locs={}
locs = clever_split(locs, ids, maxtar)
if submit=='Download':
	if len(locs) > 9:
		print 'Note: Max 9 parallel downloads.'
	print "<ul>"
elif submit=='Analyse' or submit=='Plot':
	allurls=''
	date=filename[-8:]

#for i, (machine, (resids, total_bytes)) in enumerate(locs.items()):
for i, (machine, (resids, total_bytes, paths)) in enumerate(locs.items()):
	machine = machine.rstrip()
	machine = socket.getfqdn(machine)
	if machine == 'deposit.eiscat.se': machine = 'dd1.eiscat.se'
	if machine == 'data1.eiscat.se': machine = 'dd1.eiscat.se'
	if machine == 'data1': machine = 'dd1.eiscat.se'
	if machine == 'dd1.eiscat.se': machine = 'portal'
	#machine = socket.gethostbyname(machine)
	fname = filename
	if len(locs) > 1: fname += ".part%d"%(i+1)
	fname += '.'+format
        if portno==37009:
	    url = "https://"+machine+':%d/'%portno+';'.join([ str(x) for x in resids ])+'/'+fname
        else:
            url = "http://"+machine+':%d/'%portno+';'.join([ str(x) for x in resids ])+'/'+fname
        if submit=='Download':
		if total_bytes >= (1L<<maxtar):
			big_tars=1
		if total_bytes+1 == (1L<<32):
			sizrel='over'
			unit='GiB'
			total_bytes='4'
		else:
			sizrel='approx'
			unit='bytes'
			prefix='kMGT'
			while total_bytes>1024:
				total_bytes=float(total_bytes)/1024.
				unit=prefix[0]+'iB'
				prefix=prefix[1:]
			if total_bytes>9.9:	total_bytes='%.0f'%total_bytes
			else:			total_bytes='%.1f'%(total_bytes+.05)
		print '<li><a href="'+url+'">'+fname+'</a> (%s %s %s)'%(sizrel,total_bytes,unit)
	elif submit=='Analyse' or submit=='Plot':
		if len(allurls)==0:	allurls=url
		else:	allurls=allurls+' '+url
		allpaths = ';'.join([ x[1:] for x in paths ])
if submit!='Download':
	print '<SCRIPT LANGUAGE="JavaScript">'
	print '<!--'
if submit=='Analyse' or submit=='Plot':
	print 'function createCookie(name,value,days) {'
	print '  if (days) {'
	print '	   var date=new Date();'
	print '    date.setTime(date.getTime()+(days*24*60*60*1000));'
	print '	   var expires="; expires="+date.toGMTString();'
	print '  }'
	print '  else var expires="";'
	print '  document.cookie=name+"="+value+expires+"; path=/";'
	print '}'
	print 'function readCookie(name) {'
	print '  var nameEQ=name + "=";'
	print '  var ca=document.cookie.split(\';\');'
	print '  for(var i=0;i<ca.length;i++) {'
	print '	   var c=ca[i];'
	print '	   while (c.charAt(0)==\' \') c=c.substring(1,c.length);'
	print '	   if (c.indexOf(nameEQ)==0) return c.substring(nameEQ.length,c.length);'
	print '  }'
	print '  return null;'
	print '}'
	print 'function valid(form) {'
	#From 'http://www.webreference.com/js/column5/workaround.html'
	print '  var field=form.resultpath;'
	print '  var str=field.value;'
	print '  if (window.RegExp) {'
	print '    var reg1str="(@.*@)|(\\\\.\\\\.)|(@\\\\.)|(\\\\.@)|(^\\\\.)";'
	print '    var reg2str="^.+\\\\@(\\\\[?)[a-zA-Z0-9\\\\-\\\\.]+\\\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$";'
	print '    var reg1=new RegExp(reg1str);'
	print '    var reg2=new RegExp(reg2str);'
	print '    if (!reg1.test(str) && reg2.test(str)) {'
	print '      createCookie(\'emall\',str,360)'
	print '      return true;'
	print '      }'
	print '  } else if(str.indexOf("@") >= 0) {'
	print '    createCookie(\'emall\',str,360)'
	print '    return true;'
	print '  }'
	print '  field.focus();'
	print '  field.select();'
	print '  return false;'
	print '}'
if submit=='Quota':
	print 'function def_quota(form) {'
	print '  var sum=0;'
	print '  var val;'
	print '  for (var i=0; i<form.elements.length; i++)'
	print '    if (form.elements[i].type == "text") {'
	print '      val=eval(form.elements[i].value);'
	print '      if (val<0 || val > 100) {'
	print '        form.elements[i].focus();'
	print '        form.elements[i].select();'
	print '        return false;'
	print '      }'
	print '      sum=sum+eval(form.elements[i].value);'
	print '    }'
	print '  if (sum==100) return true;'
	print '  form.CP1.focus();'
	print '  form.CP1.select();'
	print '  return false;'
	print '}'
	print 'function checkquota(country) {'
	print '  var val=parseInt(country.value);'
	print '  var form=document.quota;'
	print '  if (val==100)'
	print '    for (var i=0; i<form.elements.length; i++)'
	print '      if (form.elements[i].type == "text")'
	print '        form.elements[i].value="0";'
	print '  country.value=val.toString(10);'
	print '  return true;'
	print '}'
if submit!='Download':
	print '// -->'
	print '</SCRIPT>'
if len(locs)==0:
	print 'Please check again tomorrow'
elif submit=='Download':
	print '</ul>'
	if len(locs)>1 or maxtar>31:
		print "<FORM METHOD=POST ACTION='download.cgi'>"
		print "Maximum file size:"
		if maxtar!=31: print "<input type=submit name=maxtar value=2>",
		if maxtar!=32: print "<input type=submit name=maxtar value=4>",
		if maxtar!=63: print "<input type=submit name=maxtar value=99>",
		print "Gigabyte",
		print "<input type=hidden name=format value=%s>"%format
		for id in ids: print "<input type=hidden name=r value=%d>"%id
		print "<input type=hidden name=filename value=%s>"%filename
		print "<input type=hidden name=submit value='Download'>"
		print '</FORM>'
	if big_tars:
		print "WARNING: Some browsers cannot receive files over 2 or 4 GiB.<br>"
		print "Solution1: Recompile using -D_ENABLE_64_BIT_OFFSET, -D_LARGE_FILES or similar<br>"
		print "Solution2: Use a command line tool and redirect the output, for example <code>wget -O - <i>url</i> | tar xf -</code><br>"
		print "<br>"
	if format in ("tar", "tgz"):
		if len(locs) == 1:
			print "The file is GNU tar compatible."
		else:
			print "The files are GNU tar compatible."
	print "This service might need that your firewall needs to be set up to accept connections directly to the RAID systems.<br>"
elif submit=='Analyse':
	sites='KSTVLLL'
	ants='kir sod uhf vhf 32m 42m 32p'
	site=''
	i=0
	for ant in ants.split():
		#if allurls.count('@'+ant)>0:
		if allpaths.count('@'+ant)>0:
			if len(site)==0:	site=sites[i]
			else:
				print 'Sorry, but you can only specify data from one site or data stream.'
				print "</BODY></HTML>" 
				sys.exit()
		i=i+1
	if ant != '32p' and not date.isdigit():
		print 'Sorry, but you can only specify data from one day.'
		print "</BODY></HTML>" 
		sys.exit()
	print '<hr><h3><img src="guisdaplogo.png" onLoad="ana.resultpath.value=readCookie(\'emall\');">'
	print 'GUISDAP for dummies'
	print '<img src="guisdaplogo.png"></h3>'
	print 'This is a page for direct analysis from our data bases.'
	print 'If you are familiar with guisdap analysis, feel free to use it.'
	print 'Othervise some help is <a href="../GUISDAP/doc/howto.html">here</a>.<br>'
	#print 'Note that the service is in testing phase so the result might'
	#print 'not be what you expect.'
	print 'Normally it should be just to press "GO", but you should check the preselected parameters<br>'
	print '<FORM METHOD=POST ACTION="anareq.cgi" name=ana onSubmit="return valid(this);" >'
	#print '<FORM METHOD=GET ACTION="anareq.cgi">'
	print '<INPUT type=hidden name=datapath value="'+allurls+'">'
	print '<INPUT type=hidden name=t value="%s %s %s">'%(date[:4],date[4:6],date[6:8])
	print '<table bgcolor="lightGray"><tbody>'
	print '<tr><td>Your Email</td>'
	#print '<td colspan=3><INPUT type=text name=resultpath onChange="javascript:this.value=this.value.toLowerCase();" onFocus="javascript:this.value=readCookie(\'emall\');"></td>'
	print '<td colspan=3><INPUT type=text name=resultpath onChange="javascript:this.value=this.value.toLowerCase();"></td>'
	print '<td>Max mail size (Mb)</td>'
	print '<td><select name=maxfsize>'
	for i in [1,3,10,20,100]:
		if i==10:	print '<OPTION SELECTED>%d'%i
		else:	print '<OPTION>%d'%i
	print '</td></tr>'
	print '<tr><td>Dsp expr</td>'
	print '<td><SELECT NAME=name_expr>'
	exps='arc arc1 dlayer arcd beata bella cp0e cp0g cp0h cp1c cp1f CP1H cp1j cp1k cp1l cp1m cp2c cp3c cp4b cp7h folke hilde gup0 gup1 gup3c ipy lace manda mete pia steffe tau0 tau1 tau1a tau2 tau2pl tau3 tau7 tau8 taro uhf1g2'
	expsalt='arc arc_slice dlayer arc_dlayer beata bella cp-0-e cp-0-g cp-0-h cp-1-c cp-1-f cp-1-h cp-1-j cp-1-k cp1l cp1m cp-2-c cp-3-c cp4b cp7h folke hilde gup0 gup1 gup3c ipy lace manda mete pia steffel tau0 tau1 tau1a tau2 tau2_pl tau3 tau7 tau8 taro sp-vi-uhf1-g2'
	sel=''
	if len(exps.split()) == len(expsalt.split()):
		i=0
		for exp in exps.split():
			if filename.count(exp)>0:	sel=exp
			j=0
			for altexp in expsalt.split():
				if i==j and filename.count(altexp)>0:	sel=exp
				j=j+1
			i=i+1
	for exp in exps.split():
		if sel==exp:
			print '<OPTION SELECTED>'+exp
		else:
			print '<OPTION>'+exp
	print '</SELECT></td>'
	print '<td>Version</td><td><SELECT NAME=expver>'
	for i in range(1,10):
		if filename.count(r'%d.'%i)>0:
			print '<OPTION SELECTED>'+'%d'%i
		else:
			print '<OPTION>'+'%d'%i
	print '</SELECT></td></tr>'
	print '<tr><td>Site</td><td><SELECT NAME=siteid>'
	sites='KSTVLX'
	for i in range(len(sites)):
		if site==sites[i]:
			print '<OPTION SELECTED VALUE=%d>%s'%(i+1,sites[i])
		else:
			print '<OPTION VALUE=%d>%s'%(i+1,sites[i])
	print '</SELECT></td></tr>'
	scan='cp2 cp3 cp4 lowelnorth2 fix2 ip2 ip3'
	min1='fixed bore lowel zenith'
	min2='lowelnorth1 lowelsouth1 lowelsouth2 lowelsouth3 lowelnorth vhfcross'
	iper=[0,60,120,300]
	ipert='AntennaMovement 1minute 2minutes 5minutes'
	print '<tr><td>Integration time</td>'
	print '<td colspan=2><SELECT NAME=intper>'
	i=2
	for exp in scan.split():
		if filename.count(exp)>0: i=0
	for exp in min1.split():
		if filename.count(exp)>0: i=1
	for exp in min2.split():
		if filename.count(exp)>0: i=2
	j=0
	for exp in ipert.split():
		if i==j:
			print '<OPTION VALUE=%d SELECTED>%s'%(iper[j],exp)
		else:
			print '<OPTION VALUE=%d>%s'%(iper[j],exp)
		j=j+1
	print '</SELECT></td></tr>'
	print '<tr><td rowspan=5>Special</td>'
	print '<td colspan=3 rowspan=5><textarea name=extra rows=4"></textarea></td></tr>'
	print '<tr><TD></TD></tr></tbody>'
	print '<tr><td><INPUT TYPE=submit VALUE="GO"></td></tr></table></FORM>'
	print 'The output of the analysis will be sent to your mail account'
elif submit=='Plot':
	print '<hr><h3><onLoad="ana.resultpath.value=readCookie(\'emall\');">'
	print 'Real Time Graph</h3>'
	print 'This is a page to plot the raw data for an overview of the experiment'
	print '<FORM METHOD=POST ACTION="rtq.cgi" name=ana onSubmit="return valid(this);" enctype="multipart/form-data" >'
	print '<INPUT type=hidden name=dirs value="'+allurls+'">'
	print '<table bgcolor="lightGray"><tbody>'
	print '<tr><td>Your Email:'
	print '<INPUT type=text name=resultpath onChange="javascript:this.value=this.value.toLowerCase();">'
	print 'Max mail size (Mb):<select name=maxfsize>'
	for i in [1,3,10,20,100]:
		if i==20:	print '<OPTION SELECTED>%d'%i
		else:	print '<OPTION>%d'%i
	print '</td></tr>'
	print '<tr><td>Number dumps/secs to integrate'
	print '<INPUT type=text name=ndumps VALUE="60" pattern="[0-9]{1,3}" size=3></td>'
	#if allurls.count('information')<1:
	if allpaths.count('information')<1:
		print '</tr><tr><td>No information directory, please provide definition script:</td>'
	else:
		print '</tr><tr><td>Optional:</td>'
	print '</tr><td>Definition file <input type="file" name="rtgdef" accept=".m"></td>'
	if su(raddr()):
		print '</tr><tr><td>Special analysis:'
		print 'Plot window:<input type=text name=selfig pattern="[0-9]{1,2}" size=2>'
		print 'Subplot number <input type=text name=selsub pattern="[0-9]" size=1>'
		print 'Function/Package <input type=file name=selfun></td>'
	print '</tr><tr><td><INPUT TYPE=submit VALUE="GO"></td></tr></table></FORM>'
	print 'The output, a set of movie files, will be sent to your mail account'
elif submit=='Quota':
	owners=['CP1 CP2 CP3 CP4 CP6 CP7','UP1 UP2 UP3','IPY AA','UK NI NO SW FI CN','GE FR RU KR US','PP 3P EI CP']
	print filename+' belongs to:'
	print '<FORM METHOD=POST ACTION="quota.cgi" name=quota onSubmit="return def_quota(this);" >'
	strid=''
	for id in ids:
		strid=strid+str(id)+' '
	print '<INPUT type=hidden name=r value="'+strid[:-1]+'">'
	print '<table bgcolor="lightGray"><tbody>'
	for own in owners:
		print '<tr>'
		for owner in own.split():
			q='0'
			if ls[0].country==owner: q='100'
			print '<td>'+owner+'</td>'
			print '<td><input type=text size=3 name='+owner+' value='+q+' onChange="return checkquota(this);"></td>'
		print '</tr>'
	print '<tr><td><INPUT TYPE=submit VALUE="OK"></td></tr></FORM>'
	print '</tbody></table>'
print '<hr>'
disconnect_db(sql.cur)

print "</BODY>"
print "</HTML>" 
