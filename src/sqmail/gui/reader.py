# The mail reader top-level program.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/reader.py,v $
# $State: Exp $

import os
import sys
import time
import gtk
import gnome.ui
import gnome.url
import libglade
import urllib
import tempfile
import string
import sqmail.vfolder
import sqmail.message
import sqmail.preferences
import sqmail.gui.textviewer
import sqmail.gui.binaryviewer
import sqmail.gui.htmlviewer
import sqmail.gui.headerspane
import sqmail.gui.compose
import sqmail.gui.preferences
import sqmail.gui.purges
import sqmail.gui.utils
import sqmail.gui.spoolfetcher
import sqmail.gui.popfetcher
import sqmail.gui.aliases

# --- The mail reader itself --------------------------------------------------

instance = None
class SQmaiLReader:
	gladefilename = "sqmail.glade"

	def __init__(self):
		global instance
		if instance:
			raise RuntimeError("You can only create one SQmaiLReader instance at a time!")
		instance = self

		# Create the main window and the widget store.

		self.mainwindow = self.readglade("mainwin")
		self.widget = sqmail.gui.utils.WidgetStore(self.mainwindow)
		
		# Initialise instance variables.

		self.messagelist = []
		self.messagepages = []
		self.counting = None

		# Load the pixmaps.

		self.deleted_pixmap = gtk.GtkPixmap(self.widget.messagelist.get_window(), \
			"images/deleted-message.xpm")
		self.unread_pixmap = gtk.GtkPixmap(self.widget.messagelist.get_window(), \
			"images/unread-message.xpm")
		self.sent_pixmap = gtk.GtkPixmap(self.widget.messagelist.get_window(), \
			"images/sent-message.xpm")

		# Enable DND on the vfolder list.

		self.widget.folderlist.set_reorderable(1)

		self.update_vfolderlist()
		gtk.mainloop()

	# Read in a Glade tree.
	
	def readglade(self, name, o=None):
		if not o:
			o = self
		obj = libglade.GladeXML(self.gladefilename, name)
		obj.set_data("owner", o)
		obj.signal_autoconnect(sqmail.gui.utils.Callback(o))
		return obj
	
	# Set the progress bar.

	def pushprogress(self):
		self.widget.applicationbar.push("")

	def setprogress(self, label, a, b):
		self.widget.applicationbar.set_status(label)
		self.widget.applicationbar.set_progress(float(a)/float(b))
		#while gtk.events_pending():
		#	gtk.mainiteration(0)

	def popprogress(self):
		self.widget.applicationbar.set_progress(0.0)
		self.widget.applicationbar.pop()

	# Return a description of a vfolder suitable for insertion into the
	# folder list.

	def describe_vfolder(self, vf):
		if not vf.getcounted():
			return (vf.name, "?", "?")
		unread = vf.getunread()
		if unread:
			unread = str(unread)
		else:
			unread = ""
		return (vf.name, unread, str(vf.getlen()))

	# Modify the passed style to reflect the status of the current folder.

	def style_vfolder(self, vf, style):
		if not vf.getcounted():
			fg = sqmail.preferences.get_vfolderpendingfg()
			bg = sqmail.preferences.get_vfolderpendingbg()
			font = sqmail.preferences.get_vfolderpendingfont()
		elif vf.getunread():
			fg = sqmail.preferences.get_vfolderunreadfg()
			bg = sqmail.preferences.get_vfolderunreadbg()
			font = sqmail.preferences.get_vfolderunreadfont()
		else:
			fg = sqmail.preferences.get_vfolderfg()
			bg = sqmail.preferences.get_vfolderbg()
			font = sqmail.preferences.get_vfolderfont()

		try:
			style.font = gtk.load_font(font)
		except RuntimeError:
			print "Couldn't load", font

		colormap = self.widget.folderlist.get_colormap()
		fg = colormap.alloc(fg[0], fg[1], fg[2])
		bg = colormap.alloc(bg[0], bg[1], bg[2])
		style.fg[gtk.STATE_NORMAL] = fg
		style.base[gtk.STATE_NORMAL] = bg
		return (fg, bg)

	# Ditto, for a message.

	def describe_message(self, msg):
		f = sqmail.gui.utils.render_address((msg.getrealfrom(), \
			msg.getfrom()))
		dayago = time.time() - 24.0*60.0*60.0
		d = msg.getdate()
		if (d < dayago):
			d = time.strftime("%Y/%m/%d", time.localtime(d))
		else:
			d = time.strftime("%H:%M", time.localtime(d))
		readstatus = msg.getreadstatus()
		if (readstatus == "Read"):
			readstatus = ""
		return (readstatus, f, msg.getsubject(), d)
		
	# Sets the icon for a message.

	def icon_message(self, i, msg):
		pixmap = None
		readstatus = msg.getreadstatus()
		if (readstatus == "Unread"):
			pixmap = self.unread_pixmap
		elif (readstatus == "Sent"):
			pixmap = self.sent_pixmap
		elif (readstatus == "Deleted"):
			pixmap = self.deleted_pixmap

		if pixmap:
			self.widget.messagelist.set_pixmap(i, 0, pixmap)

	# Return the current vfolder, or the vfolder corresponding to a
	# particular node.

	def vfolder(self, node=None):
		if not node:
			node = self.widget.folderlist.selection[0]
		return self.widget.folderlist.node_get_row_data(node)
		
	# Return the current message, or the vfolder corresponding to a
	# particular message number.

	def message(self, mn=None):
		if (mn == None):
			mn = self.widget.messagelist.selection
			if (mn == []):
				return None
			mn = mn[0]
		return self.widget.messagelist.get_row_data(mn)

	# Read in the vfolder list from the database.

	def update_vfolderlist(self):
		self.pushprogress()
		self.widget.folderlist.freeze()
		sel = self.widget.folderlist.selection
		if (len(sel) == 1):
			sel = self.widget.folderlist.node_get_row_data(sel[0]).name
		else:
			sel = None
		self.widget.folderlist.clear()
		l = sqmail.vfolder.get_folder_list()
		d = {}
		for i in xrange(len(l)):
			id = l[i]
			try:
				vf = sqmail.vfolder.VFolder(id=id)
			except KeyError:
				print "WARNING! VFolder id",id,"is in the folderlist but does not seem to exist."
				continue

			name = vf.getname()
			parent = vf.getparent()
			if parent:
				try:
					parent = d[parent]
				except KeyError:
					print "DANGER! Configuration inconsistency in vfolder", name+"."
					parent = None
			else:
				parent = None

			node = self.widget.folderlist.insert_node(parent, None, \
				["", "", ""], is_leaf=0, expanded=1)
			self.widget.folderlist.node_set_row_data(node, vf)
			self.update_vfolder(node)
			d[id] = node
			if (vf.name == sel):
				self.widget.folderlist.select(node)

			self.startcounting()
		self.widget.folderlist.thaw()
		self.popprogress()
		
	# Start background counting the vfolders.

	def startcounting(self):
		if not self.counting:
			self.counting = gtk.idle_add_priority(200, \
				sqmail.gui.utils._callback(self, self.count_vfolder))

	# ...and stop it.

	def stopcounting(self):
		if self.counting:
			gtk.idle_remove(self.counting)
			self.counting = None

	# Callback on idle that looks for an uncounted vfolder and counts it.
	# If there wasn't one, the callback gets removed.

	def count_vfolder(self, n):
		for i in xrange(self.widget.folderlist.rows):
			node = self.widget.folderlist.node_nth(i)
			vf = self.vfolder(node)
			if not vf.getcounted():
				vf.scan()
				self.update_vfolder(node)
				return 1
		self.counting = None
		return 0

	# Update one individual vfolder.

	def update_vfolder(self, node):
		self.pushprogress()
		self.widget.folderlist.freeze()
		vf = self.vfolder(node)
		sqmail.gui.utils.update_ctree(self.widget.folderlist, \
			node, self.describe_vfolder(vf))
		style = self.widget.folderlist.get_style().copy()
		self.style_vfolder(vf, style)
		self.widget.folderlist.node_set_row_style(node, style)
		self.widget.folderlist.thaw()
		self.popprogress()

	# Return the folder list.

	def vfolderlist(self):
		l = []
		for i in xrange(self.widget.folderlist.rows):
			node = self.widget.folderlist.node_nth(i)
			vf = self.vfolder(node)
			l.append(vf.id)
		return l

	# Write the folder list back to the database.

	def write_vfolderlist(self):
		sqmail.utils.setsetting("vfolders", self.vfolderlist())

	# User has selected a vfolder to peruse.

	def select_vfolder(self):
		node = self.widget.folderlist.selection[0]
		vf = self.vfolder(node)
		if (vf == None):
			return
		vf.scan()
		self.update_vfolder(node)
		self.widget.foldername.set_text(vf.name)
		self.widget.folderquery.freeze()
		self.widget.folderquery.set_point(0)
		self.widget.folderquery.delete_text(0, -1)
		self.widget.folderquery.insert(None, None, None, \
			vf.getquery())
		self.widget.folderquery.set_word_wrap(1)
		self.widget.folderquery.thaw()
		self.update_messagelist()

	# ...or has deselected one. (Generated implicitly.)

	def unselect_vfolder(self, node):
		vf = self.vfolder(node)
		if (vf == None):
			return
		vf.purge()
		self.startcounting()
		#vf.scan()
		self.update_vfolder(node)

	# Modify this vfolder.

	def modify_vfolder(self):
		query = self.widget.folderquery.get_chars(0, -1)
		vf = self.vfolder()
		node = self.widget.folderlist.selection[0]
		vf.setname(self.widget.foldername.get_text())
		vf.setquery(query)
		vf.save()
		self.write_vfolderlist()

		#sqmail.gui.utils.update_ctree(self.widget.folderlist, \
		#	node, self.describe_vfolder(vf))
		self.update_vfolderlist()

	# Copy this vfolder.

	def copy_vfolder(self):
		node = self.widget.folderlist.selection[0]
		vf = self.vfolder()
		newvf = sqmail.vfolder.VFolder(name="***new***", query=vf.query, \
			parent=vf.parent)
		newvf.setname("Copy of "+vf.getname())
		newvf.save()

		l = self.vfolderlist()
		i = l.index(vf.id)
		l.insert(i+1, newvf.id)
		sqmail.utils.setsetting("vfolders", l)
		
		self.widget.folderlist.freeze()
		self.update_vfolderlist()
		self.widget.folderlist.select_row(i+1, 0)
		self.widget.folderlist.thaw()

	# Delete this vfolder.

	def delete_vfolder(self):
		vf = self.vfolder()

		for i in xrange(self.widget.folderlist.rows):
			node = self.widget.folderlist.node_nth(i)
			nvf = self.vfolder(node)
			if (nvf.parent == vf.name):
				nvf.setparent(vf.parent)

		l = self.vfolderlist()
		i = l.index(vf.id)
		l.remove(vf.id)
		sqmail.utils.setsetting("vfolders", l)
		
		self.widget.folderlist.freeze()
		self.update_vfolderlist()
		self.widget.folderlist.select_row(i, 0)
		self.widget.folderlist.thaw()
		
	# Move the vfolder.

	def move_vfolder(self, node, newparent, newsibling):
		nvf = self.vfolder(node)
		pvf = self.vfolder(newparent)
		if newsibling:
			svf = self.vfolder(newsibling)
		else:
			svf = pvf

		self.write_vfolderlist()
		nvf.setparent(pvf.id)
		nvf.save()

		self.widget.folderlist.freeze()
		i = self.widget.folderlist.focus_row
		self.update_vfolderlist()
		self.widget.folderlist.select_row(i, 0)
		self.widget.folderlist.thaw()

	# Move the vfolder down one space.

	def move_down_vfolder(self):
		vfn = self.widget.folderlist.focus_row
		vf = self.folderlist[vfn]

		if (vfn >= (len(self.folderlist)-1)):
			return

		self.widget.folderlist.freeze()
		next = self.folderlist[vfn+1]
		self.widget.folderlist.remove(vfn+1)
		self.widget.folderlist.insert(vfn, self.describe_vfolder(next))
		self.folderlist[vfn+1] = vf
		self.folderlist[vfn] = next
		self.widget.folderlist.thaw()

		self.write_vfolderlist()

	# Update the message list to reflect the currently selected vfolder.

	def update_messagelist(self):
		vf = self.vfolder()
		self.pushprogress()
		self.widget.messagelist.freeze()
		self.widget.messagelist.clear()
		self.messagelist = []
		for i in xrange(len(vf)):
			if not (i & 255):
				self.setprogress("Updating message list", i, len(vf))
			msg = sqmail.message.Message(vf[i][0])
			msg.readstatus = vf[i][1]
			msg.fromfield = vf[i][2]
			msg.realfromfield = vf[i][3]
			msg.subjectfield = vf[i][4]
			msg.date = vf[i][5]
			self.messagelist.append(msg)
			self.widget.messagelist.append(self.describe_message(msg))
			self.icon_message(i, msg)
			self.widget.messagelist.set_row_data(i, msg)
		self.widget.messagelist.unselect_all()
		self.widget.messagelist.thaw()
		self.setprogress("Analyzing message", 1, 1)
		self.popprogress()
		self.update_messagewindow()

	# Update the message window to reflect the currently selected message.

	def update_messagewindow(self):
		# Destroy all pages in the notebook.
		
		while len(self.messagepages):
			self.messagepages[0].destroy()
			self.widget.messagedisplay.remove_page(0)
			del self.messagepages[0]

		# Build the annotations drop-down list from the list of
		# folders.
		
		#self.widget.annotationfield.list.clear_items(0, -1)
		#for i in self.vfolderlist():
		#	vf = sqmail.vfolder.VFolder(id=i)
		#	item = gtk.GtkListItem(vf.name)
		#	self.widget.annotationfield.list.add(item)
		#	item.show()
		

		# Is there a selected message?
		
		msg = self.message()
		if not msg:
			self.widget.fromfield.set_text("")
			self.widget.tofield.set_text("")
			self.widget.annotationfield.set_text("")
			self.widget.datefield.set_text("")
			self.widget.subjectfield.set_text("")
			return

		# Fill in the message information boxes.
		
		self.widget.fromfield.set_text(sqmail.gui.utils.render_address(\
			(msg.getrealfrom(), msg.getfrom())))
		self.widget.tofield.set_text(sqmail.gui.utils.render_addrlist(msg.getto()))
		self.widget.annotationfield.set_text(msg.getannotation())
		self.widget.datefield.set_text(sqmail.gui.utils.render_time(msg.getdate()))
		self.widget.subjectfield.set_text(msg.getsubject())
		
		# Add the first pane to the notebook (the raw message one).
		
		viewer = sqmail.gui.headerspane.HeadersViewer(self, msg)
		self.widget.messagedisplay.append_page(viewer.getpage(), viewer.gettab())
		self.messagepages.append(viewer)

		# Now add the other panes for each attachment.

		try:
			mime = msg.mimeflatten()
			for i in range(len(mime)):
				if (mime[i][1] in sqmail.gui.textviewer.displayable):
					viewer = sqmail.gui.textviewer.TextViewer(self, mime[i])
				elif (mime[i][1] in sqmail.gui.htmlviewer.displayable):
					viewer = sqmail.gui.htmlviewer.HTMLViewer(self, mime[i])
				else:
					viewer = sqmail.gui.binaryviewer.BinaryViewer(self, mime[i])
				self.widget.messagedisplay.append_page(viewer.getpage(), viewer.gettab())
				self.messagepages.append(viewer)

			# Make sure that the second pane, which will be the body text,
			# is visible.

			self.widget.messagedisplay.set_page(1)
		except sqmail.message.MIMEDecodeAbortException:
			pass

	# Change the read-status of a message.

	def changeread_message(self, mn, msg, status):
		vf = self.vfolder()
		msg.readstatus = status
		msg.savealltodatabase()

		self.widget.messagelist.freeze()
		sqmail.gui.utils.update_clist(self.widget.messagelist, \
			mn, self.describe_message(msg))
		self.icon_message(mn, msg)
		self.widget.messagelist.thaw()


	# User has selected a message. Change to it and update.

	def select_message(self, i):
		msg = self.message()

		if (msg and (msg.getreadstatus() == "Unread")):
			self.changeread_message(i, msg, "Read")
		self.update_messagewindow()

	# --- Signal handlers -------------------------------------------------

	def on_vfolder_select(self, obj, node, b):
		self.select_vfolder()

	def on_vfolder_unselect(self, obj, node, b):
		self.unselect_vfolder(node)

	def on_message_select(self, obj, row, b, event):
		self.select_message(row)

	def on_vfolder_move(self, obj, node, newparent, newsibling):
		self.move_vfolder(node, newparent, newsibling)
		return 0

	def on_vfolder_update(self, obj):
		self.modify_vfolder()

	def on_vfolder_copy(self, obj):
		self.copy_vfolder()
	
	def on_vfolder_delete(self, obj):
		self.delete_vfolder()

	def on_vfolder_clear(self, obj):
		self.widget.folderquery.freeze()
		self.widget.folderquery.set_point(0)
		self.widget.folderquery.delete_text(0, -1)
		self.widget.folderquery.thaw()

	def on_prev_message(self, obj):
		s = self.widget.messagelist.selection
		if (len(s) != 1):
			return
		mn = s[0]-1
		if (mn > 0):
			self.widget.messagelist.unselect_all()
			self.widget.messagelist.select_row(mn, 0)
			self.widget.messagelist.moveto(mn, 0, 0.5, 0)

	def on_next_message(self, obj):
		s = self.widget.messagelist.selection
		if (len(s) != 1):
			return
		mn = s[0]+1
		if (mn < self.widget.messagelist.rows):
			self.widget.messagelist.unselect_all()
			self.widget.messagelist.select_row(mn, 0)
			self.widget.messagelist.moveto(mn, 0, 0.5, 0)

	def on_next_unread_message(self, obj):
		s = self.widget.messagelist.selection
		if (len(s) != 1):
			return
		mn = s[0]+1
		while (self.message(mn).readstatus != "Unread"):
			mn = mn + 1
			if (mn >= self.widget.messagelist.rows):
				break
		self.widget.messagelist.unselect_all()
		self.widget.messagelist.select_row(mn, 0)
		self.widget.messagelist.moveto(mn, 0, 0.5, 0)

	def on_mark_read(self, obj):
		self.widget.folderlist.freeze()
		for i in self.widget.messagelist.selection:
			msg = self.message(i)
			if (msg.readstatus == "Unread"):
				self.changeread_message(i, msg, "Read")
		self.widget.folderlist.thaw()
		self.on_next_message(None)
		
	def on_delete(self, obj):
		self.widget.folderlist.freeze()
		for i in self.widget.messagelist.selection:
			msg = self.message(i)
			self.changeread_message(i, msg, "Deleted")
		self.widget.folderlist.thaw()
		self.on_next_message(None)
		
	def on_quit(self, obj):
		sys.exit(0)

	def on_preferences(self, obj):
		sqmail.gui.preferences.SQmaiLPreferences(self)

	def on_purges(self, obj):
		sqmail.gui.purges.SQmaiLPurges(self)

	def on_about(self, obj):
		self.readglade("aboutwin")
		
	def on_new(self, obj):
		sqmail.gui.compose.SQmaiLCompose(self, None, None)

	def on_reply(self, obj):
		msg = self.message()
		if not msg:
			return
		to = [[msg.getrealfrom(), msg.getfrom()]]
		sqmail.gui.compose.SQmaiLCompose(self, msg, to)
	
	def on_reply_all(self, obj):
		msg = self.message()
		if not msg:
			return
		to = [[msg.getrealfrom(), msg.getfrom()]]
		to.extend(msg.getto())
		sqmail.gui.compose.SQmaiLCompose(self, msg, to)

	def on_save_configuration(self, obj):
		sqmail.gui.utils.FileSelector("Save Configuration...", "", sqmail.preferences.save_config)

	def on_load_configuration(self, obj):
		sqmail.gui.utils.FileSelector("Load Configuration...", "", sqmail.preferences.load_config)

	def on_check_mail(self, obj):
		self.stopcounting()
		p = sqmail.preferences.get_incomingprotocol()
		if (p == "Spool"):
			sqmail.gui.spoolfetcher.SpoolFetcher(self)
		elif (p == "POP"):
			sqmail.gui.popfetcher.POPFetcher(self)
		elif (p == "IMAP"):
			sqmail.gui.utils.errorbox("Sorry --- IMAP fetching is not implemented yet.")

	def on_spam(self, obj):
		msg = self.message()
		if not msg:
			return
		msgname = tempfile.mktemp()
		msgfp = open(msgname, "w")
		msgfp.write(msg.getheaders())
		msgfp.write("\n\n")
		msgfp.write(msg.getbody())
		msgfp.write("\n")
		msgfp.close()
		c = sqmail.gui.compose.SQmaiLCompose(self, None, \
			[["Spamcop", "spamcop@spamcop.net"]])
		c.on_attach_file(msgname, type="message/rfc822")
		os.unlink(msgname)

	def on_aliases(self, obj):
		sqmail.gui.aliases.SQmaiLAliases(self)
	
	def on_mainwin_resize(self, obj):
		win = self.widget.mainwin.get_window()
		sqmail.utils.setsetting("mainwin size", (win.width, win.height))
		
	def on_change_annotation(self, obj):
		print "Changed annotation"

	def on_message_drag_begin(self, obj):
		print "Drag begin"

	def on_unimplemented(self, obj):
		sqmail.gui.utils.errorbox("Sorry --- this feature is not implemented yet.")

	on_addresses = on_unimplemented
	on_forward = on_unimplemented

# Revision History
# $Log: reader.py,v $
# Revision 1.13  2001/03/05 20:44:41  dtrg
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
# Revision 1.12  2001/02/23 19:50:26  dtrg
# Lots of changes: added the beginnings of the purges system, CLI utility
# for same, GUI utility & UI for same, plus a CLI vfolder lister.
#
# Revision 1.11  2001/02/23 16:56:35  dtrg
# Added real icons for the Unread/Deleted/Sent field on the message list.
# Also removed the first field, which we never used.
#
# Revision 1.10  2001/02/20 17:22:36  dtrg
# Moved the bulk of the preference system out of the gui directory, where it
# doesn't belong. sqmail.gui.preferences still exists but it just contains
# the preferences editor. sqmail.preferences now contains the access
# functions and load/save functions.
#
# Revision 1.9  2001/02/15 19:34:16  dtrg
# Many changes. Bulletproofed the send box, so it should now give you
# (reasonably) user-friendly messages when something goes wrong; rescan a
# vfolder when you leave it, so the vfolder list is kept up-to-date (and in
# the background, too); added `unimplemented' messages to a lot of
# unimplemented buttons; some general tidying.
#
# Revision 1.8  2001/02/02 20:03:01  dtrg
# Added mail alias and default domain support.
# Saves the size of the main window, but as yet doesn't set the size on
# startup.
#
# Revision 1.7  2001/01/26 11:55:25  dtrg
# Double woohoo! Vfolder styles now work. Thanks to all the people on the
# PyGTK mailing list who put up with me on this. Also fixed the vfolder-copy
# feature, which was resulting in duplicate vfolder entries (SQmaiL recover
# vfolders is a godsend --- that's why I wrote it).
#
# Revision 1.6  2001/01/25 20:55:06  dtrg
# Woohoo! Vfolder styling now works (mostly, except backgrounds). Also added
# background vfolder counting to avoid that nasty delay on startup or
# whenever you fetch new mail.
#
# Revision 1.5  2001/01/22 18:31:55  dtrg
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
# Revision 1.4  2001/01/19 20:37:23  dtrg
# Changed the way vfolders are stored in the database.
#
# Now they're stored in a seperate table, vfolders, and referenced by id.
# This means that finally you can have two vfolders with the same name (very
# handy in a tree scenario). The system's also slightly less fragile.
#
# WARNING! The current code will not work with previous versions of the
# database. You will need to do "SQmaiL upgrade" to automatically convert
# your data.
#
# Revision 1.3  2001/01/18 19:27:54  dtrg
# First attempt at vfolder list styles (font works, colours don't).
#
# Revision 1.2  2001/01/11 20:07:23  dtrg
# Added preliminary HTML rendering support (ten minutes work!).
#
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


