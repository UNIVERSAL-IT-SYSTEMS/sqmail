# Views the raw message information.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/headerspane.py,v $
# $State: Exp $

import sys
import time
import gtk
import gnome.ui
import libglade
import quopri
import cStringIO
import sqmail.utils
import sqmail.gui.viewer
import sqmail.preferences

class HeadersViewer (sqmail.gui.viewer.Viewer):
	def __init__(self, reader, msg):
		self.message = msg
		msg = self.message.getheaders()+"\n\n"+\
			self.message.getbody()
		sqmail.gui.viewer.Viewer.__init__(self, reader, ["*", "", msg], "headerspane")
		font = gtk.load_font(sqmail.preferences.get_textmessagefont())
		# Ensure the text box is 80 columns wide.
		width = gtk.gdk_char_width(font, "m")*82
		# The text box is guaranteed to be empty.
		self.viewer_widget.messagetext.freeze()
		self.viewer_widget.messagetext.set_usize(width, 0)
		self.viewer_widget.messagetext.insert(font, None, None, msg)
		self.viewer_widget.messagetext.thaw()
	
	def on_save(self, obj):
		sqmail.gui.viewer.Viewer.on_save(self, obj)
	
	def getdescription(self):
		return "Entire message without MIME decoding"
	
# Revision History
# $Log: headerspane.py,v $
# Revision 1.3  2001/04/19 18:21:02  dtrg
# Added the message contents to the fake attachment structure, so that the
# Viewer superclass can successfully save/launch the entire message.
#
# Revision 1.2  2001/02/20 17:22:36  dtrg
# Moved the bulk of the preference system out of the gui directory, where it
# doesn't belong. sqmail.gui.preferences still exists but it just contains
# the preferences editor. sqmail.preferences now contains the access
# functions and load/save functions.
#
# Revision 1.1  2001/01/22 18:31:55  dtrg
# Assorted changes, comprising:
#
# * Added a new pane to the notebook display containing the entire, un
# MIMEified message. I was originally going to display just the headers and
# then optionally the body when the user pressed a button, but it seems to
# be decently fast without it.
# * The first half of the Spamcop support. Now, pressing the Spam button
# causes a compose window to appear all ready to send. The second half, that
# will deal automatically with the automated replies from Spamcop, has yet
# to be done.
# * Yet another rehash of the vfolder colour code. Still doesn't work.
#
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


