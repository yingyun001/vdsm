#
# Copyright 2013 Red Hat, Inc.
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
SUBDIRS=configurators

include $(top_srcdir)/build-aux/Makefile.subs

EXTRA_DIST = \
	validate_ovirt_certs.py.in \
	$(NULL)

nodist_vdsmtool_PYTHON = \
	validate_ovirt_certs.py \
	$(NULL)

dist_vdsmtool_PYTHON = \
	__init__.py \
	dummybr.py \
	dump_bonding_opts.py \
	dump_volume_chains.py \
	nwfilter.py \
	configfile.py \
	configurator.py \
	register.py \
	restore_nets.py \
	service.py \
	transient.py \
	unified_persistence.py \
	upgrade.py \
	vdsm-id.py \
	$(NULL)

CLEANFILES = \
	config.log \
	$(nodist_vdsmtool_PYTHON) \
	$(nodist_vdsmexec_SCRIPTS) \
	$(NULL)

all-local: \
	$(nodist_vdsmtool_PYTHON) \
	$(nodist_vdsmexec_SCRIPTS) \
	$(NULL)
