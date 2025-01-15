/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2016-02-05 Cornelius Kölbel <cornelius@privacyidea.org>
 *     Add token enrollment wizard
 * 2015-11-30 Cornelius Kölbel <cornelius@privacyidea.org>
 *     Add view for challenges
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

angular.module('privacyideaApp.tokenStates', ['ui.router', 'privacyideaApp.versioning']).config(
    ['$stateProvider', 'versioningSuffixProviderProvider',
        function ($stateProvider, versioningSuffixProviderProvider) {
            // get the instance, the pathname part
            let instance = window.location.pathname;
            if (instance === "/") {
                instance = "";
            }
            const tokenPath = instance + "/static/components/token/views/";
            $stateProvider
                .state('token', {
                    url: "/token",
                    templateUrl: tokenPath + "token.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenMenuController"
                })
                .state('token.list', {
                    url: "/list",
                    templateUrl: tokenPath + "token.list.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenController"
                })
                .state('token.assign', {
                    url: "/assign",
                    templateUrl: tokenPath + "token.assign.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenAssignController"
                })
                .state('token.details', {
                    url: "/details/:tokenSerial",
                    templateUrl: tokenPath + "token.details.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenDetailController",
                })
                .state('token.lost', {
                    url: "/lost/:tokenSerial",
                    templateUrl: tokenPath + "token.lost.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenLostController"
                })
                .state('token.getserial', {
                    url: "/getserial",
                    templateUrl: tokenPath + "token.getserial.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenGetSerialController"
                })
                .state('token.enroll', {
                    url: "/enroll/:realmname/:username/:containerSerial",
                    templateUrl: tokenPath + "token.enroll.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenEnrollController",
                    params: {realmname: null, username: null, containerSerial: null},
                })
                .state('token.rollover', {
                    url: "/rollover/:tokenType/:tokenSerial",
                    templateUrl: tokenPath + "token.enroll.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenEnrollController"
                })
                .state('token.wizard', {
                    url: "/wizard",
                    templateUrl: tokenPath + "token.enroll.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenEnrollController"
                })
                .state('token.import', {
                    url: "/import",
                    templateUrl: tokenPath + "token.import.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenImportController"
                })
                .state('token.challenges', {
                    url: "/challenges",
                    templateUrl: tokenPath + "token.challenges.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenChallengesController"
                })
                .state('token.applications', {
                    url: "/applications/:application",
                    templateUrl: tokenPath + "token.applications.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenApplicationsController",
                    params: {"application": "ssh"}
                })
                .state('token.containercreate', {
                    url: "/container",
                    templateUrl: tokenPath + "token.containercreate.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "containerCreateController"
                })
                .state('token.containerlist', {
                    url: "/container/list",
                    templateUrl: tokenPath + "token.containerlist.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "containerListController"
                })
                .state('token.containerdetails', {
                    url: "/container/details/:containerSerial",
                    templateUrl: tokenPath + "token.containerdetails.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "containerDetailsController"
                })
        }]);
