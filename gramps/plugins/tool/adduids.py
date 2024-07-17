#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2008       Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"""Tools/Database Processing/Add UIDs"""

import uuid

#-------------------------------------------------------------------------
#
# gnome/gtk
#
#-------------------------------------------------------------------------
from gi.repository import GObject
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.lib import (
    Attribute, AttributeType, ChildRefType, Citation, Date, EventRoleType,
    EventType, LdsOrd, NameType, NoteType, PlaceType, Person, UrlType)

from gramps.gen.db import find_surname_name, DbTxn
from gramps.gen.const import URL_MANUAL_PAGE
from gramps.gui.utils import ProgressMeter
from gramps.gui.display import display_help
from gramps.gui.managedwindow import ManagedWindow

from gramps.gui.dialog import OkDialog
from gramps.gui.plug import tool
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
from gramps.gui.glade import Glade
from gramps.gen.utils.id import create_uid

#-------------------------------------------------------------------------
#
# constants
#
#-------------------------------------------------------------------------

WIKI_HELP_PAGE = '%s_-_Tools' % URL_MANUAL_PAGE
WIKI_HELP_SEC = _('manual|Fix_Capitalization_of_Family_Names')

#-------------------------------------------------------------------------
#
# AddUIDs
#
#-------------------------------------------------------------------------
def generate_paf5_uid(self, handle):
    uid = create_uid(self, handle)
    checksum = calculate_checksum(uid)
    return uid[:32] + checksum

def calculate_checksum(uid):
    # Calculate the checksum based on the first 32 characters of the UID
    uid_without_checksum = uid[:32]
    sumA = sumB = 0
    for i in range(0,len(uid_without_checksum),2):
        value = uid_without_checksum[i:i+2]
        sumA += int(value, 16)
        sumB += sumA
    checksum = ((sumA % 256) << 8) + (sumB % 256)
    return '{:04X}'.format(checksum)

class AddUIDs(tool.BatchTool, ManagedWindow):

    def __init__(self, dbstate, user, options_class, name, callback=None):
        uistate = user.uistate
        self.label = _('Add valid UIDs')
        self.cb = callback

        ManagedWindow.__init__(self,uistate,[],self.__class__)
        self.set_window(Gtk.Window(),Gtk.Label(),'')

        tool.BatchTool.__init__(self, dbstate, user, options_class, name)
        if self.fail:
            return

        self.progress = ProgressMeter(
            _('Checking Person UIDs'), '', parent=uistate.window)
        self.progress.set_pass(_('Searching for persons without valid UIDs'),
                               len(self.db.get_person_handles(False)))
        self.name_list = []

        for handle in self.db.get_person_handles(False):
            person = self.db.get_person_from_handle(handle)
            name = person.get_primary_name()

            attr_list = person.get_attribute_list()

            uid = False
            for attr in attr_list:

                key = attr.get_type().xml_str()
                value = attr.get_value().strip().replace('\r', ' ')

                if key == "_UID":
                    uid = True
                    checksum = value[32:36]
                    new_checksum = calculate_checksum(value)
                    if checksum != new_checksum:
                        self.name_list.append(name)
                    continue

            if not uid:
                # add name to the list
                self.name_list.append(name)

            if uistate:
                self.progress.step()

        if self.name_list:
            self.display()
        else:
            self.progress.close()
            self.close()
            OkDialog(_('No modifications needed'),
                     _("All persons have a valid UID."),
                     parent=uistate.window)

    def display(self):

        self.top = Glade()
        window = self.top.toplevel
        self.top.connect_signals({
            "destroy_passed_object" : self.close,
            "on_ok_clicked" : self.on_ok_clicked,
            "on_help_clicked" : self.on_help_clicked,
            "on_delete_event"   : self.close,
            })

        self.list = self.top.get_object("list")
        self.set_window(window,self.top.get_object('title'),self.label)
        self.setup_configs('interface.adduids', 500, 450)

        self.model = Gtk.ListStore(GObject.TYPE_STRING)

        c = Gtk.TreeViewColumn(_('Person Name'),
                               Gtk.CellRendererText(),text=0)
        self.list.append_column(c)

        self.list.set_model(self.model)

        self.iter_list = []
        self.progress.set_pass(_('Building display'),len(self.name_list))
        for name in self.name_list:
            handle = self.model.append()
            full_name = name.get_first_name() + ' ' + name.get_surname()
            self.model.set_value(handle,0, full_name)
            self.progress.step()
        self.progress.close()

        self.show()

    def build_menu_names(self, obj):
        return (self.label,None)

    def on_help_clicked(self, obj):
        """Display the relevant portion of Gramps manual"""
        display_help(WIKI_HELP_PAGE , WIKI_HELP_SEC)

    def on_ok_clicked(self, obj):
        with DbTxn(_("UID validation"), self.db, batch=True
                   ) as self.trans:
            self.db.disable_signals()

            #  for handle, data in cursor:
            for handle in self.db.get_person_handles(False):
                person = self.db.get_person_from_handle(handle)

                change = False

                # check for _UID
                attr_list = person.get_attribute_list()

                uid = False
                for attr in attr_list:

                    key = attr.get_type().xml_str()
                    value = attr.get_value().strip().replace('\r', ' ')

                    if key == "_UID":
                        uid = True
                        checksum = value[32:36]
                        new_checksum = calculate_checksum(value)
                        if checksum != new_checksum:
                            new_value = value[0:32] + new_checksum
                            attr.set_value(new_value)
                            change = True
                        continue

                if not uid:
                    uid = generate_paf5_uid(self,handle)
                    attr = Attribute()
                    attr.set_type("_UID")
                    attr.set_value(uid)
                    person.add_attribute(attr)
                    change = True

                if change:
                    self.db.commit_person(person, self.trans)

        self.db.enable_signals()
        self.db.request_rebuild()
        # FIXME: this probably needs to be removed, and bookmarks
        # should always be rebuilt on a commit_person via signals
        # self.parent.bookmarks.redraw()
        self.close()
        self.cb()

#------------------------------------------------------------------------
#
#
#
#------------------------------------------------------------------------
class AddUIDsOptions(tool.ToolOptions):
    """
    Defines options and provides handling interface.
    """

    def __init__(self, name,person_id=None):
        tool.ToolOptions.__init__(self, name,person_id)
