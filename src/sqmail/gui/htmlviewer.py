# Views HTML messages.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/htmlviewer.py,v $
# $State: Exp $

import sys
import time
import gtk
import gnome.ui
import gnome.xmhtml
import libglade
import quopri
import cStringIO
import sqmail.utils
import sqmail.gui.viewer
import sqmail.preferences

displayable = ("text/html",)

class HTMLViewer (sqmail.gui.viewer.Viewer):
	def __init__(self, reader, a):
		sqmail.gui.viewer.Viewer.__init__(self, reader, a, "htmlmessage")
		# Glade doesn't do the GtkXmHTML widget yet. So we need to add
		# it manually.
		self.htmlwidget = gnome.xmhtml.GtkXmHTML()
		self.viewer_widget.frame.add(self.htmlwidget)
		self.htmlwidget.show()
		self.htmlwidget.freeze()
		if (self.attachment[1] == "text/quoted-printable"):
			infp = cStringIO.StringIO(self.attachment[2])
			outfp = cStringIO.StringIO()
			quopri.decode(infp, outfp)
			body = outfp.getvalue()
		else:
			body = self.attachment[2]
		self.htmlwidget.set_allow_images(1)
		self.htmlwidget.source(body)
		self.htmlwidget.thaw()
	
	def on_save(self, obj):
		sqmail.gui.viewer.Viewer.on_save(self, obj)
	
	def on_launch(self, obj):
		sqmail.gui.viewer.Viewer.on_launch(self, obj)

# Revision History
# $Log: htmlviewer.py,v $
# Revision 1.3  2001/02/20 17:22:36  dtrg
# Moved the bulk of the preference system out of the gui directory, where it
# doesn't belong. sqmail.gui.preferences still exists but it just contains
# the preferences editor. sqmail.preferences now contains the access
# functions and load/save functions.
#
# Revision 1.2  2001/01/22 18:31:55  dtrg
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
# Revision 1.1  2001/01/11 20:07:23  dtrg
# Added preliminary HTML rendering support (ten minutes work!).
#

