# Views plain text messages.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/textviewer.py,v $
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

displayable = ("text/quoted-printable", "text/plain", "text/english", \
	"text/x-vcard", "text/python", "text/patch", "application/python", \
	"application/patch", "text")

class TextViewer (sqmail.gui.viewer.Viewer):
	def __init__(self, reader, a):
		sqmail.gui.viewer.Viewer.__init__(self, reader, a, "textmessage")
		font = gtk.load_font(sqmail.preferences.get_textmessagefont())
		# Ensure the text box is 80 columns wide.
		width = gtk.gdk_char_width(font, "m")*82
		# The text box is guaranteed to be empty.
		self.viewer_widget.messagetext.freeze()
		self.viewer_widget.messagetext.set_usize(width, 0)
		if (self.attachment[1] == "text/quoted-printable"):
			infp = cStringIO.StringIO(self.attachment[2])
			outfp = cStringIO.StringIO()
			quopri.decode(infp, outfp)
			body = outfp.getvalue()
		else:
			body = self.attachment[2]
		self.viewer_widget.messagetext.insert(font, None, None, body)
		self.viewer_widget.messagetext.thaw()
	
	def on_save(self, obj):
		sqmail.gui.viewer.Viewer.on_save(self, obj)
	
	def on_launch(self, obj):
		sqmail.gui.viewer.Viewer.on_launch(self, obj)

# Revision History
# $Log: textviewer.py,v $
# Revision 1.3  2001/05/23 10:11:53  dtrg
# Added a few more MIME types to be rendered as text.
#
# Revision 1.2  2001/02/20 17:22:36  dtrg
# Moved the bulk of the preference system out of the gui directory, where it
# doesn't belong. sqmail.gui.preferences still exists but it just contains
# the preferences editor. sqmail.preferences now contains the access
# functions and load/save functions.
#
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


