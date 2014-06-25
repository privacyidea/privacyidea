# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  June 30, 2014 Cornelius Kölbel, info@privacyidea.org
#  http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
from privacyidea import model
from privacyidea.model import Machine, MachineToken, MachineOptions
from privacyidea.model.meta import Session

import logging
log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with

@log_with(log)
def create(name):
    machine = Machine(name)
    machine.store()
    log.info("Machine %r created." % machine)
    return machine

@log_with(log)
def delete(name):
    Session.query(Machine).filter(Machine.cm_name == name).delete()
    Session.commit()
    
@log_with(log)    
def show():
    res = {}
    #sqlquery = Session.query(Machine).filter()
    sqlquery = Session.query(Machine)
    for machine in sqlquery:
        res[machine.cm_name] = machine.to_json()
    return res
