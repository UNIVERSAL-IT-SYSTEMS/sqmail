# Fetches mail from a spool file.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/spoolfetcher.py,v $
# $State: Exp $

import os
import os.path
import mailbox
import sqmail.message
import sqmail.gui.preferences
import sqmail.gui.fetcher

class SpoolFetcher (sqmail.gui.fetcher.Fetcher):
	def __init__(self, reader):
		sqmail.gui.fetcher.Fetcher.__init__(self, reader, "Spool Read")

		filename = sqmail.gui.preferences.get_incomingpath()
		self.msg("Using spool file "+filename)
		self.msg("Locking spool file")
		rv = os.system("mail-lock --retry 1")
		if rv:
			self.msg("Failed to lock spool file, aborting")
			self.do_abort()
			return

		self.msg("Opening spool file")

		fp = open(filename, "r+")
		fp.seek(0, 2)
		len = fp.tell()
		fp.seek(0, 0)

		if (len == 0):
			self.msg("Spool file empty. Aborting.")
			fp.close()
			os.system("mail-unlock")
			self.do_abort()
			return

		mbox = mailbox.UnixMailbox(fp)
		count = 0
		
		self.msg("Reading messages")
		while 1:
			self.progress(fp.tell(), len)
			msg = sqmail.message.Message()
			mboxmsg = mbox.next()
			if not mboxmsg:
				break

			msg.loadfrommessage(mboxmsg)
			msg.savealltodatabase()
			count = count + 1

			if self.abort:
				self.msg("Aborted!")
				self.msg("(Duplicate messages remain in spool file.)")
				break

		self.msg(str(count)+" message(s) read")

		if not self.abort:
			if sqmail.gui.preferences.get_deleteremote():
				self.msg("All messages read; truncating spool file")
				fp.truncate(0)
			else:
				self.msg("All messages read. Leaving mail in spool file. " \
					"(Fetching again will result in duplicate messages "\
					"in your database.)")

		self.msg("Closing and unlocking spool file")
		fp.close()
		os.system("mail-unlock")
		if not self.abort:
			self.do_abort()

	def on_abort(self, obj):
		return self.do_abort()

# Revision History
# $Log: spoolfetcher.py,v $
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


