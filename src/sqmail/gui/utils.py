# Generic utilities.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/utils.py,v $
# $State: Exp $

import sys
import time
import gtk
import gnome.ui
import libglade
import types
import sqmail.gui.reader

def render_time(t):
	return time.asctime(time.gmtime(t))

def render_address(a):
	s = ""
	if ((not a[0]) or (a[0] == a[1])):
		s = s + a[1]
	else:
		s = s + a[0] + " <" + a[1] + ">"
	return s

def render_addrlist(l):
	s = ""
	for i in l:
		s = s + render_address(i) + ", "
	return s[:-2]


def update_clist(clist, row, values):
	clist.freeze()
	for i in xrange(len(values)):
		clist.set_text(row, i, values[i])
	clist.thaw()

def update_ctree(ctree, node, values):
	ctree.freeze()
	for i in xrange(len(values)):
		ctree.node_set_text(node, i, values[i])
	ctree.thaw()

class FileSelector:
	def __init__(self, name, file, method, dest):
		self.method = method
		self.dest = dest
		self.fsel = gtk.GtkFileSelection(name)
		self.fsel.set_filename(file)
		callbacks = Callback(self)
		self.fsel.cancel_button.connect("clicked", callbacks["on_cancel"])
		self.fsel.ok_button.connect("clicked", callbacks["on_select"])
		self.fsel.show()
	
	def on_cancel(self, obj):
		self.fsel.destroy()

	def on_select(self, obj):
		filename = self.fsel.get_filename()
		self.fsel.destroy()
		if self.dest:
			try:
				self.method(self.dest, filename)
			except TypeError:
				print "Exception while calling", self.method.__name__, "on", self.dest
				raise
		else:
			self.method(filename)

class WidgetStore:
	def __init__(self, tree):
		self._tree = tree

	def __getattr__(self, attr):
		w = self._tree.get_widget(attr)
		if not w:
			raise AttributeError("Widget "+attr+" not found")
		self.__dict__[attr] = w
		return w
	__getitem__ = __getattr__
	
class _callback:
	def __init__(self, dest, method):
		self.dest = dest
		self.method = method
	
	def __call__(self, *args):
		try:
			return apply(self.method, (self.dest,) + args)
		except TypeError:
			print "Exception while calling", self.method.__name__, "on", self.dest
			print "Args:", args
			raise

class Callback:
	def __init__(self, dest):
		self.dest = dest
		self.dict = {}
		for i in self.dest.__class__.__bases__:
			self.dict.update(i.__dict__)
		self.dict.update(self.dest.__class__.__dict__)

	def items(self):
		l = []
		for key, value in self.dest.__class__.__dict__.items():
			if (type(value) == types.FunctionType):
				l.append((key, _callback(self.dest, value)))
		return l
	
	def __getitem__(self, name):
		return _callback(self.dest, self.dict[name])

def errorbox(msg):
	i = gnome.ui.GnomeErrorDialog(msg, sqmail.gui.reader.instance.widget.mainwin)
	i.run_and_close()
	i.destroy()

def okbox(msg):
	i = gnome.ui.GnomeOkDialog(msg, sqmail.gui.reader.instance.widget.mainwin)
	i.run_and_close()
	i.destroy()

def okcancelbox(msg):
	i = gnome.ui.GnomeOkCancelDialog(msg, sqmail.gui.reader.instance.widget.mainwin)
	j = i.run_and_close()
	i.destroy()
	return j
	
# Revision History
# $Log: utils.py,v $
# Revision 1.2  2001/02/15 19:34:16  dtrg
# Many changes. Bulletproofed the send box, so it should now give you
# (reasonably) user-friendly messages when something goes wrong; rescan a
# vfolder when you leave it, so the vfolder list is kept up-to-date (and in
# the background, too); added `unimplemented' messages to a lot of
# unimplemented buttons; some general tidying.
#
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


		
