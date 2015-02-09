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

angular.module('privacyideaApp.config', ['ui.router']).config(
    ['$stateProvider', '$urlRouterProvider', '$locationProvider',
        function ($stateProvider, $urlRouterProvider) {
            // get the instance, the pathname part
            var instance = window.location.pathname;
            if (instance == "/") {
               instance = "";
            }
            var path = instance + "/static/views/";
            $stateProvider
                .state('config', {
                    url: "/config",
                    templateUrl: path + "config.html"
                })
                .state('config.resolvers', {
                    url: "/resolvers",
                    templateUrl: path + "config.resolvers.html"
                })
                .state('config.resolvers.list', {
                    url: "/list",
                    templateUrl: path + "config.resolvers.list.html"
                })
                .state('config.resolvers.addpasswdresolver', {
                    // Create a new resolver
                    url: "/passwd",
                    templateUrl: path + "config.resolvers.passwd.html"
                })
                .state('config.resolvers.editpasswdresolver', {
                    // edit an existing resolver
                    url: "/passwd/{resolvername:.*}",
                    templateUrl: path + "config.resolvers.passwd.html"
                })
                .state('config.resolvers.addldapresolver', {
                    url: "/ldap",
                    templateUrl: path + "config.resolvers.ldap.html"
                })
                .state('config.resolvers.editldapresolver', {
                    url: "/ldap/{resolvername:.*}",
                    templateUrl: path + "config.resolvers.ldap.html"
                })
                .state('config.resolvers.addsqlresolver', {
                    url: "/ldap",
                    templateUrl: path + "config.resolvers.sql.html"
                })
                .state('config.resolvers.editsqlresolver', {
                    url: "/ldap/{resolvername:.*}",
                    templateUrl: path + "config.resolvers.sql.html"
                })
                .state('config.system', {
                    url: "/system",
                    templateUrl: path + "config.system.html"
                })
                .state('config.policies', {
                    url: "/policies",
                    templateUrl: path + "config.policies.html"
                })
                .state('config.policies.list', {
                    url: "/list",
                    templateUrl: path + "config.policies.list.html"
                })
                .state('config.policies.details', {
                    url: "/details/{policyname:.*}",
                    templateUrl: path + "config.policies.details.html",
                    controller: "policyDetailsController"
                })
                .state('config.tokens', {
                    url: "/tokens/{tokentype:.*}",
                    templateUrl: path + "config.tokens.html"
                })
                .state('config.machines', {
                    url: "/machines",
                    templateUrl: path + "config.machines.html"
                })
                .state('config.realms', {
                    url: "/realms",
                    templateUrl: path + "config.realms.html"
                })
                .state('config.realms.list', {
                    url: "/list",
                    templateUrl: path + "config.realms.list.html"
                })
                .state('offline', {
                    url: "/offline",
                    templatesUrl: path + "offline.html"
                }).state('login', {
                    url: "/login",
                    templateUrl: path + "login.html"
                })
                .state('token', {
                    url: "/token",
                    templateUrl: path + "token.html"
                })
                .state('token.list', {
                    url: "/list",
                    templateUrl: path + "token.list.html",
                    controller: "tokenController"
                })
                .state('token.details', {
                    url: "/details/{tokenSerial:.*}",
                    templateUrl: path + "token.details.html",
                    controller: "tokenDetailController"
                })
                .state('token.enroll', {
                    url: "/enroll/{realmname:.*}/{username:.*}",
                    templateUrl: path + "token.enroll.html",
                    controller: "tokenEnrollController"
                })
                .state('token.import', {
                    url: "/import",
                    templateUrl: path + "token.import.html",
                    controller: "tokenImportController"
                })
                .state('audit', {
                    url: "/audit?serial&user",
                    templateUrl: path + "audit.html",
                    controller: "auditController"
                })
                .state('user', {
                    url: "/user",
                    templateUrl: path + "user.html"
                })
                .state('user.list', {
                    url: "/list",
                    templateUrl: path + "user.list.html"
                })
                .state('user.details', {
                    url: "/details/{realmname:.*}/{username:.*}",
                    templateUrl: path + "user.details.html",
                    controller: ['$scope', '$stateParams',
                        function ($scope, $stateParams) {
                            $scope.username = $stateParams.username;
                            $scope.realmname = $stateParams.realmname;
                        }]
                });

        }]);
