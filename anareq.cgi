#!/usr/bin/env python3
from common import *
import cgi
import os
print("Content-type: text/html\n")
print("<!DOCTYPE html>")
print("<HTML lang=\"en\">")
print("<HEAD>")
print("<META charset=\"utf-8\">")
print("<TITLE>EISCAT analysis request</TITLE>")
print("</HEAD>")
print("<BODY>")

params = cgi.FieldStorage()
gfd = 'datapath t resultpath maxfsize name_expr expver siteid intper extra'
QUERY = ''
dup = '\''
special = '\"\\\"!{&()\'; '
nl = chr(10) + chr(13)
htref = os.environ['HTTP_REFERER']
method = os.environ['REQUEST_METHOD']

if method == 'POST' and htref.count('://data.eiscat.') and htref.count('/schedule/download.cgi'):
    for par in gfd.split():
        try:
            val = params.getvalue(par)
            for s in dup:
                val = val.replace(s, s+s)
            for s in special:
                val = val.replace(s, '\\'+s)
            for s in nl:
                val = val.replace(s, '#')
            val = val.replace('##', '#')
            QUERY = QUERY + par + '=' + val + ' '
        except:
            QUERY = QUERY + par + '= '
    QUERY = QUERY + 'REMOTE_ADDR=' + raddr()
    if su(raddr()):
        print(QUERY + '<br>')

    with open('anareg.txt', 'a') as req:
        result = req.write('%s\n' % QUERY)
        if(result):
            print("Your request has been noted.<br>")
            print("The result will be sent to the mail address you provided, when the analysis is finished.")
        else:
            print("<br>Error: could not open request file<br>")
else:
    print("Bad request.")
print("</BODY>")
print("</HTML>")
