# Upgrades data from an old version of the system.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/cli/upgrade.py,v $
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
	print "Syntax: " + sys.argv[0] + " upgrade"
	print "This command should only be used when migrating from one version"
	print "of SQmaiL to another. It is a not a command you should need to"
	print "use very frequently! Be careful. This may overwrite some data."
	print "BACK EVERYTHING UP BEFORE USING!"

def upgrade_vfolders():
	cursor = sqmail.db.cursor()
	version = sqmail.utils.getsetting("vfolder data version", "0.1")
	if (version == "0.1"):
		print "Upgrading vfolder data from 0.1 to 0.2."
		try:
			cursor.execute("drop table vfolders")
			cursor.execute ( \
				"CREATE TABLE vfolders"\
				"  (id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,"\
				"  name TEXT,"\
				"  query TEXT,"\
				"  parent INTEGER)");
		except sqmail.db.db().OperationalError:
			pass
		l = []
		parents = {}
		for vf in sqmail.vfolder.get_folder_list():
			query = sqmail.utils.getsetting("vfolder query "+vf)
			parent = sqmail.utils.getsetting("vfolder parent "+vf)
			id = sqmail.vfolder.vfolder_add(vf, query, 0)
			parents[id] = parent
			l.append(id)

		for vf in l:
			d = sqmail.vfolder.vfolder_get(vf)
			p = sqmail.vfolder.vfolder_find(parents[vf])
			if (p == None):
				p = 0
			sqmail.vfolder.vfolder_set(vf, d[0], d[1], p)

		sqmail.utils.setsetting("vfolders", l)
		sqmail.utils.setsetting("vfolder data version", "0.2")

def SQmaiLUpgrade():	
	if (len(sys.argv) != 2):
		usage()
		sys.exit(2)
	
	print "Beginning upgrade"
	upgrade_vfolders()
	print "Finished upgrade"

# Revision History
# $Log: upgrade.py,v $
# Revision 1.1  2001/01/19 20:34:55  dtrg
# Added the recover and upgrade commands, plus the back-end code. recover
# will let you rebuild various bits of the database (currently just the
# vfolderlist). upgrade upgrades one version of the database to another.
#
