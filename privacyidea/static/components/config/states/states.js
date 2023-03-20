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

angular.module('privacyideaApp.configStates', ['ui.router', 'privacyideaApp.versioning']).config(
    ['$stateProvider', 'versioningSuffixProviderProvider',
        function ($stateProvider, versioningSuffixProviderProvider) {
            // get the instance, the pathname part
            var instance = window.location.pathname;
            if (instance === "/") {
               instance = "";
            }
            var configpath = instance + "/static/components/config/views/";
            $stateProvider
                .state('config', {
                    url: "/config",
                    templateUrl: configpath + "config.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers', {
                    url: "/resolvers",
                    templateUrl: configpath + "config.resolvers.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers.list', {
                    url: "/list",
                    templateUrl: configpath + "config.resolvers.list.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers.addpasswdresolver', {
                    // Create a new resolver
                    url: "/passwd",
                    templateUrl: configpath + "config.resolvers.passwd.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers.editpasswdresolver', {
                    // edit an existing resolver
                    url: "/passwd/:resolvername",
                    templateUrl: configpath + "config.resolvers.passwd.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers.addhttpresolver', {
                    url: "/httpresolver",
                    templateUrl: configpath + "config.resolvers.http.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers.edithttpresolver', {
                    url: "/httpresolver/:resolvername",
                    templateUrl: configpath + "config.resolvers.http.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers.addldapresolver', {
                    url: "/ldap",
                    templateUrl: configpath + "config.resolvers.ldap.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers.editldapresolver', {
                    url: "/ldap/:resolvername",
                    templateUrl: configpath + "config.resolvers.ldap.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers.addscimresolver', {
                    url: "/scim",
                    templateUrl: configpath + "config.resolvers.scim.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers.editscimresolver', {
                    url: "/scim/:resolvername",
                    templateUrl: configpath + "config.resolvers.scim.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers.addsqlresolver', {
                    url: "/ldap",
                    templateUrl: configpath + "config.resolvers.sql.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.resolvers.editsqlresolver', {
                    url: "/ldap/:resolvername",
                    templateUrl: configpath + "config.resolvers.sql.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.caconnectors', {
                    url: "/caconnectors",
                    templateUrl: configpath + "config.system.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "CAConnectorController"
                })
                .state('config.caconnectors.list', {
                    url: "/list",
                    templateUrl: configpath + "config.caconnectors.list.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "CAConnectorController"
                })
                .state('config.caconnectors.addlocal', {
                    url: "/local",
                    templateUrl: configpath + "config.caconnectors.local.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "CAConnectorController"
                })
                .state('config.caconnectors.editlocal', {
                    url: "/local/:connectorname",
                    templateUrl: configpath + "config.caconnectors.local.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "CAConnectorController"
                })
                .state('config.caconnectors.addmicrosoft', {
                    url: "/microsoft",
                    templateUrl: configpath + "config.caconnectors.microsoft.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "CAConnectorController"
                })
                .state('config.caconnectors.editmicrosoft', {
                    url: "/microsoft/:connectorname",
                    templateUrl: configpath + "config.caconnectors.microsoft.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "CAConnectorController"
                })
                .state('config.mresolvers', {
                    url: "/machineresolvers",
                    templateUrl: configpath + "config.machineresolvers.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.mresolvers.list', {
                    url: "/list",
                    templateUrl: configpath + "config.mresolvers.list.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.mresolvers.addhosts', {
                    // Create a new resolver
                    url: "/hosts",
                    templateUrl: configpath + "config.mresolvers.hosts.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.mresolvers.edithosts', {
                    // edit an existing resolver
                    url: "/hosts/:resolvername",
                    templateUrl: configpath + "config.mresolvers.hosts.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.mresolvers.addldap', {
                    // Create a new resolver
                    url: "/ldap",
                    templateUrl: configpath + "config.mresolvers.ldap.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.mresolvers.editldap', {
                    // edit an existing resolver
                    url: "/ldap/:resolvername",
                    templateUrl: configpath + "config.mresolvers.ldap.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.system', {
                    url: "/system",
                    templateUrl: configpath + "config.system.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.system.edit', {
                    url: "/edit",
                    templateUrl: configpath + "config.system.edit.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.system.doc', {
                    url: "/documentation",
                    templateUrl: configpath + "config.system.doc.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.policies', {
                    url: "/policies",
                    templateUrl: configpath + "config.policies.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.policies.list', {
                    url: "/list",
                    templateUrl: configpath + "config.policies.list.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.policies.details', {
                    url: "/details/:policyname",
                    templateUrl: configpath + "config.policies.details.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "policyDetailsController",
                    params: { policyname: null },
                })
                .state('config.policies.add', {
                    url: "/details/",
                    templateUrl: configpath + "config.policies.details.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "policyDetailsController"
                })
                .state('config.tokens', {
                    url: "/tokens/:tokentype",
                    templateUrl: configpath + "config.tokens.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokenConfigController",
                    params: { tokentype: null },
                })
//                .state('config.machines', {
//                    url: "/machines",
//                    templateUrl: path + "config.machines.html" + versioningSuffixProviderProvider.$get().$get()
//                })
                .state('config.realms', {
                    url: "/realms",
                    templateUrl: configpath + "config.realms.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.realms.list', {
                    url: "/list",
                    templateUrl: configpath + "config.realms.list.html" + versioningSuffixProviderProvider.$get().$get()
                })
                .state('config.smtp', {
                    url: "/smtp",
                    templateUrl: configpath + "config.system.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "smtpServerController"
                })
                .state('config.smtp.list', {
                    url: "/list",
                    templateUrl: configpath + "config.smtp.list.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "smtpServerController"
                })
                .state('config.smtp.edit', {
                    url: "/edit/:identifier",
                    templateUrl: configpath + "config.smtp.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "smtpServerController"
                })
                .state('config.smtp.add', {
                    url: "/edit/",
                    templateUrl: configpath + "config.smtp.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "smtpServerController"
                })
                .state('config.smsgateway', {
                    url: "/smsgateway",
                    templateUrl: configpath + "config.system.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "smsgatewayController"
                })
                .state('config.smsgateway.list', {
                    url: "/list",
                    templateUrl: configpath + "config.smsgateway.list.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "smsgatewayController"
                })
                .state('config.smsgateway.edit', {
                    url: "/edit/:gateway_id",
                    templateUrl: configpath + "config.smsgateway.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "smsgatewayController"
                })
                .state('config.smsgateway.add', {
                    url: "/edit/",
                    templateUrl: configpath + "config.smsgateway.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "smsgatewayController"
                })
                .state('config.radius', {
                    url: "/radius",
                    templateUrl: configpath + "config.system.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "radiusServerController"
                })
                .state('config.radius.list', {
                    url: "/list",
                    templateUrl: configpath + "config.radius.list.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "radiusServerController"
                })
                .state('config.radius.edit', {
                    url: "/edit/:identifier",
                    templateUrl: configpath + "config.radius.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "radiusServerController"
                })
                .state('config.radius.add', {
                    url: "/edit/",
                    templateUrl: configpath + "config.radius.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "radiusServerController"
                })
                .state('config.tokengroup', {
                    url: "/tokengroup",
                    templateUrl: configpath + "config.system.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokengroupController"
                })
                .state('config.tokengroup.list', {
                    url: "/list",
                    templateUrl: configpath + "config.tokengroup.list.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokengroupController"
                })
                .state('config.tokengroup.edit', {
                    url: "/edit/:groupname",
                    templateUrl: configpath + "config.tokengroup.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokengroupController"
                })
                .state('config.tokengroup.add', {
                    url: "/edit/",
                    templateUrl: configpath + "config.tokengroup.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "tokengroupController"
                })
                .state('config.serviceid', {
                    url: "/serviceid",
                    templateUrl: configpath + "config.system.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "serviceidController"
                })
                .state('config.serviceid.list', {
                    url: "/list",
                    templateUrl: configpath + "config.serviceid.list.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "serviceidController"
                })
                .state('config.serviceid.edit', {
                    url: "/edit/:servicename",
                    templateUrl: configpath + "config.serviceid.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "serviceidController"
                })
                .state('config.serviceid.add', {
                    url: "/edit/",
                    templateUrl: configpath + "config.serviceid.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "serviceidController"
                })
                .state('config.privacyideaserver', {
                    url: "/privacyideaserver",
                    templateUrl: configpath + "config.system.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "privacyideaServerController"
                })
                .state('config.privacyideaserver.list', {
                    url: "/list",
                    templateUrl: configpath + "config.privacyideaserver.list.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "privacyideaServerController"
                })
                .state('config.privacyideaserver.edit', {
                    url: "/edit/:identifier",
                    templateUrl: configpath + "config.privacyideaserver.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "privacyideaServerController"
                })
                .state('config.privacyideaserver.add', {
                    url: "/edit/",
                    templateUrl: configpath + "config.privacyideaserver.edit.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "privacyideaServerController"
                })
                .state('config.events', {
                    url: "/events",
                    templateUrl: configpath + "config.events.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "eventController"
                })
                .state('config.events.details', {
                    url: "/details/:eventid",
                    templateUrl: configpath + "config.events.details.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "eventDetailController"
                })
                .state('config.events.add', {
                    url: "/details/",
                    templateUrl: configpath + "config.events.details.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "eventDetailController"
                })
                .state('config.events.list', {
                    url: "/list",
                    templateUrl: configpath + "config.events.list.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "eventController"
                })
                .state('config.periodictasks', {
                    url: "/periodictasks",
                    templateUrl: configpath + "config.periodictasks.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "periodicTaskController"
                })
                .state('config.periodictasks.list', {
                    url: "/list",
                    templateUrl: configpath + "config.periodictasks.list.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "periodicTaskController"
                })
                .state('config.periodictasks.details', {
                    url: "/details/:ptaskid",
                    templateUrl: configpath + "config.periodictasks.details.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "periodicTaskDetailController"
                })
                .state('config.periodictasks.add', {
                    url: "/details/",
                    templateUrl: configpath + "config.periodictasks.details.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "periodicTaskDetailController"
                })
            ;
        }]);
