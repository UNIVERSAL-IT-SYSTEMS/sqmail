# Purges editor.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/purges.py,v $
# $State: Exp $

import sys
import os
import sqmail.gui.reader
import sqmail.gui.utils
import sqmail.utils
import sqmail.db
import sqmail.purges
import sqmail.vfolder
import gtk
import re
import string

is_number = re.compile('[0-9]+( .*|)$')

instance = None
class SQmaiLPurges:
	def __init__(self, reader):
		global instance

		if instance:
			return
		instance = self

		self.reader = reader
		purgeswin = reader.readglade("purgeswin", self)
		self.widget = sqmail.gui.utils.WidgetStore(purgeswin)

		# Load the pixmaps.

		self.enabled_purge_pixmap = gtk.GtkPixmap(self.widget.list.get_window(), \
			sys.path[0] + "/images/enabled-purge.xpm")
		self.disabled_purge_pixmap = gtk.GtkPixmap(self.widget.list.get_window(), \
			sys.path[0] + "/images/disabled-purge.xpm")

		# Look up the purges, and add them to the list.

		self.update_list()

		# Because we start with nothing selected, deactive the controls.

		self.set_sensitive(0)

	# Update the list with new purges.

	def update_list(self):
		self.widget.list.clear()
		i = 0
		for purge in sqmail.purges.enumerate():
			purge = sqmail.purges.Purge(purge)
			self.widget.list.append(("", "", "", ""))
			self.widget.list.set_row_data(i, purge)
			w = gtk.GtkEntry()
			
			self.describe_purge(i)
			i = i + 1

	# Populate the data fields with information from the given purge.

	def update_purge(self, purge):
		self.widget.name.set_text(purge.name)
		self.widget.active.set_active(purge.active)
		self.widget.condition.freeze()
		self.widget.condition.set_point(0)
		self.widget.condition.delete_text(0, -1)
		self.widget.condition.insert(None, None, None, \
			purge.condition)
		self.widget.condition.set_word_wrap(1)
		self.widget.condition.thaw()
		self.widget.vfolder.set_text(self.describe_vfolder( \
			purge.vfolder))

	# Set the description of a purge in the list.

	def describe_purge(self, row):
		purge = self.widget.list.get_row_data(row)
		vfn = self.describe_vfolder(purge.vfolder)
		sqmail.gui.utils.update_clist(self.widget.list, row, \
			("", purge.name, vfn, purge.condition))
		if purge.active:
			self.widget.list.set_pixmap(row, \
				0, self.enabled_purge_pixmap)
		else:
			self.widget.list.set_pixmap(row, \
				0, self.disabled_purge_pixmap)
		
	# Return the string description of a vfolder name.

	def describe_vfolder(self, id):
		if (id > 0):
			vf = sqmail.vfolder.VFolder(id=id).name
			return "%d (%s)" % (id, vf)
		else:
			return "All messages (0)"

	# (De)sensitise the controls.

	def set_sensitive(self, s):
		self.widget.deletebutton.set_sensitive(s)
		self.widget.updatebutton.set_sensitive(s)
		self.widget.name.set_sensitive(s)
		self.widget.active.set_sensitive(s)
		self.widget.vfolder.set_sensitive(s)
		self.widget.condition.set_sensitive(s)

	# Given a vfolder name, work out what the user really wanted.

	def analyse_vfolder(self, vfolder):
		# Check to see if it's a vfolder ID.

		if is_number.search(vfolder):
			try:
				i = string.index(vfolder, " ")
				return int(vfolder[:i])
			except ValueError:
				return int(vfolder)
			
		# It's not, so we assume it's a vfolder name instead.

		try:
			vf = sqmail.vfolder.VFolder(name=vfolder)
			return vf.id
		except KeyError:
			# The vfolder couldn't be found.
			return -1

	# Signal handlers.

	def on_deactivate(self, obj):
		global instance
		self.widget.purgeswin.destroy()
		instance = None

	# A row has been selected.

	def on_selection(self, obj, row, col, event):
		self.set_sensitive(1)

		purge = self.widget.list.get_row_data(row)
		self.update_purge(purge)

	# ...and deselected.

	def on_deselection(self, obj, row, col, event):
		self.set_sensitive(0)

	# The user wants to add a new purge.

	def on_add(self, obj):
		purge = sqmail.purges.Purge("New Purge", 0, 0, "0")
		purge.save()
		self.update_list()
		
	# The user wants to remove a purge.
	
	def on_remove(self, obj):
		s = self.widget.list.selection
		purge = self.widget.list.get_row_data(s[0])
		purge.delete()
		self.set_sensitive(0)
		self.update_list()

	# The user edited something.

	def on_update(self, obj):
		s = self.widget.list.selection
		if (s == []):
			return
		purge = self.widget.list.get_row_data(s[0])
		name = self.widget.name.get_text()
		if (name != purge.name):
			if sqmail.gui.utils.yesnobox("You have tried to change the name of a purge.\nBe aware that this will COPY the purge, not rename it;\nwhat's more, you'll overwrite any other purge\nthat happens to be using the new name.\n\nDo you want to continue?"):
				return
		enabled = self.widget.active.get_active()
		vfolder = self.widget.vfolder.get_text()
		vfolder = self.analyse_vfolder(vfolder)
		if ((vfolder < 0) or (vfolder > len(sqmail.vfolder.get_folder_list()))):
			sqmail.gui.utils.errorbox("That vfolder could not be found,\nor the ID you entered was out of range.")
			return
		condition = self.widget.condition.get_chars(0, -1)
		if ((condition == "1") and (vfolder == 0)):
			if sqmail.gui.utils.yesnobox("The purge you're trying to enter will destroy\nALL your messages! Are you really, really\nsure you want to do this? (Hint: `No' is\nthe recommended answer.)"):
				return

		purge = sqmail.purges.Purge(name, enabled, vfolder, condition)
		purge.save()
		self.update_list()
		self.set_sensitive(0)

# Revision History
# $Log: purges.py,v $
# Revision 1.2  2001/05/01 18:23:42  dtrg
# Added the Debian package building stuff. Now much easier to install.
# Some GUI tidying prior to the release.
# Did some work on the message DnD... turns out to be rather harder than I
# thought, as you can't have a CTree do its own native DnD and also drag
# your own stuff onto it at the same time.
#
# Revision 1.1  2001/04/19 18:17:47  dtrg
# Added a GUI purges editor that appears to work.
