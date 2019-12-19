/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2018-11-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *            Remove audit based statistics
 * 2015-07-16 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *     Add state for audit.log and audit.stats
 * 2015-01-11 Cornelius Kölbel, <cornelius@privacyidea.org>
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

angular.module('privacyideaApp.auditStates', ['ui.router', 'privacyideaApp.versioning']).config(
    ['$stateProvider', 'versioningSuffixProviderProvider',
        function ($stateProvider, versioningSuffixProviderProvider) {
            // get the instance, the pathname part
            var instance = window.location.pathname;
            if (instance === "/") {
               instance = "";
            }
            var auditpath = instance + "/static/components/audit/views/";
            $stateProvider
                .state('audit', {
                    url: "/audit",
                    templateUrl: auditpath + "audit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "auditController"
                })
                .state('audit.log', {
                    url: "/log?serial&user",
                    templateUrl: auditpath + "audit.log.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "auditController"
                });
        }]);
