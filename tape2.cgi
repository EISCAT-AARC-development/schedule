#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     List information on a specified tape number
#
#--------------------------------------------------------------------------
#     Copyright 1998 EISCAT Scientific Association. 
#     Permission to use, copy, and distribute, for non-commercial purposes, 
#     is hereby granted without fee, provided that this license information 
#     and copyright notice appear in all copies.
#--------------------------------------------------------------------------

from common import *

import os, sys, re, cgi, time

sys.path.append(tape_db_dir)
import tapelib

print "Content-type: text/HTML\n"
print "<HTML>"
print_copyright()
myhost=su(raddr())

params = cgi.FieldStorage()

tapeNumber = params.getvalue('tape','')
if not tapeNumber.isdigit():
	tapeNumber = ''
date_in = params.getvalue('date','')
if date_in:
	year_in = date_in[0:4]
	month_in = date_in[4:6]
	day_in = date_in[6:8]
	hour_in = date_in[8:10]
else:
	year_in = params.getvalue('year','')
	month_in = params.getvalue('month','')
	day_in = params.getvalue('day','')
	hour_in = params.getvalue('hour','')
do_download = params.getvalue('dl', '')
siteCode = params.getvalue('site','')
#tapeType = params.getvalue('type','')
experiment = params.getvalue('exp','')
if experiment.count(' ') > 0: # Hmm, get back pluses to exp name
	nosp=0
	for expparts in experiment.split(' '):
		if nosp==0:
			experiment=expparts
		else:
			experiment=experiment+'+'+expparts
		nosp+=1

if experiment.count('@') == 1:
	exp_wo_antenna, antenna = experiment.split('@')
else:
	exp_wo_antenna, antenna = experiment, ''

if siteCode:
	title = "Summary of Experiments known at "+site
else:
	title = site+" data archiver: Tape Contents"

print "<HEAD>"
print "<TITLE>"+title+"</TITLE>"
print "</HEAD>"
print "<BODY>"
print "<h3 align=center>"+title+"</h3>"
print "<form><center>"

script_name = os.path.basename(sys.argv[0])
def linkto(text, query=None, script=script_name):
	if query: return '<a href="'+script+'?'+query+'">'+text+'</a>'
	else: return '<a href="'+script+'">'+text+'</a>'

if siteCode:
	if not siteCode: siteCode = "95"
#if not tapeType: tapeType = "S"
	if not year_in: year_in = time.strftime("%Y")

#	tapePrefix = 'site copy'
#	for prefix, code, comment in (
#			('site copy', 'S', 'Site'),
#			('archive tape', 'A', 'Archive'),
#			('user copy', 'U', 'User copies'),
#		):
#		if tapeType == code:
#			print "<input type=radio name=type value="+code+" checked>",comment
#			tapePrefix = prefix
#		else:
#			print "<input type=radio name=type value="+code+">",comment
#	print "<br>"

	siteFound = 0
	for code, comment in (
			('ESR', 'ESR'),
			('KIR', 'Kiruna'),
			('UHF', 'Troms&oslash; UHF'),
			('SOD', 'Sodankyl&auml;'),
			('VHF', 'Troms&oslash; VHF'),
		):
		if siteCode == code:
			print "<input type=radio name=site value="+code+" checked>",comment
			siteFound = 1
		else:
			print "<input type=radio name=site value="+code+">",comment
	print "<br>"
	print "Year: <INPUT NAME=year size=4 value="+year_in+">"
	print "<input type=submit value=Query>"
	print ' &nbsp; <a href="'+script_name+'">Search by tape or date</a>'
else:
	print "Tape number: <INPUT NAME=tape size=12 value="+tapeNumber+">"
	print "or search by date:<br>"
	print "Experiment: <INPUT NAME=exp size=12 value="+experiment+">"
	print "Year: <INPUT NAME=year size=4 value="+year_in+">"
	print "Month: <INPUT NAME=month size=2 value="+month_in+">"
	print "Day: <INPUT NAME=day size=2 value="+day_in+">"
	print "Hour: <INPUT NAME=hour size=2 value="+hour_in+">"
	print "<input type=submit value=Query>"
	print ' &nbsp; <a href="'+script_name+'?site=ask">Site summaries</a>'

print "</center></form>"

print "<pre><hr>"

sql = tapelib.opendefault()
#sql = tapelib.openzfs()

def tape_comment(tape):
	return sql.get_tape_comment(tape)

def search_by_tape():
	# search by tape number
	org_tape = tapeNumber
	url = tapelib.create_tapeurl(tapeNumber, '%')
	lines = sql.select_experiment_storage_union("location LIKE %s", (url,), what="*, UNIX_TIMESTAMP(end) AS unix_end")

	if not lines:
		print "Tape",tapeNumber,"does not exist."
		return

	if tapeNumber[:2] == '95':
		print "EISCAT Svalbard Radar, Data Archive"
	elif tapeNumber[:2] == '75':
		print "EISCAT Svalbard Radar, Data Archive"
	else:
		print "EISCAT UHF Radar, Data Archive"

	c = tape_comment(tapeNumber)
	text = 'Tape #'+tapeNumber
	if c: text += ": "+c
	print text
	dump_lines_tape(lines)

def classify_location(url):
	x = tapelib.parse_raidurl(url)
	if x: return ("raid", x[0])
	x = tapelib.parse_tapeurl(url)
	if x: return ("tape", x[0])
	return ("unkn", url)

def search_by_date():
	if not re.match("[\w._+-:%]+$", exp_wo_antenna) or not re.match('(\w\w\w)?$', antenna):
		print "Illegal experiment name."
		return

	try:
		date = year_in
		if month_in:
			date += "%02d"%int(month_in)
			if day_in:
				date += "%02d"%int(day_in)
				if hour_in:
					date += " %02d"%int(hour_in)

		start, end = tapelib.parse_times(date)
	except ValueError:
		print "Illegal date specification:",`date`
		return

	if antenna:
		if do_download:
			experiments = sql.select("experiments",
				experiment_name=exp_wo_antenna, antenna=antenna)
		else:
			experiments = sql.union_select("experiments",
				experiment_name=exp_wo_antenna, antenna=antenna)
	else:
		if do_download:
			experiments = sql.select("experiments",
				experiment_name=exp_wo_antenna)
		else:
			experiments = sql.union_select("experiments",
				experiment_name=exp_wo_antenna)

	if not experiments:
		print "Experiment "+experiment+" not found in database."
		return
	lines = []
	all_sources = {}
	cutted = 0
	show_download = 0
	wildcard = 0
	limit = 999
	if exp_wo_antenna.count('%') > 0 and not myhost:
		wildcard = 1
	if myhost:
		limit = 5000
	for e in experiments:
		if do_download:
			datasets = sql.select_resource(e.experiment_id, start, end, "",limit)
		else:
			datasets = sql.select_union_resource(e.experiment_id, start, end, limit)
		if not datasets: continue
		if len(datasets) >= limit: cutted = 1
		expstring = (e.country or "??")+" "+e.antenna+" "+e.experiment_name
		for d in datasets:
			if d.type != 'info' or not wildcard:
				if do_download:
					storages = sql.select("storage", resource_id=d.resource_id)
				else:
					storages = sql.union_select("storage", resource_id=d.resource_id)
				locations = []
				for s in storages:
					l = s.location
					id = classify_location(l)
					if do_download or not myhost:
						if id[0] != 'raid': continue
						show_download=1
						id = ('raid', None)
						d.bytes = s.bytes
					elif id[0] == 'raid': show_download=1
					locations.append(id)
					all_sources[id] = None
					if do_download: break
				if locations:
					if d.account:
						lines.append((d.account+expstring[2:], d, locations))
					else: lines.append((expstring, d, locations))

	if not lines:
		print date,"not found in database"
		return

	if do_download:
		#print '<FORM ACTION=download.cgi NAME=kalven>',
		print '<FORM method=POST ACTION=download.cgi NAME=kalven>',
	print "The Data Archive has the following entries for data at",date+":"
	dump_lines(all_sources, lines)

	if wildcard:
		print "Info directories not shown for wild card selections"
	if do_download:
		print "Select the data sets that you want to download.",
		print """<script><!--"
function invert() {
e=document.kalven.elements;
for(i=1;i<e.length;i++) e[i].checked^=1; }
document.write("<input TYPE=BUTTON VALUE='Invert selection' ONCLICK='invert();'>")
--></script>"""
		print "MATLAB files are individually compressed with bzip2."
		#print "Please Select format:",
		#print "<input type=radio name=format value=tar checked>tar",
		#print "<input type=radio name=format value=tgz>tgz",
		#print "<input type=radio name=format value=zip disabled>zip"
		print "<input type=hidden name=format value=tar>"
		#print "<input type=submit value='Download checked'>",
		print "<input type=hidden name=maxtar value=2>"
		print "<input type=submit name=submit value='Download'>",
		print "<input type=hidden name=filename value="+experiment+date[0:8]+date[9:11]+">",
		#print "<input type=submit name=submit value='Analyse' disabled>",
		print "<input type=submit name=submit value='Analyse'>",
		print "<input type=submit name=submit value='Plot'>",
		if myhost:
			print "<input type=submit name=submit value='Quota'>",
		print "</FORM>"
		print """Be sure to read the <strong>EISCAT rules of the road</strong> <a href="/scientist/data/#rules">[HTML]</a> <a href="/wp-content/uploads/2016/03/Rules.pdf">[PDF]</a> regarding access and use of this data."""
		print """<strong>Note that use of data newer than one year is restricted to the experimenter only.</strong>"""
	if cutted:
		print
		print "The result list was truncated due to too many results. Narrow your query"

	if show_download:
		print
		print linkto("Go to download page",
				"date="+date[0:8]+date[9:11]+"&exp="+quote(experiment)+"&dl=1")

def search_by_experiment():
	exp_pattern = '%'.join(re.split("[^\w._+-]", exp_wo_antenna))
	ant_pattern = '%'.join(re.split("[^\w]", antenna))
	exp_pattern = re.sub('%%+|^$', '%', exp_pattern)
	ant_pattern = re.sub('%%+|^$', '%', ant_pattern)
	print "Matching experiment "+exp_pattern.replace('%','*'),
	print "and antenna "+ant_pattern.replace('%','*')

	query = []
	values = []
	if exp_pattern != '%':
		query.append("experiment_name LIKE %s")
		values.append(exp_pattern)
	if ant_pattern != '%':
		query.append("antenna LIKE %s")
		values.append(ant_pattern)
	query = query and ' AND '.join(query) or "1"
	query += " ORDER BY experiment_name, antenna, start"

	if do_download:
		experiments = sql.select_experiment_resource(what="DISTINCT experiment_name, antenna, YEAR(start) AS year", query=query, values=values, limit=250)
	else:
		experiments = sql.select_experiment_resource_union(what="DISTINCT experiment_name, antenna, YEAR(start) AS year", query=query, values=values, limit=250)
	#experiments = sql.select("experiments", limit=250, **kwords)

	if not experiments:
		print "No experiments matches that."
	done = {}
	for e in experiments:
		if e.experiment_name not in done:
			print
			print linkto(e.experiment_name, "exp="+quote(e.experiment_name)),
			done[e.experiment_name] = 1
		n = e.experiment_name+'@'+e.antenna
		if n not in done:
			print
			print linkto(n, "exp="+quote(n))+':',
			done[n] = 1
		print linkto(str(e.year), "exp=%s&year=%s"%(quote(n), e.year)),

def dump_lines_tape(lines):
	print "Type",'',"Start date & time".ljust(19),'',"End date & time".ljust(19),'',"Experiment    Directory"
	for d in lines:
		_, path = tapelib.parse_tapeurl(d.location)
		print ' '.join((
				d.type, '',
				d.start.strftime("%Y-%m-%d %H:%M:%S"), '', d.unix_end and d.end.strftime("%Y-%m-%d %H:%M:%S") or " "*19, '',
				d.antenna, d.country or "??", d.experiment_name,
				path,
		))

def dump_lines(sources, lines):
	if type(sources) == type({}):
		sources = sources.keys()
	many = len(sources) > 1
	if many:
		sources.sort()
		print ' '*len(sources), " Sources"
	for i,x in enumerate(sources):
		if many:
			print '|'*i + ',' + '-'*(len(sources)-i),
		if x[0] == 'tape':
			nr = x[1]
			c = tape_comment(nr)
			text = 'Tape #'+linkto(str(nr), "tape=%s"%nr)
			if c: text += ": "+c
			print text
		elif x[0] == 'raid':
			if x[1]:
				print "RAID disk storage at \""+x[1]+'"'
			else:
				print "RAID disk storage"
		else:
			print x[1]

	if many:
		print '|'*len(sources),
	elif do_download:
		print "<input type=checkbox disabled>",
	print "Type",'',"Start date & time".ljust(19),'',"End date & time".ljust(19),'',"Experiment"
	for expname, d, ids in lines:
		if many:
			print ''.join([ s in ids and 'x' or ' ' for s in sources ]),
		elif do_download:
			print "<input type=checkbox name=r value=%d checked>"%d.resource_id,
		print ' '.join((
				d.type, '',
				d.start.strftime("%Y-%m-%d %H:%M:%S"), '', d.unix_end and d.end.strftime("%Y-%m-%d %H:%M:%S") or " "*19, '',
				expname, 'bytes' in d and '(%d kB)'%(d.bytes/1024) or ''
		))

def showSummaries():
	print "Total on tape:",
	url = tapelib.create_tapeurl('%','%')
	total = sql.select_resource_storage("type = 'data' AND location LIKE %s",
			(url,), what="SUM(UNIX_TIMESTAMP(end)-UNIX_TIMESTAMP(start)) AS time, SUM(bytes) AS bytes")
	t = total[0]
	t.time /= 86400
	t.bytes /= 2**30
	print t.time,"days and",t.bytes,"Gigabytes"

	print "Total on raid:",
	url = tapelib.create_raidurl('%','%')
	total = sql.select_resource_storage("type = 'data' AND location LIKE %s",
			(url,), what="SUM(UNIX_TIMESTAMP(end)-UNIX_TIMESTAMP(start)) AS time, SUM(bytes) AS bytes")
	t = total[0]
	t.time /= 86400
	t.bytes /= 2**30
	print t.time,"days and",t.bytes,"Gigabytes"

def show_headers():
  d = os.environ
  k = d.keys()
  k.sort()

  print "Env Variables"
  print "<hr><b>Environment Variables</b><ul>"
  for item in k:
    print "<li><B>%s</B>: %s </li>" % (item, d[item])
  print "</ul><hr>"

if siteCode:
	if siteFound:
		showSummaries()
	else:
		print "pick a site and a year and proceed."
else:
	if tapeNumber:
		search_by_tape()
	elif year_in:
		search_by_date()
	elif experiment:
		search_by_experiment()
	else:
		print "Enter required tape number and hit the Query button, or"
		print "leave tape number blank and enter date in numbers (as YYYY MM DD HH) and hit the Query button"

print "</pre><hr>"

print "<p align=center>Prepared at",time.strftime("%H:%M UT %a %b %d, %Y"),"</p>"
disconnect_db(sql.cur)

show_headers()
print "</BODY>"
print "</HTML>" 
