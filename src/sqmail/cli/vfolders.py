# CLI utility that manages vfolders.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/cli/vfolders.py,v $
# $State: Exp $

import sys
import sqmail.db
import sqmail.vfolder
import sqmail.utils
import getopt
import cPickle
import time

def usage():
	print "Syntax: " + sys.argv[0] + " vfolders subcommand"
	print "  list               Lists all vfolders"
	
# List all vfolders.

def listfolders(list, parent, indent):
	for i in list:
		vf = sqmail.vfolder.VFolder(id=i)
		if (vf.parent == parent):
			sys.stdout.write("% 4d " % i)
			sys.stdout.write(" "*indent)
			vf = sqmail.vfolder.VFolder(id=i)
			sys.stdout.write(vf.name)
			sys.stdout.flush()
			l = 5 + indent + len(vf.name)
			sys.stdout.write(" " * (40 - l))
			sys.stdout.write("% 6d / %d" % (vf.getunread(), vf.getlen()))
			print
			listfolders(list, i, indent+2)

def list_vfolders():
	if (len(sys.argv) != 3):
		usage()
		sys.exit(2)
	
	print "  ID Name                               Unread / Total"
	print "-" * 75
	list = sqmail.vfolder.get_folder_list()
	listfolders(list, 0, 0)

def SQmaiLVFolders():	
	if (len(sys.argv) < 3):
		usage()
		sys.exit(2)

	cmd = sys.argv[2]
	if (cmd == "list"):
		list_vfolders()
	else:
		usage()
		sys.exit(2)


# Revision History
# $Log: vfolders.py,v $
# Revision 1.1  2001/02/23 19:50:26  dtrg
# Lots of changes: added the beginnings of the purges system, CLI utility
# for same, GUI utility & UI for same, plus a CLI vfolder lister.
#
