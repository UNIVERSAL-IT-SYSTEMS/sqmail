# Preference setting abstraction.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/preferences.py,v $
# $State: Exp $

import sqmail.utils
import sqmail.db
import cPickle
import getpass

# Transport

def get_incomingprotocol():
	return sqmail.utils.getsetting("incomingprotocol", \
		"Spool")
		
def get_incomingserver():
	return sqmail.utils.getsetting("incomingserver", \
		"")

def get_incomingport():
	return sqmail.utils.getsetting("incomingport", \
		0)

def get_incomingusername():
	return sqmail.utils.getsetting("incomingusername", \
		getpass.getuser())

def get_incomingpassword():
	return sqmail.utils.getsetting("incomingpassword", \
		"")

def get_deleteremote():
	return sqmail.utils.getsetting("deleteremote", \
		0)

def get_incomingpath():
	return sqmail.utils.getsetting("incomingpath", \
		"/var/spool/mail/"+getpass.getuser())

def get_fromaddress():
	return sqmail.utils.getsetting("fromaddress", \
		"(you have to set your from address)")

def get_outgoingserver():
	return sqmail.utils.getsetting("outgoingserver", \
		"localhost")

def get_outgoingport():
	return sqmail.utils.getsetting("outgoingport", \
		25)

def get_smtpdebuglevel():
	return sqmail.utils.getsetting("smtpdebuglevel", \
		1)

def get_defaultdomain():
	return sqmail.utils.getsetting("defaultdomain", \
		"")

# Appearances

def get_textmessagefont():
	return sqmail.utils.getsetting("textmessagefont", \
		"fixed")

def get_composefont():
	return sqmail.utils.getsetting("composefont", \
		"fixed")

def get_vfolderfont():
	return sqmail.utils.getsetting("vfolderfont", \
		"fixed")

def get_vfolderfg():
	return sqmail.utils.getsetting("vfolderfg", (0, 0, 0, 65535))

def get_vfolderbg():
	return sqmail.utils.getsetting("vfolderbg", (65535, 65535, 65535, 65535))

def get_vfolderunreadfont():
	return sqmail.utils.getsetting("vfolderunreadfont", \
		"fixed")

def get_vfolderunreadfg():
	return sqmail.utils.getsetting("vfolderunreadfg", (0, 0, 0, 65535))

def get_vfolderunreadbg():
	return sqmail.utils.getsetting("vfolderunreadbg", (65535, 65535, 65535, 65535))

def get_vfolderpendingfont():
	return sqmail.utils.getsetting("vfolderpendingfont", \
		"fixed")

def get_vfolderpendingfg():
	return sqmail.utils.getsetting("vfolderpendingfg", (32767, 32767, 32767, 65535))

def get_vfolderpendingbg():
	return sqmail.utils.getsetting("vfolderpendingbg", (65535, 65535, 65535, 65535))


def get_msglistfont():
	return sqmail.utils.getsetting("msglistfont", \
		"fixed")

def get_unreadmsglistfont():
	return sqmail.utils.getsetting("unreadmsglistfont", \
		"fixed")

def get_pendingmsglistfont():
	return sqmail.utils.getsetting("pendingmsglistfont", \
		"fixed")

# Miscellaneous

def get_quoteprefix():
	return sqmail.utils.getsetting("quoteprefix", \
		"> ")

#def get_spamcommand():
#	return sqmail.utils.getsetting("spamcommand", \
#		"echo 'You have not configured the spam command yet.'")

# Load & Save configuration

def save_config(filename):
	fp = open(filename, "w")
	d = {}
	cursor = sqmail.db.cursor()
	cursor.execute("SELECT name FROM settings")
	while 1:
		n = cursor.fetchone()
		if not n:
			break

		n = n[0]
		if (n != "idcounter"):
			d[n] = sqmail.utils.getsetting(n)
	
	cPickle.dump("SQmaiL preferences", fp)
	cPickle.dump(d, fp)
	fp.close()

def load_config(filename):
	fp = open(filename, "r")
	o = cPickle.load(fp)
	if (o != "SQmaiL preferences"):
		print "Not a valid preferences file!"
		return
	
	o = cPickle.load(fp)
	for i in o.keys():
		sqmail.utils.setsetting(i, o[i])
	
# Revision History
# $Log: preferences.py,v $
# Revision 1.1  2001/02/20 17:22:36  dtrg
# Moved the bulk of the preference system out of the gui directory, where it
# doesn't belong. sqmail.gui.preferences still exists but it just contains
# the preferences editor. sqmail.preferences now contains the access
# functions and load/save functions.
#
