#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# $Header: /home/chn/repos/eiscat-web/schedule/schedule.cgi,v 1.25 2013/05/13 13:04:10 ingemar Exp $
#
# This script generates operational calendars
#
#--------------------------------------------------------------------------
#        Copyright 1998-2003 EISCAT Scientific Association.
#        Permission to use, copy, and distribute, for non-commercial purposes,
#        is hereby granted without fee, provided that this license information
#        and copyright notice appear in all copies.
#--------------------------------------------------------------------------
#
# Written 26 September 1998
# Minor modifications 9 October 2001 v1.41 bi
# Converted from expect to python 11 June 2002 ch
# Using SQL database instead of textfiles 23 April 2003 ch
#
# Last modified Carl-Fredrik Enell  2020: Remote madrigal interface w cached lists of experiments
# Python3 rewrite Carl-Fredrik Enell 2020

import calendar
import time
import urllib.error
import urllib.parse
import urllib.request
import cgi
import re
import sys
import os
import pickle
from madrigalWeb.madrigalWeb import MadrigalData
from common import *
sys.path.append(tape_db_dir)
import tapelib

versionNumber = "$Revision: 3.8 $".split()[1]

selections = (
        ("S", "Scheduled"),
        ("R", "Requested"),
        ("A", "Archived data"),
)

if madroot:
    madData = MadrigalData(madroot)
else:
    madData = []

# Global variables
madList = {} # Hold monthly Madrigal experiment lists
madMonth = ''

def months(i):
    return calendar.month_name[i]

def days(i):
    return calendar.day_abbr[i]

def madrigal(year, month, day, site):
    """check for analysed data in Madrigal"""
    if not madData:
        # Do not check
        return
    # do some translations. ugly.
    site = {'32m': 'lyr', '42m': 'lyr', 'esr': 'lyr', 'vhf': 'eis',
            'uhf': 'tro', 'kir': 'kir', 'sod': 'sod'}.get(site, site)

    monthStr = months(month)[:3].lower()
    analysisDir = "%s/%s/%02d%s%s" % (year, site, day, monthStr, str(year)[2:])

    # Check if experiment exists in Madrigal.
    global madList # Speedup: cache the experiment list between calls for same month
    global madMonth
    thisMadMonth = f"mad-{year}-{month}" #also used for filename
    if madMonth != thisMadMonth or not madList:
        #Check if we already have cached a list of this month's experiments in a file
        madMonth = thisMadMonth
        madListFile = os.path.join(madListDir, madMonth)
        try:
            with open(madListFile, 'rb') as f:
                madList = pickle.load(f)
        except:
            # File does not exist, search Madrigal for all local experiments for this month.
            lastDay = calendar.monthlen(year, month)
            madList = madData.getExperiments(0, year, month, 1, 0, 0, 0, year, month, lastDay, 23, 59, 59, 1)
            try:
                # Save the list to a file if possible
                with open(madListFile, 'wb') as f:
                    pickle.dump(madList, f)
            except:
                pass
    for expr in madList:
        if expr.url.endswith(analysisDir):
            return expr.realUrl # This is the Madrigal URL to analysisDir

def workingMonth_archived(year, month):
    "Collect all entries for the present month within the given class"
    dateField = '%d:%02d' % (year, month)
    lines = sql.select_experiment_resource_union("YEAR(start) = %s AND MONTH(start) = %s AND type = 'data'", (year, month))
    table = {}
    for l in lines:
        if l.antenna and l.antenna.upper() not in show_sites:
            if l.antenna.upper() != "UHF" or "TRO" not in show_sites:
                continue
        date, start = l.start.strftime("%Y-%m-%d %H:%M:%S").split()
        date2, end = l.end.strftime("%Y-%m-%d %H:%M:%S").split()
        if date2 > date:
            if start[:5] == '23:59':
                date = date2
                start = "00:00:00"
            else:
                end = "24:00:00"  # ugly but works ...
        day = int(date.split('-')[2])
        if l.account:
            l.country = l.account
        table.setdefault((day, l.experiment_name, l.antenna, l.country), ([])).append((start, end))

    print("<!-- number of entries: ")
    print(len(table))
    print("-->")
    table2 = {}
    for (day, title, site, country), (times) in list(table.items()):
        table2.setdefault(day, []).append((title, site, country, times))

    return table2

def outputLine_archived(day, dayName, lines, dateField):
    "output a line of the required schedule"
    "recover matching entries from the schedule database"

    if day not in lines:
        return 0
    for title, site, country, times in lines[day]:
        analysis = madrigal(year, month, day, site)
        link = tapeArchive +'?exp=' + title + '&date=%d%02d%02d' % (year, month, day)

        if not country:
            country = "  "
        outputVector = list(".       "*6 + ".")
        total = 0
        for start, end in times:
            # convert start and end times to units of 30 minutes (schedule granularity)
            start = int(start[:2])*3600 + int(start[3:5])*60 + int(start[6:])
            end = int(end[:2])*3600 + int(end[3:5])*60 + int(end[6:])
            diff = end - start
            assert diff >= 0
            total += diff
            for i in range((start+900)/1800, end/1800+1) or [(start+900)/1800]:
                outputVector[i] = 'A'

        outputVector = ''.join(outputVector)
        if analysis:
            outputVector = '<a href="'+analysis+'">'+outputVector+"</a>"
        print(dateField, dayName, outputVector, site, country, end=" ")
        print('(%4.1fh)' % (total/3600.0), end=" ")
        print('<a href="' + link + '">' + title + '</a>')
    return 1

def oneLine_archived(day, dayName, lines, dateField):
    "output a line of the required schedule"
    "recover matching entries from the schedule database"

    outputLines = 0
    outputVector = [0]*48
    total = 0
    if day in lines:
        for title, site, country, times in lines[day]:
            site = site.upper()
            if site == 'UHF': site = 'TRO'
            if site[2] == 'M': site = 'ESR'
            scode = show_sites.index(site)
            if 'scinti' in title: continue
            for start, end in times:
                # convert start and end times to units of 30 minutes (schedule granularity)
                start = int(start[:2])*3600 + int(start[3:5])*60 + int(start[6:])
                end = int(end[:2])*3600 + int(end[3:5])*60 + int(end[6:])
                diff = end - start
                assert diff >= 0
                total += diff
                t1 = int((start+60)/1800)
                t2 = int((end-60)/1800)+1
                for i in range(t1, t2):
                    outputVector[i] |= 1 << scode

    sys.stdout.write(' %s %s ' % (dateField, dayName))
    for i in range(48):
        sys.stdout.write('%x'%outputVector[i])
    sys.stdout.write('\n')
    return 1

def workingMonth_scheduled(year, month, status):
    "Collect all entries for the present month within the given class"
    regex = "("+"|".join(show_sites)+")"
    if 'R' in status:
        regex += " [^A]"
    else:
        regex += " [^RA]"
    pattern = "%s %02d \d+ \d+ \d+ " % (year, month) + regex
    pattern = re.compile(pattern).match
    lines = []
    for line in open(ScheduleDB):
        if pattern(line):
            lines.append(line)
    return lines

def workingMonth_remote(year, month, status):
    all_lines = []
    for url, their_sites in scheduled_urls:
        interesting = []
        # find the intersection of the both set of sites
        for site in their_sites:
            if site in show_sites:
                interesting.append(site)
        # if a match was found, query remote site
        if not interesting: continue

        post = "sites=%s&year=%s&month=%s&status=%s" % (
            "+".join(interesting), year, month, status)
        url += "remote_scheduled.cgi"
        import socket
        try:
            lines = urllib.request.urlopen(url + '?' + post).readlines()
            # do a small sanity check on the lines
            for line in lines:
                if len(line) > 10:
                    assert line.startswith(str(year))
                    all_lines.append(line)
        except (EnvironmentError, socket.error, AssertionError):
            pass
    return all_lines

def oneLine_scheduled(day, dayName, lines, dateField):
    "recover matching entries from the schedule database"
    #1993 11 19 0100 0500 UHF 1    UK/FI/EI TKS H @missing

    outputLines = 0
    outputVector = [0]*48
    for line in lines:
        _, _, mday, start, end, site, status, _ = line.split(' ', 7)
        if int(mday) != int(day):
            continue
        if site == 'UHF': site = 'TRO'
        assert status != 'A'
        if status == 'P' or status == 'c': continue
        if not site in show_sites:
            continue
        # convert start and end times to units of 30 minutes (schedule granularity)
        t1 = int(start[:2])*2 + int(start[2:])/30
        t2 = int(end[:2])*2 + int(end[2:])/30
        scode = show_sites.index(site)
        for i in range(t1, t2):
            outputVector[i] |= 1<<scode
    sys.stdout.write(' %s %s ' % (dateField, dayName))
    for i in range(48):
        sys.stdout.write('%x'%outputVector[i])
        #sys.stdout.write(' 'bgcolor="#333333" using tables!!
    sys.stdout.write('\n')
    return 1

def outputLine_scheduled(day, dayName, lines, dateField):
    "output a line of the required schedule"
    "recover matching entries from the schedule database"
    #1993 11 19 0100 0500 UHF 1    UK/FI/EI TKS H @missing

    outputLines = 0
    for line in lines:
        _, _, mday, start, end, site, status, comment = line.split(' ', 7)
        if int(mday) != int(day):
            continue
        comment = comment.strip()
        assert status != 'A'
        title, infoFile = comment.split('@', 1)
        title = title.strip()

        # convert start and end times to units of 30 minutes (schedule granularity)
        t1 = int(start[:2])*2 + int(start[2:])/30
        t2 = int(end[:2])*2 + int(end[2:])/30

        outputVector = ""
        for i in range(49):
            if i >= t1 and i < t2 or i == t2 == 48:
                outputVector += status
            elif i%8:
                outputVector += ' '
            else:
                outputVector += '.'

        link = ''
        for url, their_sites in scheduled_urls:
            if site in their_sites:
                link = url
        print(dateField, dayName, outputVector, site, end=" ")
        if len(link) > 0 or os.path.exists(NotesDir + infoFile):
            link += commentViewer+ '?fileName=' + infoFile
            if status in '123456789PCI':
                link += '&Start=%s' % start
                link += '&End=%s' % end
            print('<a href="' + link +'">' + title + '</a>')
        else:
            print(title)
        outputLines = 1
    return outputLines

def spacerLine():
    "output a header/spacer line"
    print("           00UT    04UT    08UT    12UT    16UT    20UT    24UT")

def start_of_month():
    year, month, _, _, _, _, _, _, _ = time.gmtime()
    return time.mktime((year, month, 1, 0, 0, 0, -1, -1, 0))

def get_attributes(attr_list):
    d = os.environ
    k = list(d.keys())
    k.sort()
    attributes = {}
    for item in k:
        if (attr_list.count(item) > 0):
            attributes[item] = d.get(item)
    return attributes

def showloginName():
    attrs = get_attributes(attr_list)
    ident = get_attributes('Shib_Session_ID')
    print("<b>",)
    if 'Shib_Session_ID' in ident:
        print("Welcome ",)
        if 'displayName' in attrs:
            print(attrs.get('displayName'))
        elif 'cn' in attrs:
            print(attrs.get('cn'))
        elif 'sn' in attrs and 'givenName' in attrs:
            print(attrs.get('givenName'))
            print(" ")
            print(attrs.get('sn'))
        showLogout()
    else:
        print("You are not authenticated",)
    print("</b>")
# Main program starts here

# Start building the output page
print("Content-type: text/HTML\n")
print("<!DOCTYPE html>\n")
print("<HTML lang=\"en\">")
print_copyright()
print("<HEAD>")
print("<META charset=\"utf-8\">")
print("<TITLE>Autogenerated Schedule</TITLE>")
print("</HEAD>")
print("<BODY>")

# parse arguments
params = cgi.FieldStorage()

try:
    year = int(params['year'].value)
    assert firstYear <= year <= lastYear
except:
    year, _, _, _, _, _, _, _, _ = time.gmtime()
try:
    month = int(params['month'].value)
    assert 1 <= month <= 12
except:
    _, month, _, _, _, _, _, _, _ = time.gmtime()

if year == 2015 and month > 8:
    selections = (("S", "Scheduled"), ("R", "Requested"), ("A", "Archived data"),)
try:
    status = ""
    for code, desc in selections:
        if code in params:
            status += code
    assert status
except:
    status = "S"
try:
    Roger = params['Roger'].value
except:
    Roger = 0

show_sites = []

for code, desc in allsites:
    if code in params:
        show_sites.append(code)

# ugly hack...
if 'ESR' in show_sites: show_sites += ('32M', '42M')
if 'HEA' in show_sites: show_sites += ('HF', 'HOT')

if not show_sites:
    show_sites = [code for code, desc in sites]

cur_clock = start_of_month()
req_clock = time.mktime((int(year), int(month), 1, 0, 0, 0, -1, -1, 0))

sql = None
# pick up the database entries for this month
if 'A' in status:
    try:
        sql = tapelib.opendefault()
        theWorkingMonth_a = workingMonth_archived(year, month)
    except:
        print("Database down")
        status = status.replace('A', '')

if 'S' in status or 'R' in status:
    theWorkingMonth_s = workingMonth_scheduled(year, month, status)
    theWorkingMonth_s += workingMonth_remote(year, month, status)

showloginName()

print("<h2 align=center>" + site)

if req_clock < cur_clock:
    print("Operations,")
elif req_clock == cur_clock:
    print("Operations Schedule,")
else:
    print("Operations Planning,")

print("%s %d</h2>" % (months(month), year))

def print_form():
    print("<form>")
    print("<center><table border cellpadding=3>")
    print("<tr><td>")

    print("<table>")
    print("<tr><td>Year:</td><td><SELECT NAME=year value=%d>" % year)
    for y in range(firstYear, lastYear + 1):
        if y == year:
            print("<OPTION SELECTED VALUE=%d>%d" % (y, y))
        else:
            print("<OPTION VALUE=%d>%d" % (y, y))
    print("</SELECT></td>")
    print("<tr><td>Month:</td><td><SELECT NAME=month value=%d>"%month)
    for m in range(1, 13):
        if m == month:
            print("<OPTION SELECTED VALUE=%d>%s" % (m, months(m)))
        else:
            print("<OPTION VALUE=%d>%s" % (m, months(m)))
    print("</SELECT></td>")
    print("</table>")

    print("</td><td>")

    i = 0
    for code, desc in selections:
        if i: print("<br>")
        i += 1
        if code in status:
            print("<INPUT TYPE=CHECKBOX NAME=" + code + " CHECKED>", desc)
        else:
            print("<INPUT TYPE=CHECKBOX NAME=" + code + ">", desc)

    print("</td>")

    print("<td><table>")
    i = 0
    for code, desc in allsites:
        if i % 3 == 0: print("<tr>")
        i += 1
        print("<td>")
        if code in show_sites:
            print("<INPUT TYPE=CHECKBOX NAME="+code+" CHECKED>", desc)
        else:
            print("<INPUT TYPE=CHECKBOX NAME="+code+">", desc)
        print("</td>")
    print("</table></td>")

    print("<td><input type=submit value=Query></td>")
    print("</tr></table></center>")
    print("</form>")

print_form()

print("<hr>")

# TABLE

print("<pre>")

startingWday, numberOfDays = calendar.monthrange(year, month)

if startingWday % 7: spacerLine()

for day in range(numberOfDays):
    wday = (day+startingWday)%7
    if not wday:
        spacerLine()
    dateField = "%s:%02d:%02d"%(year, month, day+1)
    i = 0
    if 'A' in status:
        if Roger:
            i += oneLine_archived(day+1, days(wday), theWorkingMonth_a, dateField)
        else:
            i += outputLine_archived(day+1, days(wday), theWorkingMonth_a, dateField)
    if 'S' in status or 'R' in status:
        if Roger:
            show_sites = ['TRO', 'VHF', ' HEA']
            i += oneLine_scheduled(day + 1, days(wday), theWorkingMonth_s, dateField)
        else:
            i += outputLine_scheduled(day + 1, days(wday), theWorkingMonth_s, dateField)
    if not i:
        outputVector = ".       "*6+"."
        print(dateField, days(wday), outputVector)

print("</pre>")

print("<h6 align=center>Prepared at" + time.strftime("%H:%M UT %a %b %d %Y"))
print("- Autoscheduler Vn" + versionNumber+ "(" +site + "system)")
print("</h6>")
print("<hr>")

print_form()
print(sched_legend)

if sql:
    disconnect_db(sql.cur)

print("</BODY>")
print("</HTML>")
