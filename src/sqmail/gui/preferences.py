# Preference setting abstraction.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/preferences.py,v $
# $State: Exp $

import sqmail.gui.reader
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

# Appearances

def get_textmessagefont():
	return sqmail.utils.getsetting("textmessagefont", \
		"-schumacher-clean-medium-r-normal-*-14-*-*-*-c-*-iso646.1991-irv")

def get_composefont():
	return sqmail.utils.getsetting("composefont", \
		"-schumacher-clean-medium-r-normal-*-14-*-*-*-c-*-iso646.1991-irv")

def get_vfolderfont():
	return sqmail.utils.getsetting("vfolderfont", \
		"-schumacher-clean-medium-r-normal-*-14-*-*-*-c-*-iso646.1991-irv")

def get_vfolderfg():
	return sqmail.utils.getsetting("vfolderfg", (0, 0, 0, 1.0))

def get_vfolderbg():
	return sqmail.utils.getsetting("vfolderbg", (1.0, 1.0, 1.0, 1.0))

def get_vfolderunreadfont():
	return sqmail.utils.getsetting("vfolderunreadfont", \
		"-schumacher-clean-medium-r-normal-*-14-*-*-*-c-*-iso646.1991-irv")

def get_vfolderunreadfg():
	return sqmail.utils.getsetting("vfolderunreadfg", (0, 0, 0, 1.0))

def get_vfolderunreadbg():
	return sqmail.utils.getsetting("vfolderunreadbg", (1.0, 1.0, 1.0, 1.0))

def get_msglistfont():
	return sqmail.utils.getsetting("msglistfont", \
		"-schumacher-clean-medium-r-normal-*-14-*-*-*-c-*-iso646.1991-irv")

def get_unreadmsglistfont():
	return sqmail.utils.getsetting("unreadmsglistfont", \
		"-schumacher-clean-medium-r-normal-*-14-*-*-*-c-*-iso646.1991-irv")

def get_pendingmsglistfont():
	return sqmail.utils.getsetting("pendingmsglistfont", \
		"-schumacher-clean-medium-r-normal-*-14-*-*-*-c-*-iso646.1991-irv")

# Miscellaneous

def get_quoteprefix():
	return sqmail.utils.getsetting("quoteprefix", \
		"> ")

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
	
instance = None
class SQmaiLPreferences:
	def __init__(self, reader):
		global instance

		if instance:
			return
		instance = self

		self.reader = reader
		preferenceswin = reader.readglade("preferenceswin", self)
		self.widget = sqmail.gui.utils.WidgetStore(preferenceswin)

		# Transport

		p = get_incomingprotocol()
		if (p == "IMAP"):
			self.widget.imapbutton.set_active(1)
		elif (p == "POP"):
			self.widget.popbutton.set_active(1)
		elif (p == "Spool"):
			self.widget.spoolbutton.set_active(1)

		self.widget.incomingserver.set_text(get_incomingserver())

		self.widget.incomingport.set_text(str(get_incomingport()))

		self.widget.incomingusername.set_text(get_incomingusername())

		self.widget.incomingpassword.set_text(get_incomingpassword())

		self.widget.incomingpath.set_text(get_incomingpath())

		self.widget.deleteremotebutton.set_active(get_deleteremote())

		self.widget.fromaddress.set_text(get_fromaddress())

		self.widget.outgoingserver.set_text(get_outgoingserver())

		self.widget.outgoingport.set_text(str(get_outgoingport()))

		self.widget.smtpdebug.set_active(get_smtpdebuglevel())

		# Appearances

		self.widget.textmessagefont.set_font_name(get_textmessagefont())

		self.widget.composefont.set_font_name(get_composefont())

		self.widget.vfolderfont.set_font_name(get_vfolderfont())
		apply(self.widget.vfolderfg.set_i8, get_vfolderfg())
		apply(self.widget.vfolderbg.set_i8, get_vfolderbg())

		self.widget.vfolderunreadfont.set_font_name(get_vfolderunreadfont())
		apply(self.widget.vfolderunreadfg.set_i8, get_vfolderunreadfg())
		apply(self.widget.vfolderunreadbg.set_i8, get_vfolderunreadbg())

		self.widget.msglistfont.set_font_name(get_msglistfont())

		self.widget.unreadmsglistfont.set_font_name(get_unreadmsglistfont())

		self.widget.pendingmsglistfont.set_font_name(get_pendingmsglistfont())
		
		# Miscellaneous

		self.widget.quoteprefix.set_text(get_quoteprefix())
	
	# Signal handlers.

	def on_deactivate(self, obj):
		global instance
		self.widget.preferenceswin.destroy()
		instance = None

	def on_apply(self, obj, a):
		if (a == 1):
			return
		
		# Transport

		if (self.widget.imapbutton.get_active()):
			p = "IMAP"
		elif (self.widget.popbutton.get_active()):
			p = "POP"
		elif (self.widget.spoolbutton.get_active()):
			p = "Spool"
		sqmail.utils.setsetting("incomingprotocol", p)

		sqmail.utils.setsetting("incomingserver", \
			self.widget.incomingserver.get_text())

		sqmail.utils.setsetting("incomingport", \
			int(self.widget.incomingport.get_text()))

		sqmail.utils.setsetting("incomingusername", \
			self.widget.incomingusername.get_text())

		sqmail.utils.setsetting("incomingpassword", \
			self.widget.incomingpassword.get_text())

		sqmail.utils.setsetting("incomingpath", \
			self.widget.incomingpath.get_text())

		sqmail.utils.setsetting("deleteremote", \
			self.widget.deleteremotebutton.get_active())

		sqmail.utils.setsetting("fromaddress", \
			self.widget.fromaddress.get_text())

		sqmail.utils.setsetting("outgoingserver", \
			self.widget.outgoingserver.get_text())

		sqmail.utils.setsetting("outgoingport", \
			int(self.widget.outgoingport.get_text()))

		sqmail.utils.setsetting("smtpdebuglevel", \
			self.widget.smtpdebug.get_active())

		# Appearances
	
		sqmail.utils.setsetting("textmessagefont", \
			self.widget.textmessagefont.get_font_name())

		sqmail.utils.setsetting("composefont", \
			self.widget.composefont.get_font_name())

		sqmail.utils.setsetting("vfolderfont", \
			self.widget.vfolderfont.get_font_name())
		sqmail.utils.setsetting("vfolderfg", \
			self.widget.vfolderfg.get_i8())
		sqmail.utils.setsetting("vfolderbg", \
			self.widget.vfolderbg.get_i8())

		sqmail.utils.setsetting("vfolderunreadfont", \
			self.widget.vfolderunreadfont.get_font_name())
		sqmail.utils.setsetting("vfolderunreadfg", \
			self.widget.vfolderunreadfg.get_i8())
		sqmail.utils.setsetting("vfolderunreadbg", \
			self.widget.vfolderunreadbg.get_i8())

		sqmail.utils.setsetting("msglistfont", \
			self.widget.msglistfont.get_font_name())

		sqmail.utils.setsetting("unreadmsglistfont", \
			self.widget.unreadmsglistfont.get_font_name())

		sqmail.utils.setsetting("pendingmsglistfont", \
			self.widget.pendingmsglistfont.get_font_name())

	
		# Miscellaneous

		sqmail.utils.setsetting("quoteprefix", \
			self.widget.quoteprefix.get_text())

	def on_changed(self, *args):
		self.widget.preferenceswin.set_modified(1)

# Revision History
# $Log: preferences.py,v $
# Revision 1.2  2001/01/18 19:27:07  dtrg
# Now saves the colours for read and unread vfolders.
#
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


