# The mail reader top-level program.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/reader.py,v $
# $State: Exp $

import os
import sys
import time
import gtk
import GDK
import gnome.ui
import gnome.url
import libglade
import urllib
import tempfile
import thread
import time
import string
import sqmail.vfolder
import sqmail.message
import sqmail.preferences
import sqmail.picons
import sqmail.server
import sqmail.utils
import sqmail.gui.textviewer
import sqmail.gui.binaryviewer
import sqmail.gui.htmlviewer
import sqmail.gui.imageviewer
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
	gladefilename = sys.path[0] + "/sqmail.glade"
	dnd_target = [("application/x-sqmail-message", 0, -1)]

	def __init__(self):
		global instance
		if instance:
			raise RuntimeError("You can only create one SQmaiLReader instance at a time!")
		instance = self

		# Create the main window and the widget store.

		self.mainwindow = self.readglade("mainwin")
		self.widget = sqmail.gui.utils.WidgetStore(self.mainwindow)
		
		# Create various background threads.

		sqmail.picons.start_thread()

		# Initialize SQmaiL server and add callback

		self.server = sqmail.server.Server()
		gtk.timeout_add(300, self.server.loop)

		# Initialise instance variables.

		self.messagelist = []
		self.messagepages = []
		self.counting = None

		# Initialize messagelist instance

		self.messagelist = MessageList(self)

		# Start polling as determined by the settings

		interval = 1000*int(sqmail.utils.getsetting("Polling interval", "10"))
		gtk.timeout_add(interval, self.poll)

		# Enable DND on the vfolder list.

		self.widget.folderlist.drag_dest_set(gtk.DEST_DEFAULT_ALL, \
			self.dnd_target, GDK.ACTION_MOVE)
		self.widget.messageicon.drag_source_set(GDK.BUTTON1_MASK, \
			self.dnd_target, GDK.ACTION_MOVE)
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
		return (vf.getname(), "%d" % vf.getunread(), "%d" % vf.getsize())

	# Modify the passed style to reflect the status of the current folder.

	def style_vfolder(self, vf, style):
		if vf.getunread():
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
			sel = self.widget.folderlist.node_get_row_data(sel[0]).id
		else:
			sel = None
		print "Clearing list"
		self.widget.folderlist.clear()
		print "Done"

		# Create tree starting with root folder and recurse depth
		# first adding nodes in order specified by the vfolder's
		# getchildren function.
		self._addnode_recursive(sqmail.vfolder.get_by_id(1), None, sel)
		
		#self.startcounting()
		self.widget.folderlist.thaw()
		self.popprogress()
		
	def _addnode_recursive(self, vfolder, parentnode, sel):
		"""Helper function for update_vfolder"""
		node = self.widget.folderlist.insert_node(parentnode, None,
					["", "", ""], is_leaf=0, expanded=1)
		self.widget.folderlist.node_set_row_data(node, vfolder)
		self.update_vfolder(node)
		if vfolder.id == sel:
			self.widget.folderlist.select(node)
		for child in vfolder.getchildren():
			self._addnode_recursive(child, node, sel)

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
		self.update_vfolder(node)
		self.widget.foldername.set_text(vf.name)
		self.widget.folderquery.freeze()
		self.widget.folderquery.set_point(0)
		self.widget.folderquery.delete_text(0, -1)
		self.widget.folderquery.insert(None, None, None,
			vf.getuquerystr())
		self.widget.folderquery.set_word_wrap(1)
		self.widget.folderquery.thaw()
		self.messagelist.update_messagelist(vf)

	# ...or has deselected one. (Generated implicitly.)

	def unselect_vfolder(self, node):
		vf = self.vfolder(node)
		if (vf == None):
			return
		self.messagelist.save_curmsg(vf)
		#vf.clearcache()
		#self.startcounting()
		#vf.scan()
		self.update_vfolder(node)

	# Modify this vfolder.

	def modify_vfolder(self):
		query = self.widget.folderquery.get_chars(0, -1)
		vf = self.vfolder()
		node = self.widget.folderlist.selection[0]
		vf.setname(self.widget.foldername.get_text())
		vf.setuquery(query)
		#self.write_vfolderlist()

		#sqmail.gui.utils.update_ctree(self.widget.folderlist, \
		#	node, self.describe_vfolder(vf))
		self.update_vfolderlist()

	# Copy this vfolder.

	def copy_vfolder(self):
		node = self.widget.folderlist.selection[0]
		vf = self.vfolder()
		newvf = sqmail.vfolder.create_vfolder("Copy of " + vf.getname(),
											  vf.id, str(vf.uquery))
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

		mainparent = vf.getparents()[0]
		for child in vf.getchildren():
			mainparent.addchildid(child.id)

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

		# Update the icon.

		if sqmail.preferences.get_usepicons():
			sqmail.gui.utils.set_xpm(self.widget.messageicon, \
				sqmail.picons.get_picon_xpm(msg.getfrom()))
		else:
			sqmail.gui.utils.set_xpm(self.widget.messageicon, \
				None)

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
				elif (mime[i][1] in sqmail.gui.imageviewer.displayable):
					viewer = sqmail.gui.imageviewer.ImageViewer(self, mime[i])
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
		self.messagelist.update_readstatus(mn, msg)

	# User has selected a message. Change to it and update.

	def select_message(self, i):
		msg = self.message()

		if (msg and (msg.getreadstatus() == "Unread")):
			self.changeread_message(i, msg, "Read")
		self.update_messagewindow()

	def poll(self):
		"""Poll in the background

		Every so often, as determind by preferences, check to see if
		the sequence "UpdatedVFolders" has any members.  If it does,
		it clears the sequence, reloads the folder list, and also
		reloads the message list, if the current folder was one
		affected.

		"""
		try: self.polling_sequence
		except AttributeError:
			self.polling_sequence = \
				   (sqmail.sequences.get_by_name("UpdatedVFolders") or
				    sqmail.sequences.create_sequence("UpdatedVFolders"))

		print "beginning poll"
		changed_folderids = self.polling_sequence.list()
		if changed_folderids:
			print "found new messages"
			self.polling_sequence.deleteids(changed_folderids)
			for folderid in changed_folderids:
				vf = sqmail.vfolder.get_by_id(folderid)
				vf.getunread("table")
				vf.getsize("table")
				if vf is self.messagelist.vfolder:
					self.messagelist.save_curmsg(vf)
					self.messagelist.update_messagelist(vf)
			self.update_vfolderlist()
		return 1

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

	# Change the readstatus of an individual message.

	def change_readstatus(self, readstatus):
		self.widget.folderlist.freeze()
		for i in self.widget.messagelist.selection:
			msg = self.message(i)
			self.changeread_message(i, msg, readstatus)
		self.widget.folderlist.thaw()
		
	def on_mark_message_read(self, obj):
		self.change_readstatus("Read")

	def on_mark_message_unread(self, obj):
		self.change_readstatus("Unread")

	def on_mark_message_deleted(self, obj):
		self.change_readstatus("Deleted")

	def on_mark_message_sent(self, obj):
		self.change_readstatus("Sent")

	# The same as on_mark_message_deleted, but advances to the next
	# message.

	def on_delete(self, obj):
		self.change_readstatus("Deleted")
		self.on_next_message(None)
		
	def on_quit(self, obj):
		self.server.stop()   # Stop server, remove socket
		self.messagelist.save_curmsg(self.vfolder())
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
		if sqmail.preferences.get_deletespam():
			self.on_delete(obj)

	def on_add_to_picons_queue(self, obj):
		vf = self.vfolder()
		for i in xrange(len(vf)):
			print "Queuing", vf[i][2]
			sqmail.picons.queue_address(vf[i][2])
		
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

	# Start dragging the message icon.

	def on_message_start_drag(self, obj, context, selection_data, info, time):
		data = "Hello, world!"
		selection_data.set(selection_data.target, 8, data)

	on_addresses = on_unimplemented
	on_forward = on_unimplemented



class MessageList:
	"""Wrapper around widget for displaying message lists

	self.widget is the main widget, a CList.  This class was added
	because of the complications in only getting information about
	some of the messages in a folder.  at_top and at_bottom should be
	true respectively if there are no more messages to get before or
	after those currently displayed.

	"""
	def __init__(self, reader):
		self.reader = reader
		self.widget = reader.widget.messagelist
		
		self.blocksize = sqmail.utils.getsetting("Header blocksize", 100)
		self.curmsg = None
		self.curmsgpos = None
		self.at_top = None
		self.at_bottom = None
		self.messagelist = None
		self.vfolder = None

		# Load pixmaps
		self.deleted_pixmap = gtk.GtkPixmap(self.widget.get_window(),
			sys.path[0] + "/images/deleted-message.xpm")
		self.unread_pixmap = gtk.GtkPixmap(self.widget.get_window(),
			sys.path[0] + "/images/unread-message.xpm")
		self.sent_pixmap = gtk.GtkPixmap(self.widget.get_window(),
			sys.path[0] + "/images/sent-message.xpm")


	def update_messagelist(self, vfolder):
		"""Update message list to reflect currently selected vfolder

		First insert some messages aftet and including the current
		message, and mark the first one inserted as the current.  Then
		insert the previous ones at the beginning.

		"""
		self.vfolder = vfolder
		self.reader.pushprogress()
		self.widget.freeze()
		self.widget.clear()
		
		self.messagelist = []
		self.insert_messagelist(vfolder.scan(vfolder.curmsg, self.blocksize))
		self.curmsgpos = 0
		self.insert_messagelist(vfolder.scan(vfolder.curmsg,
											 -self.blocksize), 0)
		# This moveto doesn't work, don't know why not
		self.widget.moveto(self.curmsgpos)
		self.widget.select_row(self.curmsgpos, 0)
		self.widget.thaw()
		self.reader.setprogress("Analyzing message", 1, 1)
		self.reader.update_messagewindow()

	def insert_messagelist(self, newlist, position = -1):
		"""Insert sequence of message headers at specified position

		If position == -1, append.  This also updates self.messagelist
		"""
		if position == -1: position = len(self.messagelist)

		ml_length = len(newlist)
		i = 0
		for columns in newlist:
			msg = sqmail.message.Message(columns[0])
			msg.readstatus = columns[1]
			msg.fromfield = columns[2]
			msg.realfromfield = columns[3]
			msg.subjectfield = columns[4]
			msg.date = columns[5]
			self.messagelist.insert(position + i, msg)
			self.widget.insert(position + i, self.describe_message(msg))
			self.icon_message(position + i, msg)
			self.widget.set_row_data(position + i, msg)
			i = i + 1
		if self.curmsgpos is not None and self.curmsgpos <= position:
			self.curmsgpos = self.curmsgpos + i

	def icon_message(self, i, msg):
		"""Set the icon for a message"""
		pixmap = None
		readstatus = msg.getreadstatus()
		if (readstatus == "Unread"):
			pixmap = self.unread_pixmap
		elif (readstatus == "Sent"):
			pixmap = self.sent_pixmap
		elif (readstatus == "Deleted"):
			pixmap = self.deleted_pixmap
		if pixmap:
			self.widget.set_pixmap(i, 0, pixmap)

	def describe_message(self, msg):
		"""Return message information to be listed in messagelist widget"""
		f = sqmail.gui.utils.render_address((msg.getrealfrom(),
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

	def update_readstatus(self, msgpos, msg):
		"""Add/remove the little picture of the envelope on the left"""
		self.widget.freeze()
		self.icon_message(msgpos, msg)
		sqmail.gui.utils.update_clist(self.widget, msgpos,
									  self.describe_message(msg))
		self.widget.thaw()

	def save_curmsg(self, vf):
		"""Writes current message to database for current folder"""
		current_message = self.reader.message()
		if current_message:
			vf.setcurmsg(current_message.id)

# Revision History
# $Log: reader.py,v $
# Revision 1.24  2001/06/08 04:38:16  bescoto
# Multifile diff: added a few convenience functions to db.py and sequences.py.
# vfolder.py and queries.py are largely new, they are part of a system that
# caches folder listings so the folder does not have to be continually reread.
# createdb.py and upgrade.py were changed to deal with the new folder formats.
# reader.py was changed a bit to make it compatible with these changes.
#
# Revision 1.23  2001/05/31 20:28:01  bescoto
# Added a few lines so reader starts server, polls periodically, and then
# stops on_quit.
#
# Revision 1.22  2001/05/26 18:17:47  bescoto
# A few changes to work with new vfolder.py changes
#
# Revision 1.21  2001/05/23 10:08:31  dtrg
# Added the image viewer; now gifs, jpegs and pngs will be viewed inline.
#
# Revision 1.20  2001/05/01 18:23:42  dtrg
# Added the Debian package building stuff. Now much easier to install.
# Some GUI tidying prior to the release.
# Did some work on the message DnD... turns out to be rather harder than I
# thought, as you can't have a CTree do its own native DnD and also drag
# your own stuff onto it at the same time.
#
# Revision 1.19  2001/04/19 18:24:16  dtrg
# Added the ability to change the readstatus of a message. Also did some
# minor tweaking to various areas.
#
# Revision 1.18  2001/03/13 19:28:22  dtrg
# Doesn't load message headers until you select the folder; this improves
# speed and memory consumption considerably (because it's not keeping huge
# numbers of message headers around).
#
# Revision 1.17  2001/03/12 19:30:11  dtrg
# Now automatically queues up new messages for picon fetching in the
# background (using a real thread, too).
#
# Revision 1.16  2001/03/12 10:35:06  dtrg
# Now lets you turn off picons.
#
# Revision 1.15  2001/03/09 20:36:19  dtrg
# First draft picons support.
#
# Revision 1.14  2001/03/09 10:39:55  dtrg
# Replaced some str() with % syntax.
#
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


