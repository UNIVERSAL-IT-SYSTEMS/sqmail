# Fetcher superclass. Provides generic services to implement a mail fetcher.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/fetcher.py,v $
# $State: Exp $

import os
import gtk
import sqmail.gui.utils

class Fetcher:
	def __init__(self, reader, title):
		self.reader = reader
		win = reader.readglade("progresswin", self)
		self.widget = sqmail.gui.utils.WidgetStore(win)
		self.widget.closebutton.set_sensitive(0)
		self.abort = 0

		self.widget.progresswin.set_title(title)

	def msg(self, msg):
		t = self.widget.textbox
		t.freeze()
		t.set_point(t.get_length())
		t.insert(None, None, None, msg)
		t.insert(None, None, None, "\n")
		t.set_point(t.get_length())
		t.thaw()
		self.wait()
	
	def progress(self, a, b):
		if (a > b):
			a = b
		self.widget.progressbar.set_percentage(float(a)/float(b))
		self.wait()
	
	def wait(self):
		while gtk.events_pending():
			gtk.mainiteration(0)

	def do_abort(self):
		if self.abort:
			self.widget.progresswin.destroy()
			return 0
		else:
			self.abort = 1
			self.widget.cancelbutton.set_sensitive(0)
			self.widget.closebutton.set_sensitive(1)
			return 1
# Revision History
# $Log: fetcher.py,v $
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#

		
