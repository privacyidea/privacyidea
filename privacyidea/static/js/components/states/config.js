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
    ['$stateProvider', '$urlRouterProvider',
        function ($stateProvider, $urlRouterProvider) {
            $stateProvider
                .state('config', {
                    url: "/config",
                    templateUrl: "/static/views/config.html"
                })
                .state('config.resolvers', {
                    url: "/resolvers",
                    templateUrl: "/static/views/config.resolvers.html"
                })
                .state('config.resolvers.list', {
                    url: "/list",
                    templateUrl: "/static/views/config.resolvers.list.html"
                })
                .state('config.resolvers.addpasswdresolver', {
                    // Create a new resolver
                    url: "/passwd",
                    templateUrl: "/static/views/config.resolvers.passwd.html"
                })
                .state('config.resolvers.editpasswdresolver', {
                    // edit an existing resolver
                    url: "/passwd/{resolvername:.*}",
                    templateUrl: "/static/views/config.resolvers.passwd.html"
                })
                .state('config.resolvers.addldapresolver', {
                    url: "/ldap",
                    templateUrl: "/static/views/config.resolvers.ldap.html"
                })
                .state('config.resolvers.editldapresolver', {
                    url: "/ldap/{resolvername:.*}",
                    templateUrl: "/static/views/config.resolvers.ldap.html"
                })
                .state('config.resolvers.addsqlresolver', {
                    url: "/ldap",
                    templateUrl: "/static/views/config.resolvers.sql.html"
                })
                .state('config.resolvers.editsqlresolver', {
                    url: "/ldap/{resolvername:.*}",
                    templateUrl: "/static/views/config.resolvers.sql.html"
                })
                .state('config.system', {
                    url: "/system",
                    templateUrl: "/static/views/config.system.html"
                })
                .state('config.tokens', {
                    url: "/tokens/{tokentype:.*}",
                    templateUrl: "/static/views/config.tokens.html"
                })
                .state('config.machines', {
                    url: "/machines",
                    templateUrl: "/static/views/config.machines.html"
                })
                .state('config.realms', {
                    url: "/realms",
                    templateUrl: "/static/views/config.realms.html"
                })
                .state('config.realms.list', {
                    url: "/list",
                    templateUrl: "/static/views/config.realms.list.html"
                })
                .state('offline', {
                    url: "/offline",
                    templatesUrl: "/static/views/offline.html"
                }).state('login', {
                    url: "/login",
                    templateUrl: "/static/views/login.html"
                })
                .state('token', {
                    url: "/token",
                    templateUrl: "/static/views/token.html"
                })
                .state('token.list', {
                    url: "/list",
                    templateUrl: "/static/views/token.list.html",
                    controller: "tokenController"
                })
                .state('token.details', {
                    url: "/details/{tokenSerial:.*}",
                    templateUrl: "/static/views/token.details.html",
                    controller: "tokenDetailController"
                })
                .state('token.enroll', {
                    url: "/enroll/{realmname:.*}/{username:.*}",
                    templateUrl: "/static/views/token.enroll.html",
                    controller: "tokenEnrollController"
                })
                .state('token.import', {
                    url: "/import",
                    templateUrl: "/static/views/token.import.html",
                    controller: "tokenImportController"
                })
                .state('audit', {
                    url: "/audit?serial&user",
                    templateUrl: "/static/views/audit.html",
                    controller: "auditController"
                })
                .state('user', {
                    url: "/user",
                    templateUrl: "/static/views/user.html"
                })
                .state('user.list', {
                    url: "/list",
                    templateUrl: "/static/views/user.list.html"
                })
                .state('user.details', {
                    url: "/details/{realmname:.*}/{username:.*}",
                    templateUrl: "/static/views/user.details.html",
                    controller: ['$scope', '$stateParams',
                        function ($scope, $stateParams) {
                            $scope.username = $stateParams.username;
                            $scope.realmname = $stateParams.realmname;
                        }]
                });

        }]);
