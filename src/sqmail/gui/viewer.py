# Viewer superclass. Provides generic services for displaying attachments.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/viewer.py,v $
# $State: Exp $

import sys
import time
import gtk
import gnome.ui
import libglade
import sqmail.gui.utils

class Viewer:
	def __init__(self, r, a, w):
		self.attachment = a
		self.reader = r
		self.page = gtk.GtkFrame(None)
		xml = self.reader.readglade("messageframe", self)
		self.frame_widget = sqmail.gui.utils.WidgetStore(xml)
		self.frame_widget.frame.hide()

		self.frame_widget.frame.reparent(self.page)
		self.frame_widget.messageframe.destroy()

		xml = self.reader.readglade(w, self)
		self.viewer_widget = sqmail.gui.utils.WidgetStore(xml)
		self.viewer_widget.frame.hide()

		self.viewer_widget.frame.reparent(self.frame_widget.container)
		self.viewer_widget[w].destroy()
		self.page.show()
		self.tab = gtk.GtkLabel(self.attachment[0])

		self.frame_widget.attachmentinfo.set_text(self.getdescription())

		self.viewer_widget.frame.show()
		self.frame_widget.frame.show()

	def destroy(self):
		self.frame_widget.frame.hide()

	def getpage(self):
		return self.page
	
	def gettab(self):
		return self.tab
	
	def getdescription(self):
		return "Type: %s  Named: %s\n%d bytes long" % \
			(self.attachment[1], self.attachment[0], \
			len(self.attachment[2]))
	
	def on_save(self, obj):
		sqmail.gui.utils.FileSelector("Save Attachment...", \
			self.attachment[0], self.save_attachment)
	
	def save_attachment(self, name):
		fp = open(name, "w")
		fp.write(self.attachment[2])
		fp.close()
	
	def on_launch(self, obj):
		print "Launching attachment"

# Revision History
# $Log: viewer.py,v $
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
# Revision 1.2  2001/01/11 20:31:54  dtrg
# Small performance enhancement to reduce flicker when changing messages.
#
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


