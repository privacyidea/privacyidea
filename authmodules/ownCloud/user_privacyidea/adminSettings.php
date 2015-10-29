<?php

/**
 * privacyidea authentication module for ownCloud
 * See https://www.privacyidea.org
 *
 * 2015-10-26 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *            Use privacyIDEA realm
 * 2015-06-24 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *            initial writeup
 *
 *    This program is free software: you can redistribute it and/or
 *    modify it under the terms of the GNU Affero General Public
 *    License, version 3, as published by the Free Software Foundation.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU Affero General Public License for more details.
 *
 *    You should have received a copy of the
 *               GNU Affero General Public License
 *    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 *
 */

# Only Admin users may call this
OC_Util::checkAdminUser();
# Add the javascript js/adminSettings.js
\OCP\Util::addScript('user_privacyidea', 'adminSettings');

# get the config helper object
$helper = new \OCA\user_privacyidea\lib\Helper();

# Set the template templates/adminSettings.php
$tmpl = new OCP\Template('user_privacyidea', 'adminSettings');

# Read values from configuration
$tmpl->assign('enable_privacyidea', $helper->is_privacyidea_enabled());
$tmpl->assign('verify_ssl', $helper->is_ssl_check());
$tmpl->assign('allow_normal_login', $helper->is_normal_login_allowed());
$tmpl->assign('allow_api', $helper->is_api_allowed());

$url = $helper->get_url();
$tmpl->assign('privacyidea_url', $url);

$realm = $helper->get_realm();
$tmpl->assign('realm', $realm);

$proxy = $helper->get_proxy();
$tmpl->assign('privacyidea_proxy', $proxy);

\OCP\Util::writeLog('user_privacyidea', "Setting URL: $url", OCP\Util::DEBUG);
return $tmpl->fetchPage();
