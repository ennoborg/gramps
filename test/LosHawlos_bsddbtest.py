#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
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

# test/LosHawlos_bsddbtest.py

from bsddb import dbshelve, db
import os
import sys

sys.path.append('../gramps')
import const

env_name = os.path.expanduser(const.bsddbenv_dir)
if not os.path.isdir(env_name):
       os.mkdir(env_name)

env = db.DBEnv()
env.set_cachesize(0,0x2000000)
env.set_lk_max_locks(25000)
env.set_lk_max_objects(25000)
env.set_flags(db.DB_LOG_AUTOREMOVE,1)
env_flags = db.DB_CREATE|db.DB_RECOVER|db.DB_PRIVATE|\
            db.DB_INIT_MPOOL|db.DB_INIT_LOCK|\
            db.DB_INIT_LOG|db.DB_INIT_TXN|db.DB_THREAD
try:
    env.open(env_name,env_flags)
except db.DBRunRecoveryError, e:
    print "Exception: "
    print e
    env.remove(env_name)
    env.open(env_name,env_flags)