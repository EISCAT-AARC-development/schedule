#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Header: /home/chn/repos/eiscat-web/schedule/submit.cgi,v 1.14 2013/05/13 13:04:09 ingemar Exp $
#
# This script handles request submissions
#
#--------------------------------------------------------------------------
#     Copyright 2001 EISCAT Scientific Association. 
#     Permission to use, copy, and distribute, for non-commercial purposes, 
#     is hereby granted without fee, provided that this license information 
#     and copyright notice appear in all copies.
#--------------------------------------------------------------------------
#
# Written 27 September 1998
# converted to python 12 June 2002

from common import *

import subprocess, os, sys, re, cgi, time, calendar

versionNumber = "$Revision: 1.14 $".split()[1]

print "Content-type: text/HTML\n"
print "<!DOCTYPE html>"
print "<HTML lang=\"en\">"
print_copyright()
print "<HEAD>"
print "<META charset=\"utf-8\">"
print "<TITLE>Request submission form</TITLE>"
print "</HEAD>"
print "<BODY>"
print "<h3 align=center>EISCAT Schedule Request</h3>"

print "<i><center>"

params = cgi.FieldStorage()

keystuff=0
# check that string does not contain control characters
valid_name = lambda s: re.match('[^\000-\037\177]+$', s)

validations = {
	'year': lambda y: re.match('\d\d\d\d$', y),
	'month': lambda y: 1 <= int(y) <= 12,
	'day': lambda y: 1 <= int(y) <= 31,
	'endyear': lambda y: re.match('\d\d\d\d$', y),
	'endmonth': lambda y: 1 <= int(y) <= 12,
	'endday': lambda y: 1 <= int(y) <= 31,
	'experiment': lambda s: re.match('\w[ \w]{0,9}$', s),
	'description': lambda s: re.match('[^\000-\037]{0,255}$', s),
	'resources': lambda s: re.match(r'maintenance|IPY|TNA|\w\w\([0-9.]+\)(,\w\w\([0-9.]+\))*$', s),
	'contact': valid_name,
	'phone': lambda s: re.match(r'[\d+ /-]*$', s),
	'email': lambda s: re.match(r'[\w.-]+@[\w.-]+$', s),
	'fax': lambda s: re.match(r'[\d+ /-]*$', s),
	'starttime': lambda s: 0 <= int(s[:2]) <= 24 and 0 <= int(s[2:]) <= 59,
	'endtime': lambda s: 0 <= int(s[:2]) <= 24 and 0 <= int(s[2:]) <= 59,
	'choice': lambda s, v=[x for x,y in sites]: s in v,
	'responsible': valid_name,
	'notes': lambda s: re.match('[^\000-\011\013-\037\177]*$', s),
	'submitter': valid_name,
	#'keywords': lambda s: re.match('[^\000-\011\013-\037\177]*$', s),
	#'url': lambda s: re.match('[^\000-\011\013-\037\177]*$', s),
	#'region': lambda s: re.match('[^\000-\011\013-\037\177]*$', s),
	#'public': lambda s: re.match('[^\000-\011\013-\037\177]*$', s),
}

# make a 'struct' of the passed arguments

class foo: pass
k = foo()
got_input = 0

for key, valid in validations.items():
	value = params.getvalue(key,'')
	if value: got_input = 1
	setattr(k, key, value)

# Some persons have default values
if k.contact == 'Ingemar Haggstrom':
	k.phone = '+46 980 79155'
	k.fax = "+47 980 79159"
	k.email = "ingemar@eiscat.se"

# All operating systems have different line-ends
k.notes = re.sub('\r\n?|\n\r','\n',k.notes)

# default values for some fields
if not k.endyear: k.endyear = k.year
if not k.endmonth: k.endmonth = k.month

# validate all fields
errfields = []

for key, valid in validations.items():
	value = getattr(k, key)
	try:
		assert valid(value)
	except (AssertionError, ValueError):
		errfields.append(key)

if got_input:
	# check with number of days this month
	if 'month' not in errfields and 'year' not in errfields and 'day' not in errfields:
		if int(k.day) > calendar.monthrange(int(k.year), int(k.month))[1]:
			errfields.append('day')
	if 'endmonth' not in errfields and 'endyear' not in errfields and 'endday' not in errfields:
		if int(k.endday) > calendar.monthrange(int(k.endyear), int(k.endmonth))[1]:
			errfields.append('endday')
else:
	# auto fillin todays date
	year,month,day, hour,minute,_, _,_,_ = time.gmtime()
	k.year = str(year)
	k.month = k.endmonth = str(month)
	k.day = k.endday = str(day)
	k.starttime = k.endtime = "%02d%02d"%(hour, minute)
		
def update_database(k):
	k.month = "%02d"%int(k.month)
	k.day = "%02d"%int(k.day)
	k.endmonth = "%02d"%int(k.endmonth)
	k.endday = "%02d"%int(k.endday)
	status = "R"
	if k.resources == 'maintenance':
		status = 'M'
	elif k.resources.startswith('CP') and k.submitter == 'I Häggström':
		status = 'C'
	infofilename = k.year+k.month+k.day+str(os.getpid())
	#os.popen4('cvs up '+ScheduleDB)[1].read()
	# The following line needs to be checked maybe it does not do
	# the correct thing as the line above AW 2009-10-30
	#subprocess.Popen(['cvs', 'up '+ScheduleDB]).wait()
	subprocess.Popen(['cvs', 'up', ScheduleDB], stdout=subprocess.PIPE).communicate()[0]
	try:
		f = open(ScheduleDB,'a')
	except EnvironmentError, why:
		print "Database unreachable (",why,")"
		sys.exit()
	if k.year == k.endyear and k.month == k.endmonth and k.day == k.endday:
		f.write('%s %s %s %s %s %s %c %s\t%s @%s\n'%(k.year, k.month, k.day, k.starttime,
					k.endtime, k.choice, status, k.experiment, k.resources, infofilename))
	else:
		# spans several days, make multiple entries in database
		f.write('%s %s %s %s 2400 %s %c %s\t%s @%s\n'%(k.year, k.month, k.day, k.starttime,
					k.choice, status, k.experiment, k.resources, infofilename))
		for day in range(int(k.day)+1, int(k.endday)):
			f.write('%s %s %02d 0000 2400 %s %c %s\t%s @%s\n'%(k.year, k.month, day,
						k.choice, status, k.experiment, k.resources, infofilename))
		f.write('%s %s %s 0000 %s %s %c %s\t%s @%s\n'%(k.year, k.month, k.endday, k.endtime,
					k.choice, status, k.experiment, k.resources, infofilename))
	f.close()

	# make information file
	try:
		f = open(NotesDir+infofilename, 'w')
	except EnvironmentError, why:
		print "Cannot write notes file:", why
		sys.exit()
	f.write('experiment '+k.experiment+'\n')
	f.write('instrument '+k.choice+'\n')
	f.write('start %s %s %s %s\n'%(k.year, k.month, k.day, k.starttime))
	f.write('end %s %s %s %s\n'%(k.endyear, k.endmonth, k.endday, k.endtime))
	f.write('status '+status+'\n')
	if k.description: f.write('description '+k.description+'\n')
	f.write('contact '+k.contact+'\n')
	if k.phone: f.write('phone '+k.phone+'\n')
	f.write('email '+k.email+'\n')
	if k.fax: f.write('fax '+k.fax+'\n')
	f.write('operator '+k.responsible+'\n')
	f.write('submitter '+k.submitter+'\n')
	f.write('resources '+k.resources+'\n')
	if k.notes: f.write('notes\n'+k.notes+'\n')
	f.close()
	
	print "<pre>"
	#print os.popen4('cvs add '+NotesDir+infofilename)[1].read()
	# The following line needs to be checked maybe it does not do
	# the correct thing as the line above AW 2009-10-30
	print subprocess.Popen(['cvs', 'add ', NotesDir+infofilename], stdout=subprocess.PIPE).communicate()[0]

	#print os.popen4('cvs ci -m "" '+NotesDir+infofilename+' '+ScheduleDB)[1].read()
	# The following line needs to be checked maybe it does not do
	# the correct thing as the line above AW 2009-10-30
	print subprocess.Popen(['cvs', 'ci', '-m', '""', NotesDir+infofilename, ScheduleDB], stdout=subprocess.PIPE).communicate()[0]
	print "</pre>"

	# mail infofile to some people
	def mailit_to(addr, file=NotesDir+infofilename):
		#os.popen('mail '+addr+' < '+file).read()
		subprocess.Popen(['/bin/sh', '-c', 'mail '+ addr+ ' < '+ file], stdout=subprocess.PIPE).communicate()[0]

	year,month,day, _,_,_, _,_,_ = time.gmtime()
	mdiff = (int(k.year) - year)*12 + (int(k.month)-month)

	late = mdiff < 1 or (mdiff == 1 and day > 10)
	advert_new_submits(mailit_to, late, k.choice)

if got_input:
	if not errfields:
		# check all times.
		start = time.mktime((int(k.year), int(k.month), int(k.day), int(k.starttime[:2]), int(k.starttime[2:]), 0, -1, -1, 0))
		stop = time.mktime((int(k.endyear), int(k.endmonth), int(k.endday), int(k.endtime[:2]), int(k.endtime[2:]), 0, -1, -1, 0))
		now = time.time()
		if start <= now:
			print "<font color=red>Start time has already passed</font><br>"
			errfields.append('starttime')
		elif stop <= start:
			print "<font color=red>Start time is set after end time</font><br>"
			errfields.append('endtime')
		#elif stop > start+3600*60*30:
		#	print "<font color=red>Experiment lasts more than a month</font><br>"
		#	errfields.append('endtime')
		elif k.month <> k.endmonth or k.year <> k.endyear:
			print "<font color=red>Experiment must not cross a month boundary, split into two requests</font><br>"
			errfields.append('endtime')
		elif int(k.endtime) == 0:
			print "<font color=red>Use 24:00 previous day instead of 00:00 in end time</font><br>"
			errfields.append('endtime')
	if errfields:
		print "<font color=red>Some fields have the wrong format. Please correct all fields marked ERROR</font>"
	else:
		print "All fields correct, updating database...<br>"
		update_database(k)
		print "<font color=green>Database successfully updated</font>"

def out_flags(key):
	if key in errfields:
		if got_input: print "<font color=red>ERROR</font>"
		if not getattr(k, key): print "(required)"

def input_field(key, extra):
	print "<INPUT NAME="+key+" "+extra+' value="'+getattr(k,key)+'">'
	out_flags(key)

print "</center><hr><form method=POST><center>"
print 'Experiment name (max 10 characters):'
input_field('experiment', 'size=10 maxlen=10')

print '<br>Description (short text or url)<br>'
input_field('description', 'size=80')

print '<br>Contact:'
input_field('contact', 'size=30')
print 'Phone:'
input_field('phone', 'size=15')
print '<br>Email:'
input_field('email', 'size=30')
print 'Fax:'
input_field('fax', 'size=15')
print '<hr><table border cellpadding=3><tr>'
for value, desc in sites:
	print '<td><input type=radio name=choice'
	if k.choice == value: print 'checked'
	print 'value='+value+'>',desc,'('+value+')</td>'
print '</table>'
out_flags('choice')

print 'Start year:'
input_field('year','size=4 maxlen=4')
print 'month:'
input_field('month','size=2 maxlen=2')
print 'day:'
input_field('day','size=2 maxlen=2')
print 'time:'
input_field('starttime','size=4 maxlen=4')
print 'End day:'
input_field('endday','size=2 maxlen=2')
print 'time:'
input_field('endtime','size=4 maxlen=4')

print 'year: %s month: %s'%(k.endyear, k.endmonth)
print '<br>Responsible experimenter at EISCAT:'
input_field('responsible','size=30')

print '<hr>Notes:<br>'
print '<textarea name=notes rows=6 cols=80 wrap=hard>'+k.notes+'</textarea>'
out_flags('notes')

if keystuff:
	print '<br>Region of measurement:'
	print '<input type=radio name=k.region value=d>D'
	print '<input type=radio name=k.region value=e>E'
	print '<input type=radio name=k.region value=f>F'
	print '<input type=radio name=k.region value=t>topside'
	print '<input type=radio name=k.region value=o>other'
	out_flags('region')
	print '<br>Keywords:'
	print '<textarea name=keywords rows=1 cols=80>'+k.keywords+'</textarea>'
	out_flags('keywords')
	print '<br>Public motivation:'
	print '<textarea name=keywords rows=2 cols=80>'+k.public+'</textarea>'
	out_flags('public')

print '<br>Resources:'
input_field('resources','size=24')
print 'Format: &lt;Associate code&gt;(&lt;hours&gt;), eg EI(50)<br>'
print 'Submitted by:'
input_field('submitter', 'size=30')

print '</i><input type=submit value="Submit request"></center>'
print '</form>'
print '<p align=center><i>Check confirmation line at the top of this form to be sure your entry was accepted!</i></p>'

print '<hr><center>Autosheduler Vn',versionNumber+'</center>'

print "</BODY>"
print "</HTML>" 
