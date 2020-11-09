#!/usr/bin/env python3
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

import os
import sys
import cgi
from common import *
sys.path.append(tape_db_dir)
import tapelib

print("Content-type: text/html\n")
print("<!DOCTYPE html>")
print("<HTML lang=\"en\">")
print_copyright()
print("<HEAD>")
print("<META charset=\"utf-8\">")
print("<TITLE>EISCAT data download</TITLE>")
print("</HEAD>")
print("<BODY>")

if not su(raddr()):
    print("</BODY></HTML>")
    sys.exit()

params = cgi.FieldStorage()

quto = []
owner = []
for key in params:
    if key != 'r':
        owner.append(key)
        quto.append(params.getvalue(key))
ownerstr = ''
for i in range(len(owner)):
    if int(quto[i]) == 100:
        ownerstr = owner[i]
        break
    elif int(quto[i]) > 0:
        ownerstr = ownerstr + owner[i] + '(' + quto[i] + ')'
value = params.getvalue("r")
if not value:
    print("No data sets were chosen.")
    sys.exit()
ids = value.split()
filename = params.getvalue('filename', 'data')

sql = tapelib.opendefault()

locs = []
info = 0
for id in ids:
    ls = sql.select_experiment_storage_union("resource.resource_id = %s", (id,), what="antenna, experiment_name, start, end, type")[0]
    if ls.type == 'data':
        testls = sql.select_experiment_storage_union("experiments.antenna=%s AND experiment_name=%s AND start=%s AND end=%s AND type='data'", (ls.antenna, ls.experiment_name, ls.start, ls.end), what="resource.resource_id AS r")
        for rr in testls:
            if rr.r != int(id):
                print("Not unique data, change table??")
                print(ls)
                print(testls)
                sys.exit()
        locs.append(ls)
    else: info = info+1

qfile = open('/home/chn/quota.txt', 'a')
for ls in locs:
    print('%s\t%s\t%s\t%s\t%s' % (ls.experiment_name, ls.antenna, ls.start, ls.end, ownerstr))
    qfile.write('%s\t%s\t%s\t%s\t%s\n' % (ls.experiment_name, ls.antenna, ls.start, ls.end, ownerstr))
    print('<br>')

qfile.close()
print('<hr>')
if info:
    print("Info directories are common property<br>")
print('<a href="javascript:history.go(-4);" title="go back to schedule">Back</a>')
disconnect_db(sql.cur)

print("</BODY></HTML>")
