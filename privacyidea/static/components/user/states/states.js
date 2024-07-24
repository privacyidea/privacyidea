/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
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

angular.module('privacyideaApp.userStates', ['ui.router', 'privacyideaApp.versioning']).config(
    ['$stateProvider', 'versioningSuffixProviderProvider',
        function ($stateProvider, versioningSuffixProviderProvider) {
            // get the instance, the pathname part
            var instance = window.location.pathname;
            if (instance === "/") {
               instance = "";
            }
            var userpath = instance + "/static/components/user/views/";
            $stateProvider
                .state('user', {
                    url: "/user",
                    templateUrl: userpath + "user.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "userController"
                })
                .state('user.list', {
                    url: "/list",
                    templateUrl: userpath + "user.list.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('user.details', {
                    url: "/details/{realmname:.*}/{username:.*}",
                    templateUrl: userpath + "user.details.html" + versioningSuffixProviderProvider.$get().$get(),
                    params: {resolvername: null,
                             editable: null},
                    controller: "userDetailsController"
                })
                .state('user.password', {
                    url: "/password",
                    templateUrl: userpath + "user.password.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "userPasswordController"
                })
                .state('user.add', {
                    url: "/add",
                    templateUrl: userpath + "user.add.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "userAddController"
                });
        }]);
