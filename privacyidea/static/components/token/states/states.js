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
            var instance = window.location.pathname;
            if (instance === "/") {
               instance = "";
            }
            var tokenpath = instance + "/static/components/token/views/";
            $stateProvider
                .state('token', {
                    url: "/token",
                    templateUrl: tokenpath + "token.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('token.list', {
                    url: "/list",
                    templateUrl: tokenpath + "token.list.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenController"
                })
                .state('token.assign', {
                    url: "/assign",
                    templateUrl: tokenpath + "token.assign.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenAssignController"
                })
                .state('token.details', {
                    url: "/details/:tokenSerial",
                    templateUrl: tokenpath + "token.details.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenDetailController",
                })
                .state('token.lost', {
                    url: "/lost/:tokenSerial",
                    templateUrl: tokenpath + "token.lost.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenLostController"
                })
                .state('token.getserial', {
                    url: "/getserial",
                    templateUrl: tokenpath + "token.getserial.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenGetSerialController"
                })
                .state('token.enroll', {
                    url: "/enroll/:realmname/:username",
                    templateUrl: tokenpath + "token.enroll.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenEnrollController",
                    params: { realmname: null, username: null },
                })
                .state('token.rollover', {
                    url: "/rollover/:tokenType/:tokenSerial",
                    templateUrl: tokenpath + "token.enroll.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenEnrollController"
                })
                .state('token.wizard', {
                    url: "/wizard",
                    templateUrl: tokenpath + "token.enroll.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenEnrollController"
                })
                .state('token.import', {
                    url: "/import",
                    templateUrl: tokenpath + "token.import.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenImportController"
                })
                .state('token.challenges', {
                    url: "/challenges",
                    templateUrl: tokenpath + "token.challenges.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenChallengesController"
                })
                .state('token.applications', {
                    url: "/applications/:application",
                    templateUrl: tokenpath + "token.applications.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenApplicationsController",
                    params: { "application": "ssh"}
                });
        }]);
