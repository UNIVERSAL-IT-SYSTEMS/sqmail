# The mail reader top-level program.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/reader.py,v $
# $State: Exp $

import sys
import time
import gtk
import gnome.ui
import libglade
import sqmail.vfolder
import sqmail.message
import sqmail.gui.textviewer
import sqmail.gui.binaryviewer
import sqmail.gui.preferences
import sqmail.gui.compose
import sqmail.gui.utils
import sqmail.gui.spoolfetcher
import sqmail.gui.popfetcher

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
		while gtk.events_pending():
			gtk.mainiteration(0)

	def popprogress(self):
		self.widget.applicationbar.set_progress(0.0)
		self.widget.applicationbar.pop()

	# Return a description of a vfolder suitable for insertion into the
	# folder list.

	def describe_vfolder(self, vf):
		unread = vf.getunread()
		if unread:
			unread = str(unread)
		else:
			unread = ""
		return (vf.name, unread, str(vf.getlen()))

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
		return ("", msg.getreadstatus(), f, msg.getsubject(), d)
		
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
			self.setprogress("Updating vfolders", i, len(l))
			name = l[i]
			vf = sqmail.vfolder.VFolder(name=name)
			parent = sqmail.utils.getsetting("vfolder parent "+name)
			if parent:
				try:
					parent = d[parent]
				except KeyError:
					print "DANGER! Configuration inconsistency in vfolder", name+"."
					parent = None

			node = self.widget.folderlist.insert_node(parent, None, \
				self.describe_vfolder(vf), \
				is_leaf=0, expanded=1)
			self.widget.folderlist.node_set_row_data(node, vf)
			d[name] = node
			if (vf.name == sel):
				self.widget.folderlist.select(node)
		self.widget.folderlist.thaw()
		self.popprogress()
		
	# Return the folder list.

	def vfolderlist(self):
		l = []
		for i in xrange(self.widget.folderlist.rows):
			node = self.widget.folderlist.node_nth(i)
			vf = self.vfolder(node)
			l.append(vf.name)
		return l

	# Write the folder list back to the database.

	def write_vfolderlist(self):
		sqmail.utils.setsetting("vfolders", self.vfolderlist())

	# User has selected a vfolder to peruse.

	def select_vfolder(self):
		vf = self.vfolder()
		if (vf == None):
			return
		self.widget.foldername.set_text(vf.name)
		self.widget.folderquery.freeze()
		self.widget.folderquery.set_point(0)
		self.widget.folderquery.delete_text(0, -1)
		self.widget.folderquery.insert(None, None, None, \
			vf.getquery())
		self.widget.folderquery.set_word_wrap(1)
		self.widget.folderquery.thaw()
		self.update_messagelist()

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
		newvf = sqmail.vfolder.VFolder(name=vf.name, query=vf.query, \
			parent=vf.parent)
		newvf.name = "Copy of "+newvf.name
		newvf.save()

		l = self.vfolderlist()
		i = l.index(vf.name)
		l.insert(i+1, newvf.name)
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
		i = l.index(vf.name)
		l.remove(vf.name)
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
		nvf.setparent(pvf.name)
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
			self.widget.messagelist.set_row_data(i, msg)
		self.widget.messagelist.unselect_all()
		self.widget.messagelist.thaw()
		self.setprogress("Analyzing message", 1, 1)
		self.popprogress()
		self.update_messagewindow()

	# Update the message window to reflect the currently selected message.

	def update_messagewindow(self):
		while len(self.messagepages):
			self.messagepages[0].destroy()
			self.widget.messagedisplay.remove_page(0)
			del self.messagepages[0]

		self.widget.annotationfield.list.clear_items(0, -1)
		for i in self.vfolderlist():
			item = gtk.GtkListItem(i)
			self.widget.annotationfield.list.add(item)
			item.show()

		msg = self.message()
		if not msg:
			self.widget.fromfield.set_text("")
			self.widget.tofield.set_text("")
			self.widget.annotationfield.entry.set_text("")
			self.widget.datefield.set_text("")
			self.widget.subjectfield.set_text("")
			return

		self.widget.fromfield.set_text(sqmail.gui.utils.render_address(\
			(msg.getrealfrom(), msg.getfrom())))
		self.widget.tofield.set_text(sqmail.gui.utils.render_addrlist(msg.getto()))
		self.widget.annotationfield.entry.set_text(msg.getannotation())
		self.widget.datefield.set_text(sqmail.gui.utils.render_time(msg.getdate()))
		self.widget.subjectfield.set_text(msg.getsubject())
		
		mime = msg.mimeflatten()
		for i in range(len(mime)):
			if (mime[i][1] in sqmail.gui.textviewer.displayable):
				viewer = sqmail.gui.textviewer.TextViewer(self, mime[i])
			else:
				viewer = sqmail.gui.binaryviewer.BinaryViewer(self, mime[i])
			self.widget.messagedisplay.append_page(viewer.getpage(), viewer.gettab())
			self.messagepages.append(viewer)

	# Change the read-status of a message.

	def changeread_message(self, mn, msg, status):
		vf = self.vfolder()
		msg.readstatus = status
		msg.savealltodatabase()

		self.widget.messagelist.freeze()
		sqmail.gui.utils.update_clist(self.widget.messagelist, \
			mn, self.describe_message(msg))
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
		sqmail.gui.utils.FileSelector("Save Configuration...", "", sqmail.gui.preferences.save_config, None)

	def on_load_configuration(self, obj):
		sqmail.gui.utils.FileSelector("Load Configuration...", "", sqmail.gui.preferences.load_config, None)

	def on_check_mail(self, obj):
		p = sqmail.gui.preferences.get_incomingprotocol()
		if (p == "Spool"):
			sqmail.gui.spoolfetcher.SpoolFetcher(self)
		elif (p == "POP"):
			sqmail.gui.popfetcher.POPFetcher(self)

	def on_spam(self, obj):
		msg = self.message()
		if not msg:
			return
		print msg.getheaders()
		print
		print msg.getbody()

# Revision History
# $Log: reader.py,v $
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


