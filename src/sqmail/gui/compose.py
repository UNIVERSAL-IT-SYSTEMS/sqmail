# Handles the compose window.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/compose.py,v $
# $State: Exp $

import os.path
import string
import sys
import MimeWriter
import base64
import quopri
import cStringIO
import gtk
import smtplib
import time
import rfc822
import re
import gnome.mime
import sqmail.utils
import sqmail.message
import sqmail.gui.reader
import sqmail.gui.utils
import sqmail.gui.textviewer

# All hi-bit chars.
iso_char = re.compile('[\177-\377]')

class SQmaiLCompose:
	def __init__(self, reader, message, addrlist):
		self.reader = reader
		self.message = message
		composewin = reader.readglade("composewin", self)
		self.widget = sqmail.gui.utils.WidgetStore(composewin)

		self.font = gtk.load_font(sqmail.gui.preferences.get_composefont())
		# Ensure the text box is 80 columns wide.
		width = gtk.gdk_char_width(self.font, "m")*82

		# Set up the header fields.

		if addrlist:
			self.widget.tofield.set_text(sqmail.gui.utils.render_addrlist(addrlist))
		self.widget.fromfield.set_text(sqmail.gui.preferences.get_fromaddress())
		if message:
			i = self.message.getsubject()
			if (i[:3] == "Re:") or (i[:3] == "re:"):
				self.widget.subjectfield.set_text(i)
			else:
				self.widget.subjectfield.set_text("Re: "+i)

		# Set up the sign button.

		self.signaturespopup = gtk.GtkMenu()
		signatures = os.listdir(os.path.expanduser("~"))
		signatures.sort()
		for i in signatures:
			if (i[0:10] == ".signature"):
				w = gtk.GtkMenuItem(i)
				w.show()
				w.connect("activate", sqmail.gui.utils.Callback(self)["on_sign_with"])
				w.set_data("file", i)
				self.signaturespopup.append(w)
				
		# Set up the quote button.

		if message:
			self.quotepopup = gtk.GtkMenu()
			attachments = message.mimeflatten()
			for i in attachments:
				if (i[1] in sqmail.gui.textviewer.displayable):
					w = gtk.GtkMenuItem(i[1]+": "+i[0])
					w.show()
					w.connect("activate", sqmail.gui.utils.Callback(self)["on_quote_with"])
					w.set_data("msg", i[2])
					self.quotepopup.append(w)
		else:
			self.widget.quotebutton.set_sensitive(0)

		self.widget.textbox.freeze()
		self.widget.textbox.set_usize(width, 0)

		# These two lines set the font. *shrug*
		self.widget.textbox.insert(self.font, None, None, "\n")
		self.widget.textbox.delete_text(0, 1)

		# We want word wrapping.
		self.widget.textbox.set_word_wrap(1)

		self.widget.textbox.thaw()

	def makemessage(self):
		out = cStringIO.StringIO()
		mw = MimeWriter.MimeWriter(out)

		# Write standard header.
		mw.addheader("X-Mailer", "SQmaiL (http://sqmail.sourceforge.net)")
		mw.addheader("From", self.widget.fromfield.get_text())
		mw.addheader("To", self.widget.tofield.get_text())
		mw.addheader("Subject", self.widget.subjectfield.get_text())
		mw.addheader("MIME-Version", "1.0")

		# If we were replying to something, write the in-reply-to
		# header.
		if (self.message):
			msg = self.message.rfc822()
			msg = msg.getheader("Message-ID")
			if msg:
				mw.addheader("In-Reply-To", msg)

		# Split the To box into a list of addresses.
		atfp = cStringIO.StringIO(self.widget.extrasfield.get_chars(0, -1))
		while 1:
			i = atfp.readline()
			if not i:
				break
			i = string.strip(i)
			header, value = string.split(i, ": ", 1)
			mw.addheader(header, value)

		# Do we need to make the body into quoted-printable?
		body = self.widget.textbox.get_chars(0, -1)
		if iso_char.search(body):
			fp = cStringIO.StringIO(body)
			atfp = cStringIO.StringIO()
			quopri.encode(fp, atfp, 0)
			body = atfp.getvalue()
			bodyencoding = "quoted-printable"
		else:
			bodyencoding = "7bit"

		# Do we have attachments to worry about?
		if self.widget.attachmentlist.rows:
			# Yes; we need to send a multipart message.
			fp = mw.startmultipartbody("mixed")
			submw = mw.nextpart()
			submw.addheader("Content-Disposition", "inline; filename=\"body text\"")
			submw.addheader("Content-Transfer-Encoding", bodyencoding)
			fp = submw.startbody("text/plain")
			fp.write(body)
			for i in xrange(self.widget.attachmentlist.rows):
				type = self.widget.attachmentlist.get_text(i, 0)
				name = self.widget.attachmentlist.get_text(i, 2)
				submw = mw.nextpart()
				submw.addheader("Content-Transfer-Encoding", "base64")
				submw.addheader("Content-Disposition", "attachment; filename=\""+name+"\"")
				fp = submw.startbody(type)
				atfp = cStringIO.StringIO(self.widget.attachmentlist.get_row_data(i))
				base64.encode(atfp, fp)
			mw.lastpart()
		else:
			# No; a single part message will do.
			mw.addheader("Content-Transfer-Encoding", bodyencoding)
			fp = mw.startbody("text/plain")
			fp.write(body)
		return out.getvalue()

	def on_send(self, obj):
		smtp = smtplib.SMTP(sqmail.gui.preferences.get_outgoingserver(), \
			sqmail.gui.preferences.get_outgoingport())
		smtp.set_debuglevel(sqmail.gui.preferences.get_smtpdebuglevel())
		fromaddr = self.widget.fromfield.get_text()
		toaddr = []
		for i in rfc822.AddressList(self.widget.tofield.get_text()).addresslist:
			toaddr.append(i[1])
		msgstring = self.makemessage()
		smtp.sendmail(fromaddr, toaddr, msgstring)
		smtp.quit()
		# If we got this far, the message went out successfully.
		# Incorporate the message into the database (for the outbox).
		msg = sqmail.message.Message()
		msg.loadfromstring(msgstring)
		msg.date = time.time()
		msg.readstatus = "Sent"
		msg.savealltodatabase()
		# We can destroy the send window.
		self.widget.composewin.destroy()
	
	def on_attach(self, obj):
		sqmail.gui.utils.FileSelector("Attach File...", "", \
			SQmaiLCompose.on_attach_file, self)

	def on_attach_file(self, name):
		file = open(name)
		# Determine the length of the file.
		file.seek(0, 2)
		l = file.tell()
		file.seek(0, 0)
		# Read the entire file into memory.
		file = file.read(l)
		# Now add it to the icon list.
		type = gnome.mime.type_of_file(name)
		name = os.path.basename(name)
		pos = self.widget.attachmentlist.append([type, str(len(file)), name])
		self.widget.attachmentlist.set_row_data(pos, file)
	
	def on_delete_attachment(self, name):
		s = self.widget.attachmentlist.selection
		if (len(s) != 1):
			return
		self.widget.attachmentlist.remove(s[0])
	
	def on_sign(self, obj):
		self.signaturespopup.popup(None, None, None, 1, 0)

	def on_sign_with(self, obj):
		file = os.path.expanduser("~/"+obj.get_data("file"))
		if os.access(file, os.X_OK):
			# The signature file is executable, so run it to get
			# the result.
			fp = os.popen(file)
		else:
			# Normal file.
			fp = open(file)
		self.widget.textbox.freeze()
		ipoint = self.widget.textbox.get_point()
		self.widget.textbox.set_point(self.widget.textbox.get_length())
		self.widget.textbox.insert(self.font, None, None, "\n-- \n")
		while 1:
			i = fp.readline()
			if not i:
				break
			self.widget.textbox.insert(self.font, None, None, i)
		self.widget.textbox.set_point(ipoint)
		self.widget.textbox.thaw()

	def on_quote(self, obj):
		self.quotepopup.popup(None, None, None, 1, 0)
	
	def on_quote_with(self, obj):
		fp = cStringIO.StringIO(obj.get_data("msg"))
		self.widget.textbox.freeze()
		prefix = sqmail.gui.preferences.get_quoteprefix()
		while 1:
			i = fp.readline()
			if not i:
				break
			self.widget.textbox.insert(self.font, None, None, prefix)
			self.widget.textbox.insert(self.font, None, None, i)
		self.widget.textbox.thaw()

# Revision History
# $Log: compose.py,v $
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


