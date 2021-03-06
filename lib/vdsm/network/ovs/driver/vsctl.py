# Copyright 2016 Red Hat, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#
# The implementation has been inspired by openstack OVS access
from __future__ import absolute_import

import collections
import json
import logging
import uuid

from vdsm.commands import execCmd
from vdsm.network import errors as ne
from vdsm.network.errors import ConfigNetworkError
from vdsm.utils import CommandPath, memoized

from . import (API as DriverAPI,
               Transaction as DriverTransaction,
               Command as DriverCommand)

# TODO: add a test which checks if following lists are mutual exclusive
# if there is just one item in a list, it is reported as single item
_DB_ENTRIES_WHICH_SHOULD_BE_LIST = {'ports', 'interfaces'}
# if a single item entry is not defined, it is reported as empty list
_DB_ENTRIES_WHICH_SHOULD_NOT_BE_LIST = {
    'tag', 'bond_active_slave', 'bond_mode', 'lacp', 'mac_in_use'}


class Transaction(DriverTransaction):

    def __init__(self):
        self.commands = []

    def commit(self):
        if not self.commands:
            return

        args = []
        for command in self.commands:
            args += ['--'] + command.cmd
        exec_line = [_ovs_vsctl_cmd()] + ['--oneline', '--format=json'] + args
        logging.debug('Executing commands: %s' % ' '.join(exec_line))

        rc, out, err = execCmd(exec_line)
        if rc != 0:
            raise ConfigNetworkError(
                ne.ERR_BAD_PARAMS,
                'Executing commands failed: %s' % '\n'.join(err))
        if out is None:
            return

        for i, line in enumerate(out):
            self.commands[i].set_raw_result(line)
        return [cmd.result for cmd in self.commands]

    def add(self, *commands):
        self.commands += commands


class Command(DriverCommand):

    def __init__(self, cmd):
        self.cmd = cmd
        self._result = None

    def execute(self):
        with Transaction() as t:
            t.add(self)
        return self.result

    @property
    def result(self):
        return self._result

    def set_raw_result(self, data):
        self._result = data.split(r'\n') if data else []


class DBResultCommand(Command):

    def set_raw_result(self, data):
        if not data:
            self._result = None
            return

        try:
            jdata = json.loads(data)
        except (ValueError, TypeError):
            self._result = ['ERROR: Unable to interpret cmd output', data]
            return

        headings = jdata['headings']
        data = jdata['data']
        results = []
        for record in data:
            obj = {}
            for pos, heading in enumerate(headings):
                obj[heading] = _normalize(heading, _val_to_py(record[pos]))
            results.append(obj)
        self._result = results


def create():
    return Vsctl()


class Vsctl(DriverAPI):

    def transaction(self):
        return Transaction()

    def add_br(self, bridge, may_exist=False):
        command = []
        if may_exist:
            command.append('--may-exist')
        command.extend(['add-br', bridge])
        return Command(command)

    def list_br(self):
        return Command(['list-br'])

    def del_br(self, bridge, if_exists=False):
        command = []
        if if_exists:
            command.append('--if-exists')
        command.extend(['del-br', bridge])
        return Command(command)

    def list_db_table(self, table, row=None):
        command = ['list', table]
        if row:
            command.append(row)
        return DBResultCommand(command)

    def add_vlan(self, bridge, vlan, fake_bridge_name=None, may_exist=False):
        command = []
        if may_exist:
            command.append('--may-exist')
        if fake_bridge_name is None:
            fake_bridge_name = 'vlan{}'.format(vlan)
        command.extend(['add-br', fake_bridge_name, bridge, str(vlan)])
        return Command(command)

    def del_vlan(self, vlan, fake_bridge_name=None, if_exist=False):
        if fake_bridge_name is None:
            fake_bridge_name = 'vlan{}'.format(vlan)
        return self.del_br(fake_bridge_name, if_exist)

    def add_bond(self, bridge, bond, nics, fake_iface=False, may_exist=False):
        command = []
        if may_exist:
            command.append('--may-exist')
        if fake_iface:
            command.append('--fake-iface')
        command.extend(['add-bond', bridge, bond] + nics)
        return Command(command)

    def attach_bond_slave(self, bond, slave):
        id = uuid.uuid4()
        if_cmd = ['--id=@%s' % id, 'create', 'Interface', 'name=%s' % slave]
        port_cmd = ['add', 'Port', bond, 'interfaces', '@%s' % id]
        return Command(if_cmd), Command(port_cmd)

    def detach_bond_slave(self, bond, slave):
        id = uuid.uuid4()
        if_cmd = ['--id=@%s' % id, 'get', 'Interface', slave]
        port_cmd = ['remove', 'Port', bond, 'interfaces', '@%s' % id]
        return Command(if_cmd), Command(port_cmd)

    def add_port(self, bridge, port, may_exist=False):
        command = []
        if may_exist:
            command.append('--may-exist')
        command.extend(['add-port', bridge, port])
        return Command(command)

    def del_port(self, port, bridge=None, if_exists=False):
        command = []
        if if_exists:
            command.append('--if-exists')
        command.append('del-port')
        if bridge:
            command.append(bridge)
        command.append(port)
        return Command(command)

    def list_ports(self, bridge):
        return Command(['list-ports', bridge])

    def set_db_entry(self, table, row, key, value):
        command = ['set', table, row, '%s=%s' % (key, value)]
        return Command(command)

    def do_nothing(self):
        return Command([])


def _val_to_py(val):
    """Convert a json ovsdb return value to native Python object."""
    if isinstance(val, collections.Sequence) and len(val) == 2:
        if val[0] == "uuid":
            return uuid.UUID(val[1])
        elif val[0] == "set":
            return [_val_to_py(x) for x in val[1]]
        elif val[0] == "map":
            return {_val_to_py(x): _val_to_py(y) for x, y in val[1]}
    return val


def _convert_to_list(data):
    return data if isinstance(data, list) else [data]


def _convert_to_single(data):
    return None if data == [] else data


def _normalize(heading, value):
    if heading in _DB_ENTRIES_WHICH_SHOULD_BE_LIST:
        value = _convert_to_list(value)
    elif heading in _DB_ENTRIES_WHICH_SHOULD_NOT_BE_LIST:
        value = _convert_to_single(value)
    return value


@memoized
def _ovs_vsctl_cmd():
    return CommandPath('ovs-vsctl',
                       '/usr/sbin/ovs-vsctl',
                       '/usr/bin/ovs-vsctl').cmd
