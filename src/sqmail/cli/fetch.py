# Incorporate messages into the database.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/cli/fetch.py,v $
# $State: Exp $

import sys
import string
import time
import getpass
import mailbox
import rfc822
import sqmail.db
import sqmail.message
import sqmail.vfolder
import getopt
import os.path
import cPickle
import time

def usage():
	print "Syntax: " + sys.argv[0] + " fetch <cmd>"
	print "Available commands:"
	print "  file [<filename>]  Reads a single message from a file"

def fetch_file():
	if (len(sys.argv) == 3):
		infp = sys.stdin
	elif (len(sys.argv) == 4):
		inname = sys.argv[3]
		infp = open(inname, "r")
		if not infp:
			print "File not found"
			sys.exit(1)
	else:
		usage()
		sys.exit(2)

	msg = rfc822.Message(infp)
	sqmsg = sqmail.message.Message()
	sqmsg.loadfrommessage(msg)
	sqmsg.savealltodatabase()
  
def SQmaiLFetch():	
	if (len(sys.argv) < 3):
		usage()
		sys.exit(2)
	
	cmd = sys.argv[2]
	if (cmd == "file"):
		fetch_file()
	else:
		usage()
		sys.exit(2)

# Revision History
# $Log: fetch.py,v $
# Revision 1.1  2001/05/23 10:49:37  dtrg
# Added the ability to incorporate messages into the database without the
# GUI. (Currently just for single messages.)
#
