/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2016-05-07 Cornelius Kölbel <cornelius@privacyidea.org>
 *     Add state for event handler
 * 2015-12-18 Cornelius Kölbel <cornelius@privacyidea.org>
 *     Add state for SMTP Servers
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

angular.module('privacyideaApp.configStates', ['ui.router']).config(
    ['$stateProvider',
        function ($stateProvider) {
            // get the instance, the pathname part
            var instance = window.location.pathname;
            if (instance === "/") {
               instance = "";
            }
            var configpath = instance + "/static/components/config/views/";
            $stateProvider
                .state('config', {
                    url: "/config",
                    templateUrl: configpath + "config.html"
                })
                .state('config.resolvers', {
                    url: "/resolvers",
                    templateUrl: configpath + "config.resolvers.html"
                })
                .state('config.resolvers.list', {
                    url: "/list",
                    templateUrl: configpath + "config.resolvers.list.html"
                })
                .state('config.resolvers.addpasswdresolver', {
                    // Create a new resolver
                    url: "/passwd",
                    templateUrl: configpath + "config.resolvers.passwd.html"
                })
                .state('config.resolvers.editpasswdresolver', {
                    // edit an existing resolver
                    url: "/passwd/{resolvername:.*}",
                    templateUrl: configpath + "config.resolvers.passwd.html"
                })
                .state('config.resolvers.addldapresolver', {
                    url: "/ldap",
                    templateUrl: configpath + "config.resolvers.ldap.html"
                })
                .state('config.resolvers.editldapresolver', {
                    url: "/ldap/{resolvername:.*}",
                    templateUrl: configpath + "config.resolvers.ldap.html"
                })
                .state('config.resolvers.addscimresolver', {
                    url: "/scim",
                    templateUrl: configpath + "config.resolvers.scim.html"
                })
                .state('config.resolvers.editscimresolver', {
                    url: "/scim/{resolvername:.*}",
                    templateUrl: configpath + "config.resolvers.scim.html"
                })
                .state('config.resolvers.addsqlresolver', {
                    url: "/ldap",
                    templateUrl: configpath + "config.resolvers.sql.html"
                })
                .state('config.resolvers.editsqlresolver', {
                    url: "/ldap/{resolvername:.*}",
                    templateUrl: configpath + "config.resolvers.sql.html"
                })
                .state('config.caconnectors', {
                    url: "/caconnectors",
                    templateUrl: configpath + "config.caconnectors.html"
                })
                .state('config.caconnectors.list', {
                    url: "/list",
                    templateUrl: configpath + "config.caconnectors.list.html"
                })
                .state('config.caconnectors.addlocal', {
                    url: "/local",
                    templateUrl: configpath + "config.caconnectors.local.html"
                })
                .state('config.caconnectors.editlocal', {
                    url: "/local/{connectorname:.*}",
                    templateUrl: configpath + "config.caconnectors.local.html"
                })
                .state('config.mresolvers', {
                    url: "/machineresolvers",
                    templateUrl: configpath + "config.machineresolvers.html"
                })
                .state('config.mresolvers.list', {
                    url: "/list",
                    templateUrl: configpath + "config.mresolvers.list.html"
                })
                .state('config.mresolvers.addhosts', {
                    // Create a new resolver
                    url: "/hosts",
                    templateUrl: configpath + "config.mresolvers.hosts.html"
                })
                .state('config.mresolvers.edithosts', {
                    // edit an existing resolver
                    url: "/hosts/{resolvername:.*}",
                    templateUrl: configpath + "config.mresolvers.hosts.html"
                })
                .state('config.mresolvers.addldap', {
                    // Create a new resolver
                    url: "/ldap",
                    templateUrl: configpath + "config.mresolvers.ldap.html"
                })
                .state('config.mresolvers.editldap', {
                    // edit an existing resolver
                    url: "/ldap/{resolvername:.*}",
                    templateUrl: configpath + "config.mresolvers.ldap.html"
                })
                .state('config.system', {
                    url: "/system",
                    templateUrl: configpath + "config.system.html"
                })
                .state('config.sysdoc', {
                    url: "/system/documentation",
                    templateUrl: configpath + "config.system.html"
                })
                .state('config.policies', {
                    url: "/policies",
                    templateUrl: configpath + "config.policies.html"
                })
                .state('config.policies.list', {
                    url: "/list",
                    templateUrl: configpath + "config.policies.list.html"
                })
                .state('config.policies.details', {
                    url: "/details/{policyname:.*}",
                    templateUrl: configpath + "config.policies.details.html",
                    controller: "policyDetailsController"
                })
                .state('config.tokens', {
                    url: "/tokens/{tokentype:.*}",
                    templateUrl: configpath + "config.tokens.html",
                    controller: "tokenConfigController"
                })
//                .state('config.machines', {
//                    url: "/machines",
//                    templateUrl: path + "config.machines.html"
//                })
                .state('config.realms', {
                    url: "/realms",
                    templateUrl: configpath + "config.realms.html"
                })
                .state('config.realms.list', {
                    url: "/list",
                    templateUrl: configpath + "config.realms.list.html"
                })
                .state('config.smtp', {
                    url: "/smtp",
                    templateUrl: configpath + "config.smtp.html",
                    controller: "smtpServerController"
                })
                .state('config.smtp.list', {
                    url: "/list",
                    templateUrl: configpath + "config.smtp.list.html",
                    controller: "smtpServerController"
                })
                .state('config.smtp.edit', {
                    url: "/edit/{identifier:.*}",
                    templateUrl: configpath + "config.smtp.edit.html",
                    controller: "smtpServerController"
                })
                .state('config.smsgateway', {
                    url: "/smsgateway",
                    templateUrl: configpath + "config.smsgateway.html",
                    controller: "smsgatewayController"
                })
                .state('config.smsgateway.list', {
                    url: "/list",
                    templateUrl: configpath + "config.smsgateway.list.html",
                    controller: "smsgatewayController"
                })
                .state('config.smsgateway.edit', {
                    url: "/edit/{gateway_id:.*}",
                    templateUrl: configpath + "config.smsgateway.edit.html",
                    controller: "smsgatewayController"
                })
                .state('config.radius', {
                    url: "/radius",
                    templateUrl: configpath + "config.radius.html",
                    controller: "radiusServerController"
                })
                .state('config.radius.list', {
                    url: "/list",
                    templateUrl: configpath + "config.radius.list.html",
                    controller: "radiusServerController"
                })
                .state('config.radius.edit', {
                    url: "/edit/{identifier:.*}",
                    templateUrl: configpath + "config.radius.edit.html",
                    controller: "radiusServerController"
                })
                .state('config.privacyideaserver', {
                    url: "/privacyideaserver",
                    templateUrl: configpath + "config.privacyideaserver.html",
                    controller: "privacyideaServerController"
                })
                .state('config.privacyideaserver.list', {
                    url: "/list",
                    templateUrl: configpath + "config.privacyideaserver.list.html",
                    controller: "privacyideaServerController"
                })
                .state('config.privacyideaserver.edit', {
                    url: "/edit/{identifier:.*}",
                    templateUrl: configpath + "config.privacyideaserver.edit.html",
                    controller: "privacyideaServerController"
                })
                .state('config.events', {
                    url: "/events",
                    templateUrl: configpath + "config.events.html",
                    controller: "eventController"
                })
                .state('config.events.details', {
                    url: "/details/{eventid:.*}",
                    templateUrl: configpath + "config.events.details.html",
                    controller: "eventDetailController"
                })
                .state('config.events.list', {
                    url: "/list",
                    templateUrl: configpath + "config.events.list.html",
                    controller: "eventController"
                })
                .state('config.periodictasks', {
                    url: "/periodictasks",
                    templateUrl: configpath + "config.periodictasks.html",
                    controller: "periodicTaskController"
                })
                .state('config.periodictasks.list', {
                    url: "/list",
                    templateUrl: configpath + "config.periodictasks.list.html",
                    controller: "periodicTaskController"
                })
                .state('config.periodictasks.details', {
                    url: "/details/{ptaskid:.*}",
                    templateUrl: configpath + "config.periodictasks.details.html",
                    controller: "periodicTaskDetailController"
                })
            ;
        }]);
