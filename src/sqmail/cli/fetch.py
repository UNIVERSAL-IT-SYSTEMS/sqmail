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
	print "  file [<filename>]  Reads a single message from a file.  If"
	print "                     <filename> is absent, read from stdin."

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
	sqmail.vfolder.filter_incoming(sqmsg)
  
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
# Revision 1.3  2001/08/06 20:43:20  bescoto
# One line document change
#
# Revision 1.2  2001/06/08 04:38:16  bescoto
# Multifile diff: added a few convenience functions to db.py and sequences.py.
# vfolder.py and queries.py are largely new, they are part of a system that
# caches folder listings so the folder does not have to be continually reread.
# createdb.py and upgrade.py were changed to deal with the new folder formats.
# reader.py was changed a bit to make it compatible with these changes.
#
# Revision 1.1  2001/05/23 10:49:37  dtrg
# Added the ability to incorporate messages into the database without the
# GUI. (Currently just for single messages.)
#
