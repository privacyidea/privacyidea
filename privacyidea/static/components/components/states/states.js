/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2016-09-01  Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *             Add component. Move from client application type
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

angular.module('privacyideaApp.componentStates', ['ui.router']).config(
    ['$stateProvider',
        function ($stateProvider) {
            // get the instance, the pathname part
            var instance = window.location.pathname;
            if (instance === "/") {
               instance = "";
            }
            var auditpath = instance + "/static/components/components/views/";
            $stateProvider
                .state('component', {
                    url: "/component",
                    templateUrl: auditpath + "component.html",
                    controller: "componentController"
                })
                .state('component.clienttype', {
                    url: "/clienttype",
                    templateUrl: auditpath + "component.clienttype.html",
                    controller: "componentController"
                })
                .state('component.subscriptions', {
                    url: "/subscriptions",
                    templateUrl: auditpath + "component.subscriptions.html",
                    controller: "componentController"
                })
            ;
        }]);
