# Viewer class for generic binary attachments.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/binaryviewer.py,v $
# $State: Exp $

import sys
import time
import gtk
import gnome.ui
import libglade
import sqmail.gui.viewer

class BinaryViewer (sqmail.gui.viewer.Viewer):
	def __init__(self, reader, a):
		sqmail.gui.viewer.Viewer.__init__(self, reader, a, "binarymessage")

	def on_save(self, obj):
		sqmail.gui.viewer.Viewer.on_save(self, obj)
	
	def on_launch(self, obj):
		sqmail.gui.viewer.Viewer.on_launch(self, obj)

# Revision History
# $Log: binaryviewer.py,v $
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


