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
import sqmail.gui.preferences

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
		self.htmlwidget.source(body)
		self.htmlwidget.thaw()
	
	def on_save(self, obj):
		sqmail.gui.viewer.Viewer.on_save(self, obj)
	
	def on_launch(self, obj):
		sqmail.gui.viewer.Viewer.on_launch(self, obj)

# Revision History
# $Log: htmlviewer.py,v $
# Revision 1.1  2001/01/11 20:07:23  dtrg
# Added preliminary HTML rendering support (ten minutes work!).
#

