# Fetches mail from a POP server.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/popfetcher.py,v $
# $State: Exp $

import os
import os.path
import mailbox
import poplib
import string
import sqmail.message
import sqmail.gui.preferences
import sqmail.gui.fetcher

class POPFetcher (sqmail.gui.fetcher.Fetcher):
	def __init__(self, reader):
		sqmail.gui.fetcher.Fetcher.__init__(self, reader, "POP Read")

		server = sqmail.gui.preferences.get_incomingserver()
		port = sqmail.gui.preferences.get_incomingport()
		if not port:
			port = 110
		username = sqmail.gui.preferences.get_incomingusername()
		password = sqmail.gui.preferences.get_incomingpassword()

		self.msg("Connecting to POP server")
		pop = poplib.POP3(server, port)
		self.msg(pop.getwelcome())
		
		self.msg("Authenticating")
		pop.user(username)
		pop.pass_(password)

		messages, total = pop.stat()
		if not messages:
			self.msg("No messages to fetch. Aborting.")
			self.do_abort()
			return

		self.msg(str(messages)+" message(s) to fetch for a total of "+\
			str(total)+" bytes")

		bytesread = 0
		for count in xrange(messages):
			self.progress(bytesread, total)
			smsg = ""
			i = pop.retr(count+1)
			bytesread = bytesread + i[2]
			for i in i[1]:
				smsg = smsg + i + "\n"

			msg = sqmail.message.Message()
			msg.loadfromstring(smsg)
			msg.savealltodatabase()
		
			if sqmail.gui.preferences.get_deleteremote():
				pop.dele(count+1)

			if self.abort:
				self.msg("Aborted!")

		self.progress(bytesread, total)
		self.msg(str(count+1)+" message(s) read. Disconnecting.")
		pop.quit()
		if not self.abort:
			self.do_abort()
			
	def on_abort(self, obj):
		return self.do_abort()

# Revision History
# $Log: popfetcher.py,v $
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


