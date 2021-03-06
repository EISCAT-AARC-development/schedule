#!/usr/bin/env python3
# -*- coding: utf-8 -*-
######## site configuration options #############
import os
import sys
import MySQLdb
sys.path.append('/var/www/auth')
sys.path.append('/home/archive/shared-auth')
from token_url_utility import *
from eiscat_auth import *

# name of this system
site = "data.eiscat.se"
# Trusted single ip
myip = '192.168.11.102/23'
# path to Schedule database (a text file)
ScheduleDB = "ScheduleDataBase"
# where to put the information about individial entries
# Don't forget the '/' at the end
NotesDir = "./notes/"
# url to the notes viewer
commentViewer = "comment.cgi"
tapeArchive = "tape2.cgi"
# tape_db directory
tape_db_dir = "/home/archive/tape_db"
#Port nr for the tape_db application
portno = 37009
# Set to false to disable checking of machines
check_machines = False

# List of attributes supported by schedule app
# The attribute short names must match what is configured in shibboleth attribute_map.xml
# attr_list = ["cn", "displayName", "givenName", "mail", "sn", "uid", "unscoped_affiliation","eppn"]
attr_list = ["sn", "givenName", "displayName", "distinguishedName", "mail", "mailVerified", "schacHomeOrganization", "eduPersonUniqueId", "eduPersonPrimaryAffiliation", "eduPersonScopedAffiliation", "eduPersonEntitlement", "eduPersonAssurance", "persistent-id"]

private_key = open('/var/www/auth/private_key.pem', 'r').read()
public_key = open('/var/www/auth/public_key.pem', 'r').read()

exp_seconds = 3600
download_times = 4

#SHould debug information be shown?
show_debug = True

# Remote Madrigal options, addition by CFE 2020
madroot = "https://portal.eiscat.se/madrigal/"
madViewer = "/madrigal/cgi-bin/madExperiment.cgi"
madListDir = "/var/www/mad_lists"

def raddr():
    raddr = os.environ['REMOTE_ADDR']
    if raddr == '192.168.11.5':
        try:
            r = os.environ['HTTP_X_FORWARDED_FOR'].split(',')
            return r[0]
        except: return raddr
    return raddr

def su(ip):
    raddr = os.environ['REMOTE_ADDR']
    ip32 = 0
    for ippart in ip.split('.'):
        ip32 = ip32*256 + int(ippart)
    net, mask = myip.split('/')
    net32 = 0
    for ippart in net.split('.'):
        net32 = net32*256 + int(ippart)
    if (ip32-net32)>>(32-int(mask)) == 0:
        return True
    return False

# database settings - for tape archive
def connect_db():
    try:
        database = MySQLdb.connect(user="www", db="tape_archive")
    except StandardError as why:
        print("<font color=red>The database server is currentry down.</font><br>")
        print("Reason: <i>" + str(why) + "</i>")
        sys.exit()
    return database.cursor()

def disconnect_db(cur):
    # displaying MySQL version is a security leak.
    # also: this functionis called disconnect, buit that is actually not what it is doing?
    cur.execute("SELECT VERSION()")
    ver = cur.fetchone()
        #if ver:
        #       print "<p align=right><i>Powered by MySQL version "+ver[0]+"</i></p>"
        #else:
        #       print "<p align=right><i>Powered by MySQL</i></p>"


# The sites available together with a 3-letter code
eiscat_sites = (        # used on EISCAT
        ("VHF", "VHF radar"),
        ("UHF", "Tristatic UHF"),
        ("TRO", "Troms&oslash; UHF"),
        ("KIR", "Kiruna receiver"),
        ("SOD", "Sodankyl&auml; receiver"),
        ("ESR", "Svalbard radar"),
        ("HEA", "HF heating/radar"),
)
leicester_sites = (     # Leiceseter sites
        ("SPE", "SPEAR"),
)

sites = eiscat_sites

### NEW since march 2004 -- importing schedule from remote sites ###
# some urls...
eiscat_url = "http://portal.eiscat.se/raw/schedule/"
leicester_url = "http://143.210.44.98/cgi-bin/scheduler/"
scheduled_urls = [
        # (url, list of sites which)
        (eiscat_url, ["VHF", "UHF", "TRO", "KIR", "SOD", "ESR", "HEA"]),
        (leicester_url, ["SPE"]),
]
allsites = eiscat_sites + leicester_sites
scheduled_urls = [(leicester_url, ["SPE"])]

# If you don't want to import from other sites, use these
#scheduled_urls = []
#allsites = sites

# the valid year range
firstYear = 1981; lastYear = 2020

sched_legend = """<hr><p align=center><b>KEY</b></p>
<pre>
       C = <a href="http://portal.eiscat.se/iswg">Common Programme</a>  1..9 = Special Programme    H = Heating
                                    (number=priority)
       P = Passive              R = Requested            M = Maintenance
     ESR = Svalbard IS radar  VHF = VHF IS radar       UHF = Tristatic UHF IS radar
     TRO = Troms&oslash; UHF system  KIR = Kiruna receiver    SOD = Sodankyl&auml; receiver
     HEA = HF (heating)

  <a href=submit.cgi>Requests</a> must be approved by the appropriate National Representative</a>
      CN = China               FI = Finland             FR = France
      GE = Germany             NI = Japan               NO = Norway
      SW = Sweden              UK = United Kingdom
      EI = EISCAT staff        3P = third party         TNA= TransNationalAccess
</pre><hr>
<p align=center>Please address questions and inquiries about schedules to
<a href="mailto:ingemar@eiscat.se">Ingemar Häggström</a>.
"""

# Determine who gets email when someone submits a new experiment
# late_submission = if there is less than 20 days on the month preceding
#                   the experiment month.
# choice          = which antenna is needed
def advert_new_submits(mailit_to, late_submission, choice):
    # used on eiscat:
    if late_submission:
        mailit_to('ingemar@eiscat.se')
    if choice == 'HEA':
        mailit_to('mike@eiscat.uit.no')
