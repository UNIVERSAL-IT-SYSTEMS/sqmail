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
import popen2
import string

def render_time(t):
	return time.asctime(time.gmtime(t))

def render_address(a):
	if (type(a) == types.StringType):
		return a
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

# Browses for a file.

class FileSelector:
	def __init__(self, name, file, method, user=None):
		self.method = method
		self.user = user
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
		if self.user:
			self.method(filename, self.user)
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

# Pop up assorted message boxes, and block until the user OKs them.

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
	
# Applies an image, in face format, to a container widget.

def set_face(w, f):
	w.set_data("face", f)
	if not sqmail.preferences.get_usexfaces():
		return

	decoder = sqmail.preferences.get_xfacedecoder()
	pipefp = popen2.popen2(decoder)
	pipefp[1].write(f)
	pipefp[1].close()
	pixdata = sqmail.utils.load_xpm(pipefp[0])
	if not pixdata:
		sqmail.gui.utils.errorbox("I was unable to decode an X-Face string. See the error message on the console.")
		return
	set_xpm(w, pixdata)


# Applies an XPM image to a container widget.

def set_xpm(w, xpm):
	c = w.children()
	if c:
		c[0].destroy()
	if not xpm:
		return

	pixmap, mask = gtk.create_pixmap_from_xpm_d(w, None, xpm)
	pixmap = gtk.GtkPixmap(pixmap, None)
	w.add(pixmap)
	pixmap.show()
			
# Revision History
# $Log: utils.py,v $
# Revision 1.7  2001/03/12 14:28:38  dtrg
# Added the ability to disable X-Faces completely, as they weren't working
# for some people (even with the code to detect if the decoding was
# failing). Still needs a bit of cosmetic work --- it would be nice to grey
# out preferences GUI elements that aren't valid when they're disabled ---
# but it works.
#
# Revision 1.6  2001/03/09 20:36:19  dtrg
# First draft picons support.
#
# Revision 1.5  2001/03/07 12:21:21  dtrg
# Now tests for the X-Face encoder and decoder commands failing, and no
# longer seg faults.
#
# Revision 1.4  2001/03/05 20:44:41  dtrg
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
# Revision 1.3  2001/02/20 17:22:36  dtrg
# Moved the bulk of the preference system out of the gui directory, where it
# doesn't belong. sqmail.gui.preferences still exists but it just contains
# the preferences editor. sqmail.preferences now contains the access
# functions and load/save functions.
#
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


		
