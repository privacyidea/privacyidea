#!/bin/bash
#
# 2018-07-31 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
# Copyright (c) 2018, Cornelius Kölbel
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

if [ "$1" == "" ]; then
	echo
	echo "Please specify the pi.cfg file!"
	echo
	exit 1
else
	PICFG=$1
fi

tempfile=`mktemp --suff=.diag`

log() {
	echo $1 >> $tempfile
}

get_os() {
	log
	log "Linux Distribution"
	log "=================="
	cat /etc/*-release >> $tempfile
}

get_pi_cfg() {
	log
	log "pi.cfg file"
	log "==========="
	grep -v SECRET_KEY $PICFG | grep -v PI_PEPPER | grep -v SQLALCHEMY_DATABASE_URI >> $tempfile
}


upload_info() {
	echo
	echo "Please upload the diagnostics file $tempfile to your support team."
	echo
}

pi_versions() {
	log
	log "privacyIDEA Versions"
	log "===================="
	log "Is this Ubuntu?"
	log "---------------"
	dpkg -l | grep privacyidea >> $tempfile
	dpkg -l | grep apache >> $tempfile
	dpkg -l | grep nginx >> $tempfile
	log "Is this CentOS/RHEL?"
	log "--------------------"
	rpm -qa | grep privacyidea >> $tempfile
	rpm -qa | grep httpd >> $tempfile
	rpm -qa | grep nginx >> $tempfile
	log "Is this a pip installation?"
	log "---------------------------"
	log "The contents of /opt/:"
	ls -l /opt >> $tempfile
	log "Can we do a pip freeze?"
	pip freeze >> $tempfile
}

pi_config() {
	log
	log "privacyIDEA Configuration"
	log "========================="
	log "Resolvers"
	log "---------"
	pi-manage resolver list >> $tempfile
	log "Realms"
	log "------"
	pi-manage realm list >> $tempfile
	log "Events"
	log "------"
	pi-manage event e_export >> $tempfile
	log "Policies"
	log "--------"
	pi-manage policy p_export >> $tempfile
}


pi_logfile() {
	log
	log "privacyIDEA Logfile"
	log "==================="
	R=`grep "PI_LOGFILE" $PICFG | cut -d "=" -f2 | sed -e s/\"//g | sed -e s/\'//g`
	cat $R >> $tempfile
}

get_os
get_pi_cfg
pi_versions
pi_config
pi_logfile
#pi_auditlog
upload_info
