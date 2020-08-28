#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This script displays and edits notes files for the schedule system
#
#--------------------------------------------------------------------------
#     Copyright 2001 EISCAT Scientific Association. 
#     Permission to use, copy, and distribute, for non-commercial purposes, 
#     is hereby granted without fee, provided that this license information 
#     and copyright notice appear in all copies.
#--------------------------------------------------------------------------
#
# Written 27 June 2001
# converted to python 12 June 2002

from common import *

import os, sys, re, cgi, time, subprocess

versionNumber = "$Revision: 1.9 $".split()[1]

def cleanify(str, multiline=0):
	if not str:
		return ''
	if multiline:
		return re.sub('[\000-\011\013-\037\177]','',str)
	return re.sub('[\000-\037\177]','',str).strip()

# Main program starts here

print "Content-type: text/HTML\n"
print "<!DOCTYPE html>"
print "<HTML lang=\"en\">"
print_copyright()
print "<HEAD>"
print "<META charset=\"utf-8\">"
print "<TITLE>Schedule Notes Viewer</TITLE>"
print "</HEAD>"

print "<BODY>"
print "<h3 align=center>Schedule Notes Viewer Vn "+versionNumber+"</h3>"

params = cgi.FieldStorage()

fileName = params.getfirst('fileName','')
Start = params.getfirst('Start','')
End = params.getfirst('End','')
Mday = params.getfirst('Mday','')

diagnostics = ''
if not re.match('\d+$', fileName):
	print 'Illegal fileName parameter'
	sys.exit()


if params.getvalue('sure') == "y":
	diagnostics += "Writing new file<br>"
	try:
		f = open(NotesDir+fileName, 'w')
	except EnvironmentError, why:
		print "Cannot write file:", why
		sys.exit()
	experiment = cleanify(params.getvalue('experiment'))
	if experiment: f.write('experiment '+experiment+'\n')
	instrument = cleanify(params.getvalue('instrument'))
	if instrument: f.write('instrument '+instrument+'\n')
	start = cleanify(params.getvalue('start'))
	if start: f.write('start '+start+'\n')
	end = cleanify(params.getvalue('end'))
	if end: f.write('end '+end+'\n')
	status = cleanify(params.getvalue('status'))
	if status: f.write('status '+status+'\n')
	description = cleanify(params.getvalue('description'))
	if description: f.write('description '+description+'\n')
	contact = cleanify(params.getvalue('contact'))
	if contact: f.write('contact '+contact+'\n')
	phone = cleanify(params.getvalue('phone'))
	if phone: f.write('phone '+phone+'\n')
	email = cleanify(params.getvalue('email'))
	if email: f.write('email '+email+'\n')
	fax = cleanify(params.getvalue('fax'))
	if fax: f.write('fax '+fax+'\n')
	operator = cleanify(params.getvalue('operator'))
	if operator: f.write('operator '+operator+'\n')
	submitter = cleanify(params.getvalue('submitter'))
	if submitter: f.write('submitter '+submitter+'\n')
	resources = cleanify(params.getvalue('resources'))
	if resources: f.write('resources '+resources+'\n')
	notes = cleanify(params.getvalue('notes'), multiline=1)
	if notes: f.write('notes\n'+notes+'\n')
	f.close()
	#cvs_output = os.popen4('cvs ci -m "" '+NotesDir+fileName)[1].read()
	# The following line needs to be checked maybe it does not do
	# the correct thing as the line above AW 2009-10-30
	#cvs_ouput = subprocess.Popen(['cvs', 'ci -m '+NotesDir+fileName]).wait()
	cvs_output = subprocess.Popen(['cvs', 'ci', '-m', '""', NotesDir+fileName], stdout=subprocess.PIPE).communicate()[0]
	#diagnostics += cvs_output.replace('\n','<br>')
	diagnostics += "Done."
else:
	experiment = instrument = start = end = status = description = contact = ''
	phone = email = fax = operator = submitter = resources = notes = ''
	#os.popen4('cvs up '+NotesDir+fileName)[1].read()
	# The following line needs to be checked maybe it does not do
	# the correct thing as the line above AW 2009-10-30
	#subprocess.Popen(['cvs', 'up '+NotesDir+fileName]).wait()
	subprocess.Popen(['cvs', 'up', NotesDir+fileName], stdout=subprocess.PIPE).communicate()[0]
	try:
		f = open(NotesDir+fileName)
	except EnvironmentError:
		print "File",fileName,"does not exist."
		sys.exit()
	while 1:
		line = f.readline()
		if not line: break
		if ' ' in line:
			hdr, val = line.split(' ', 1)
			val = cleanify(val)
			if hdr == 'experiment': experiment = val
			elif hdr == 'instrument': instrument = val
			elif hdr == 'start': start = val
			elif hdr == 'end': end = val
			elif hdr == 'status': status = val
			elif hdr == 'description': description = val
			elif hdr == 'contact': contact = val
			elif hdr == 'phone': phone = val
			elif hdr == 'email': email = val
			elif hdr == 'fax': fax = val
			elif hdr == 'operator': operator = val
			elif hdr == 'submitter': submitter = val
			elif hdr == 'resources': resources = val
			elif hdr == 'notes':
				notes = val+'\n'+f.read()
				break
		elif line.strip() == 'notes':
			notes = f.read()
			break
	f.close()

print "<h3 align=center>"+instrument+":",experiment,start,"-",end+"</h3>"
if Start:
	print "<h3 align=center>Scheduled for",Start+"-"+End+"</h3>"

print "<form method=POST>"

print "<center>"
if description.startswith("http"):
    print '<a href="'+description+'">Description</a>'
else:
    print 'Description'
print '<INPUT NAME=description size=80 value="'+cgi.escape(description, 1)+'">'
print "<br>"
print 'Contact: <input name=contact size=30 value="'+cgi.escape(contact, 1)+'">'
print 'Phone: <input name=phone size=15 value="'+cgi.escape(phone, 1)+'">'
print 'Fax: <input name=fax size=15 value="'+cgi.escape(fax, 1)+'"><br>'
print '<a href="mailto:'+email+'.REMOVE">Email</a>: <input name=email size=30 value="'+email+'"><br>'
print "Responsible experimenter for"
for code, desc in sites:
	if code == instrument:
		print desc+":"
		break
else:
	print instrument+":"

print '<input name=operator size=30 value="'+cgi.escape(operator, 1)+'"><br>'
print 'Resources: '+resources+' [format: &lt;Associate code&gt;(&lt;hours&gt;), eg EI(50)]<hr>'

print "Notes<br>"
print "<center><TEXTAREA NAME=notes ROWS=12 COLS=80 WRAP=VIRTUAL>"+cgi.escape(notes)+"</TEXTAREA></center><br>"

# TODO: Print links in notes

print 'Submitted by: <input name=submitter size=30 value="'+cgi.escape(submitter, 1)+'">'
if su(raddr()):
	print "<input type=checkbox name=sure value=y>Change"
print "<input type=submit value=Refresh><br>"

print "</center>"

print '<INPUT NAME=instrument value="'+instrument+'" type=hidden>'
print '<INPUT NAME=experiment value="'+experiment+'" type=hidden>'
print '<INPUT NAME=start value="'+start+'" type=hidden>'
print '<INPUT NAME=end value="'+end+'" type=hidden>'
print '<INPUT NAME=fileName value="'+fileName+'" type=hidden>'
print '<INPUT NAME=resources value="'+resources+'" type=hidden>'
print "</form>"

if diagnostics:
	print "<hr>"
	print diagnostics

print "</BODY>"
print "</HTML>" 
