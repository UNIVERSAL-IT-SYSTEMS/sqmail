# Views images.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/imageviewer.py,v $
# $State: Exp $

import os
import sys
import time
import gtk
import gnome.ui
import libglade
import quopri
import tempfile
import cStringIO
import sqmail.utils
import sqmail.gui.viewer
import sqmail.preferences

displayable = ("image/gif", "image/jpeg", "image/png", "image")

class ImageViewer (sqmail.gui.viewer.Viewer):
	def __init__(self, reader, a):
		sqmail.gui.viewer.Viewer.__init__(self, reader, a, "imagemessage")
		# Write out the attachment to a temporary file.
		msgname = tempfile.mktemp()
		msgfp = open(msgname, "w")
		msgfp.write(self.attachment[2])
		msgfp.close()
		# Load it into the viewer.
		self.viewer_widget.messagepixmap.load_file(msgname)
		# Nuke the temporary file.
		os.unlink(msgname)
	
	def on_save(self, obj):
		sqmail.gui.viewer.Viewer.on_save(self, obj)
	
	def on_launch(self, obj):
		sqmail.gui.viewer.Viewer.on_launch(self, obj)

# Revision History
# $Log: imageviewer.py,v $
# Revision 1.1  2001/05/23 10:08:31  dtrg
# Added the image viewer; now gifs, jpegs and pngs will be viewed inline.
#
