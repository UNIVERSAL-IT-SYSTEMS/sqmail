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
	global sqmail
	cursor = sqmail.db.cursor()
	version = sqmail.utils.getsetting("vfolder data version", "0.1")
	if (version == "0.1"):
		import sqmail.vfolder
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

	if (version == "0.2"):
		print "Upgrading vfolder data from 0.2 to 0.3"
		try: cursor.execute("DROP TABLE vfolders_temp")
		except sqmail.db.db().OperationalError: pass
		cursor.execute("RENAME TABLE vfolders TO vfolders_temp")
		cursor.execute("""
            CREATE TABLE vfolders
                (id INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
                 name TEXT,
                 size INTEGER UNSIGNED,
                 unread INTEGER UNSIGNED,
                 curmsg INTEGER UNSIGNED,
                 curmsgpos INTEGER UNSIGNED,
                 query TEXT,
                 children TEXT)""")
		cursor.execute("INSERT INTO vfolders (name, query, children) "
					   "VALUES ('/', '1', '')")

		oldfolderids, oldfolderparents = {}, {}
		for row in sqmail.db.fetchall("SELECT id,name,query,parent "
									  "FROM vfolders_temp"):
			oldfolderids[row[0]] = [row[1], row[2], row[3]]
			if not oldfolderparents.has_key(row[3]):
				oldfolderparents[row[3]] = []
			if not oldfolderparents.has_key(row[0]):
				oldfolderparents[row[0]] = []
			oldfolderparents[row[3]].append(row[0])

		import sqmail.vfolder
		oldtonew = {0:1}
		newparents = [0]
		while newparents:
			newparentcopy = newparents
			newparents = []
			for parent in newparentcopy:
				for child in oldfolderparents[parent]:
					childrow = oldfolderids[child]
					vf = sqmail.vfolder.create_vfolder(childrow[0],
													   oldtonew[parent],
													   childrow[1])
					oldtonew[child] = vf.id
					newparents.append(child)
		sqmail.utils.setsetting("vfolder data version", "0.3")
		

def upgrade_purges():
	cursor = sqmail.db.cursor()
	version = sqmail.utils.getsetting("purges data version")
	if (version == None):
		print "Adding new purges data."
		cursor.execute( \
			"CREATE TABLE purges"\
			"  (active TINYINT,"\
			"  name TEXT,"\
			"  vfolder INTEGER,"\
			"  condition TEXT)");

		sqmail.utils.setsetting("purges data version", "0.2")

def upgrade_data():
	cursor = sqmail.db.cursor()
	version = sqmail.utils.getsetting("message data version")
	if (version == None):
		print "Converting message data."
		sqmail.utils.setsetting("message data version", "0.3")

def upgrade_picons():
	cursor = sqmail.db.cursor()
	version = sqmail.utils.getsetting("picons data version")
	if (version == None):
		print "Adding new picons data."
		cursor.execute( \
			"CREATE TABLE picons"\
			"  (email VARCHAR(128) PRIMARY KEY NOT NULL,"\
			"  image TEXT)");
		sqmail.utils.setsetting("picons data version", "0.2")

def upgrade_sequences():
	cursor = sqmail.db.cursor()
	version = sqmail.utils.getsetting("sequences data version")
	if version == None:
		print "Creating sequence tables"
		cursor.execute("""CREATE TABLE sequence_data
                          (sid INTEGER UNSIGNED NOT NULL,
                           id INTEGER UNSIGNED NOT NULL,
                           UNIQUE INDEX sidid (sid, id))""")
		cursor.execute("""CREATE TABLE sequence_temp
                          (sid INTEGER UNSIGNED NOT NULL,
                           id INTEGER UNSIGNED NOT NULL,
                           UNIQUE INDEX sidid (sid, id))""")
		cursor.execute("""CREATE TABLE sequence_descriptions
                          (sid INTEGER UNSIGNED NOT NULL
                               AUTO_INCREMENT PRIMARY KEY,
                           name TEXT NOT NULL,
                           misc LONGBLOB)""")
		setsetting(cursor, "sequences data version", "0.0")

def SQmaiLUpgrade():	
	if (len(sys.argv) != 2):
		usage()
		sys.exit(2)
	
	print "Beginning upgrade"
	upgrade_vfolders()
	upgrade_purges()
	upgrade_data()
	upgrade_picons()
	upgrade_sequences()
	print "Finished upgrade"

# Revision History
# $Log: upgrade.py,v $
# Revision 1.5  2001/06/08 04:38:16  bescoto
# Multifile diff: added a few convenience functions to db.py and sequences.py.
# vfolder.py and queries.py are largely new, they are part of a system that
# caches folder listings so the folder does not have to be continually reread.
# createdb.py and upgrade.py were changed to deal with the new folder formats.
# reader.py was changed a bit to make it compatible with these changes.
#
# Revision 1.4  2001/03/09 20:36:19  dtrg
# First draft picons support.
#
# Revision 1.3  2001/03/05 20:44:41  dtrg
# Lots of changes.
# * Added outgoing X-Face support (relies on netppm and compface).
# * Rearrange the FileSelector code now I understand about bound and unbound
# method calls.
# * Put in a workaround for the MimeReader bug, so that when given a message
# that triggers it, it fails cleanly and presents the user with the
# undecoded message rather than eating all the core and locking the system.
# * Put some sanity checking in VFolder so that attempts to access unknown
# vfolders are trapped cleanly, rather than triggering the
# create-new-vfolder code and falling over in a heap.
#
# Revision 1.2  2001/02/23 19:50:26  dtrg
# Lots of changes: added the beginnings of the purges system, CLI utility
# for same, GUI utility & UI for same, plus a CLI vfolder lister.
#
# Revision 1.1  2001/01/19 20:34:55  dtrg
# Added the recover and upgrade commands, plus the back-end code. recover
# will let you rebuild various bits of the database (currently just the
# vfolderlist). upgrade upgrades one version of the database to another.
#
