# CLI utility that manages the purges.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/cli/purges.py,v $
# $State: Exp $

import sys
import sqmail.db
import sqmail.vfolder
import sqmail.purges
import sqmail.utils
import getopt
import cPickle
import time

def usage():
	print "Syntax: " + sys.argv[0] + " purges subcommand"
	print "  list               Lists all purges"
	print "  show <name>        Show information on one purge"
	print "  unset <name>       Removes a purge"
	print "  set <name> <vfolderno> <condition>"
	print "                     Adds a new purge or modifies one"
	print "  enable <name>      Enables a purge"
	print "  disable <name>     Disables a purge"
	print "  test               Tests the purges and reports results"
	print "  execute [<name>]   Executes one or all purges"
	print "WARNING! Purged messages are gone, forever. If you make a mistake with"
	print "an SQL query you may wipe your entire database. Only enable purges"
	print "you know work! Test your purges before you enable them!"
	
# If you don't know what this does, you shouldn't be reading this

def yesno(c):
	if c:
		return "Yes"
	return "No"

# Works out the name of a folder from the ID

def foldername(id):
	if (id == 0):
		return "All messages"
	try:
		vf = sqmail.vfolder.VFolder(id=id)
		return vf.name
	except KeyError:
		return "Invalid folder ID"

# Create a new purge, or change an existing one.

def new_purge():
	if (len(sys.argv) != 6):
		usage()
		sys.exit(2)
	
	name = sys.argv[3]
	vfolder = int(sys.argv[4])
	condition = sys.argv[5]
	print "Updating `%s'" % name

	p = sqmail.purges.Purge(name, 0, vfolder, condition)
	p.save()

# Deletes a purge.

def remove_purge():
	if (len(sys.argv) != 4):
		usage()
		sys.exit(2)
	
	name = sys.argv[3]
	try:
		p = sqmail.purges.Purge(name)
	except KeyError:
		print "No purge of that name could be found."
		sys.exit(1)
	
	print "Deleting `%s'" % name
	p.delete()

# List all purges.

def list_purges():
	if (len(sys.argv) != 3):
		usage()
		sys.exit(2)
	
	list = sqmail.purges.enumerate()
	print "%-11s %-7s %-20s %-35s" % ("Name", "Active?", "Vfolder", "Condition")
	print "----------------------------------------------------------------------------"
	for name in list:
		p = sqmail.purges.Purge(name)
		s = "%d (%s)" % (p.vfolder, foldername(p.vfolder))
		print "%-15s %-3s %-20s %-35s" % (p.name, yesno(p.active), s, \
			p.condition)

# Show information on one purge.

def show_purge():
	if (len(sys.argv) != 4):
		usage()
		sys.exit(2)
	
	name = sys.argv[3]
	try:
		p = sqmail.purges.Purge(name)
	except KeyError:
		print "No purge of that name could be found."
		sys.exit(1)
	print "Purge name:      ", p.name
	print "Enabled?         ", yesno(p.active)
	print "Based on vfolder:", p.vfolder, "=", foldername(p.vfolder)
	print "SQL condition:"
	print p.condition

# Enables/disables a purge

def enable_disable_purge(onoff):
	if (len(sys.argv) != 4):
		usage()
		sys.exit(2)
	
	name = sys.argv[3]
	try:
		p = sqmail.purges.Purge(name)
	except KeyError:
		print "No purge of that name could be found."
		sys.exit(1)
	
	if onoff:
		print "Enabling `%s'" % name
		p.active = 1
	else:
		print "Disabling `%s'" % name
		p.active = 0
	p.save()

# Test all purges.

def test_purges():
	if (len(sys.argv) != 3):
		usage()
		sys.exit(2)
	
	list = sqmail.purges.enumerate()
	print "%-15s  Messages to be purged" % "Name"
	print "----------------------------------------------------------------------------"
	for name in list:
		p = sqmail.purges.Purge(name)
		removed = p.count_matching()
		total = p.count_total()

		sys.stdout.write("%-15s  would delete %d of %d" % (name, removed, total))
		if p.active:
			print
		else:
			print ", but not enabled"

# Execute one or all purges.

def execute_purges():
	if (len(sys.argv) == 3):
		# Execute all purges.
		for purge in sqmail.purges.enumerate():
			purge_one(purge)
	elif (len(sys.argv) == 4):
		# Execute one purge.
		purge = sys.argv[3]
		try:
			purge_one(purge)
		except KeyError:
			print "No purge of that name could be found."
			sys.exit(1)

	else:
		usage()
		sys.exit(2)

def purge_one(purge):
	p = sqmail.purges.Purge(purge)
	sys.stdout.write(purge)
	sys.stdout.write("... ")
	sys.stdout.flush()
	
	p = p.purge_now()
	if (p == None):
		sys.stdout.write("disabled\n")
	else:
		sys.stdout.write("deleted %d messages out of %d\n" % p)

def SQmaiLPurges():	
	if (len(sys.argv) < 3):
		usage()
		sys.exit(2)

	cmd = sys.argv[2]
	if (cmd == "set"):
		new_purge()
	elif (cmd == "unset"):
		remove_purge()
	elif (cmd == "list"):
		list_purges()
	elif (cmd == "show"):
		show_purge()
	elif (cmd == "test"):
		test_purges()
	elif (cmd == "enable"):
		enable_disable_purge(1)
	elif (cmd == "disable"):
		enable_disable_purge(0)
	elif (cmd == "execute"):
		execute_purges()
	else:
		usage()
		sys.exit(2)


# Revision History
# $Log: purges.py,v $
# Revision 1.2  2001/03/01 19:55:38  dtrg
# Completed the command-line based purges system. Hesitantly applied it to
# my own data. Nothing catastrophic has happened yet.
#
# Revision 1.1  2001/02/23 19:50:26  dtrg
# Lots of changes: added the beginnings of the purges system, CLI utility
# for same, GUI utility & UI for same, plus a CLI vfolder lister.
#
