# CLI utility that manages the SQmaiL configuration settings.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/cli/settings.py,v $
# $State: Exp $

import sys
import sqmail.db
import sqmail.preferences
import sqmail.utils
import getopt
import cPickle
import time

def usage():
	print "Syntax: " + sys.argv[0] + " settings subcommand"
	print "  list               List all settings"
	print "  show <name>        Show the value of one setting"
	print "  unset <name>       Remove a setting"
	print "  set <name> <value> Change a setting"
	print "WARNING! This command can do all kinds of weird things. There is no"
	print "confirmation on anything because I am assuming that if you read this"
	print "warning, and go ahead anyway, you know what you are doing. If not,"
	print "tough. Nothing you can do here *ought* to change the message database,"
	print "but You Have Been Warned."
	
# List all settings in the database.

def list_settings():
	if (len(sys.argv) != 3):
		usage()
		sys.exit(2)
	
	cursor = sqmail.db.cursor()
	cursor.execute("SELECT name FROM settings")
	while 1:
		n = cursor.fetchone()
		if not n:
			break
		n = n[0]

		# "idcounter" is special. We don't let the user even *touch*
		# that.

		if (n == "idcounter"):
			continue

		v = sqmail.utils.getsetting(n)

		print n, "=", repr(v)

# Delete a setting.

def unset_setting():
	if (len(sys.argv) != 4):
		usage()
		sys.exit(2)
	
	setting = sys.argv[3]
	print "Removing setting '%s'" % setting

	cursor = sqmail.db.cursor()
	cursor.execute("DELETE FROM settings WHERE name = '"+sqmail.db.escape(setting)+"'")
	n = cursor.fetchone()

# Change a setting.

def set_setting():
	if (len(sys.argv) != 5):
		usage()
		sys.exit(2)
	
	setting = sys.argv[3]
	try:
		value = eval(sys.argv[4])
	except:
		print "Failed to evaluate the setting value."
		sys.exit(1)
	
	print "Setting '%s' =" % setting, repr(value)
	sqmail.utils.setsetting(setting, value)

# Show the value of one particular setting.

def show_setting():
	if (len(sys.argv) != 4):
		usage()
		sys.exit(2)
	
	setting = sys.argv[3]
	value = sqmail.utils.getsetting(setting)

	print setting, "=", repr(value)

def SQmaiLSettings():	
	if (len(sys.argv) < 3):
		usage()
		sys.exit(2)

	cmd = sys.argv[2]
	if (cmd == "list"):
		list_settings()
	elif (cmd == "unset"):
		unset_setting()
	elif (cmd == "set"):
		set_setting()
	elif (cmd == "show"):
		show_setting()
	else:
		usage()
		sys.exit(2)


# Revision History
# $Log: settings.py,v $
# Revision 1.1  2001/02/20 18:14:04  dtrg
# Added the settings command. This gives you a basic CLI to the settings
# database, which should let you play with the configuration without having
# to start the GUI.
#
