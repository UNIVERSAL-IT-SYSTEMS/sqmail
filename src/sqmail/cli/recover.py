# Attempts to recover some broken system
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/cli/recover.py,v $
# $State: Exp $

import sys
import string
import time
import getpass
import mailbox
import sqmail.db
import sqmail.message
import sqmail.vfolder
import getopt
import os.path
import cPickle
import time

def usage():
	print "Syntax: " + sys.argv[0] + " recover <cmd>"
	print "Available commands:"
	print "  vfolderlist        Rebuilds the vfolder list"
	print "If you have persistent problems, this command may help. Maybe."
	print "BACK EVERYTHING UP BEFORE USING!"

def recover_vfolderlist():
	cursor = sqmail.db.cursor()
	print "Rebuilding vfolder list."
	l = []
	cursor.execute("SELECT id FROM vfolders")
	while 1:
		i = cursor.fetchone()
		if not i:
			break
		l.append(i[0])
	sqmail.utils.setsetting("vfolders", l)
	print "Done."

def SQmaiLRecover():	
	if (len(sys.argv) != 3):
		usage()
		sys.exit(2)
	
	cmd = sys.argv[2]
	if (cmd == "vfolderlist"):
		recover_vfolderlist()
	else:
		usage()
		sys.exit(2)

# Revision History
# $Log: recover.py,v $
# Revision 1.1  2001/01/19 20:34:55  dtrg
# Added the recover and upgrade commands, plus the back-end code. recover
# will let you rebuild various bits of the database (currently just the
# vfolderlist). upgrade upgrades one version of the database to another.
#
