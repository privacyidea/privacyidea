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
myApp.factory("PolicyTemplateFactory", ["$http", "inform", "gettextCatalog",
                                        function($http, inform, gettextCatalog){
    var URL = "https://raw.githubusercontent.com/privacyidea/policy-templates/master/templates/";
    return {
        setUrl: function(url) {
            URL = url;
        },
        getTemplates: function(callback) {
            //debug: console.log("Going to fetch Policy Templates");
            $http.get(URL + "index.json")
                .then(function(response) { callback(response.data) }, function (error) {
                    //debug: console.log("Error fetching Policy Templates.");
                    //debug: console.log(error);
                    inform.add(gettextCatalog.getString("Error fetching" +
                        " policy templates."),
                                {type: "danger", ttl:10000});
            });
        },
        getTemplate: function(templateName, callback) {
            //debug: console.log("Going to fetch Policy Template " + templateName);
            $http.get(URL + templateName + ".json")
                .then(function(response) { callback(response.data) }, function (error) {
                    //debug: console.log(error);
                    inform.add(gettextCatalog.getString("Error fetching" +
                            " policy template ")
                        + templateName,
                                {type: "danger", ttl:10000});
            });
        }
    };
}]);

myApp.factory("ConfigFactory", ["AuthFactory", "$http", "$state", "$rootScope",
                                "resolverUrl", "realmUrl", "machineResolverUrl",
                                "policyUrl", "eventUrl", "smtpServerUrl",
                                "radiusServerUrl", "smsgatewayUrl",
                                "defaultRealmUrl", "systemUrl", "periodicTaskUrl",
                                "privacyideaServerUrl", "CAConnectorUrl", "tokengroupUrl",
                                "serviceidUrl",
                                function (AuthFactory, $http, $state, $rootScope,
                                          resolverUrl, realmUrl, machineResolverUrl,
                                          policyUrl, eventUrl, smtpServerUrl,
                                          radiusServerUrl, smsgatewayUrl,
                                          defaultRealmUrl, systemUrl,
                                          periodicTaskUrl, privacyideaServerUrl,
                                          CAConnectorUrl, tokengroupUrl, serviceidUrl) {
    /**
     Each service - just like this service factory - is a singleton.
     */
    return {
        getPGPKeys: function(callback) {
            $http.get(systemUrl + "/gpgkeys", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getSMSProviders: function(callback) {
            $http.get(smsgatewayUrl + "/providers", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getSMSGateways: function(gwid, callback) {
            if(!gwid) {gwid = "";}
            $http.get(smsgatewayUrl + "/" + gwid, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        setSMSGateway: function(params, callback) {
            $http.post(smsgatewayUrl, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delSMSGateway: function(name, callback) {
            $http.delete(smsgatewayUrl+ "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delEvent: function(eventId, callback) {
            $http.delete(eventUrl + "/" + eventId, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        enableEvent: function(eventId, callback) {
            $http.post(eventUrl + "/enable/" + eventId, {},
                {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        disableEvent: function(eventId, callback) {
            $http.post(eventUrl + "/disable/" + eventId, {},
                {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        setEvent: function(params, callback) {
            $http.post(eventUrl, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getEvents: function(callback) {
            $http.get(eventUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getEvent: function(eventid, callback) {
            $http.get(eventUrl + "/" + eventid, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getHandlerActions: function(handlername, callback) {
            $http.get(eventUrl + "/actions/" + handlername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getHandlerConditions: function(handlername, callback) {
            $http.get(eventUrl + "/conditions/" + handlername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getHandlerPositions: function(handlername, callback) {
            $http.get(eventUrl + "/positions/" + handlername, {
              headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delPeriodicTask: function (ptaskid, callback) {
            $http.delete(periodicTaskUrl + "/" + ptaskid, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getPeriodicTasks: function(callback) {
            $http.get(periodicTaskUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getPeriodicTaskmodules: function(callback) {
            $http.get(periodicTaskUrl + "/taskmodules/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getPeriodicTaskmoduleOptions: function(taskmodule, callback) {
            $http.get(periodicTaskUrl + "/options/" + taskmodule, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getPeriodicTask: function(ptaskid, callback) {
            $http.get(periodicTaskUrl + "/" + ptaskid, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        setPeriodicTask: function(params, callback) {
            $http.post(periodicTaskUrl + "/", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        enablePeriodicTask: function(ptaskid, callback) {
            $http.post(periodicTaskUrl + "/enable/" + ptaskid, {},
                { headers: {'PI-Authorization': AuthFactory.getAuthToken()} }
            ).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        disablePeriodicTask: function(ptaskid, callback) {
            $http.post(periodicTaskUrl + "/disable/" + ptaskid, {},
                { headers: {'PI-Authorization': AuthFactory.getAuthToken()} }
            ).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getNodes: function(callback) {
            $http.get(periodicTaskUrl + "/nodes/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delPolicy: function (policyName, callback) {
            $http.delete(policyUrl + "/" + policyName, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        setPolicy: function (policyName, params, callback) {
            $http.post(policyUrl + "/" + policyName, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getPolicies: function (callback) {
            $http.get(policyUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getPolicy: function (policyname, callback) {
            $http.get(policyUrl + "/" + policyname, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        enablePolicy: function (policyname, callback) {
            $http.post(policyUrl + "/enable/" + policyname, {}, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        disablePolicy: function (policyname, callback) {
            $http.post(policyUrl + "/disable/" + policyname, {}, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getPolicyDefs: function (callback) {
            // Return the policy definitions
            $http.get(policyUrl + "/defs", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getPolicyConditionDefs: function (callback) {
            // Return the definitions for policy conditions
            $http.get(policyUrl + "/defs/conditions", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getPINodes: function (callback) {
            // Return the definitions for policy conditions
            $http.get(policyUrl + "/defs/pinodes", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getResolvers: function (callback) {
            $http.get(resolverUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getEditableResolvers: function (callback) {
            $http.get(resolverUrl + "/?editable=1", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getResolver: function(resolvername, callback) {
            $http.get(resolverUrl + "/" + resolvername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getMachineResolver: function (resolvername, callback) {
            $http.get(machineResolverUrl + "/" + resolvername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getMachineResolvers: function (callback) {
            $http.get(machineResolverUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getCAConnectors: function (callback) {
            $http.get(CAConnectorUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getCAConnectorNames: function (callback) {
            $http.get(systemUrl + "/names/caconnector", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getCAConnector: function (connectorname, callback) {
            $http.get(CAConnectorUrl + "/" + connectorname, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getRealms: function (callback) {
            $http.get(realmUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getAdminRealms: function(callback) {
            $http.get(realmUrl + "/superuser", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        setResolver: function (name, params, callback) {
            $http.post(resolverUrl + "/" + name, params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
                }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        setMachineResolver: function (name, params, callback) {
            $http.post(machineResolverUrl + "/" + name, params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}
                }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        setCAConnector: function(name, params, callback) {
            $http.post(CAConnectorUrl + "/" + name, params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}
                }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getCASpecificOptions: function(catype, params, callback) {
            //encodeURI("/random?len=" + len + "&encode=" + encode)
            var pstring = new URLSearchParams(params).toString()
            $http.get(CAConnectorUrl + "/specific/" + catype + "?" + pstring,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        testResolver: function (params, callback) {
            $http.post(resolverUrl + "/test", params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}
                }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        testMachineResolver: function (params, callback) {
            $http.post(machineResolverUrl + "/test", params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}
                }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delResolver: function(name, callback) {
            $http.delete(resolverUrl + "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken() }
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });

        },
        delMachineResolver: function(name, callback) {
            $http.delete(machineResolverUrl + "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken() }
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });

        },
        delCAConnector: function(name, callback) {
            $http.delete(CAConnectorUrl + "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken() }
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        setRealm: function(name, params, callback) {
            $http.post(realmUrl + "/" + name, params, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delRealm: function(name, callback) {
            $http.delete(realmUrl +  "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        setDefaultRealm: function(name, callback) {
            $http.post(defaultRealmUrl + "/" + name, {},
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) })
        },
        clearDefaultRealm: function(callback) {
            $http.delete(defaultRealmUrl, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getDocumentation: function(callback) {
            $http.get(systemUrl + "/documentation", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        saveSystemConfig: function(params, callback) {
            $http.post(systemUrl + "/setConfig", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delSystemConfig: function(key, callback) {
            $http.delete(systemUrl + "/" + key, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getRandom: function(len, encode, callback) {
            $http.get(systemUrl +
                encodeURI("/random?len=" + len + "&encode=" + encode), {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        testTokenConfig: function(tokentype, params, callback) {
            $http.post(systemUrl + "/test/" + tokentype, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        loadSystemConfig: function(callback, key) {
            if (!key) {key = "";}
            $http.get(systemUrl + "/" + key, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getSystemConfig: function(callback) {
            $http.get(systemUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getSmtp: function(callback, identifier) {
            if (!identifier) {identifier = "";}
            $http.get(smtpServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delSmtp: function(identifier, callback) {
            $http.delete(smtpServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        addSmtp: function(params, callback) {
            var identifier = params["identifier"];
            $http.post(smtpServerUrl + "/" + identifier, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        testSmtp: function(params, callback) {
            $http.post(smtpServerUrl + "/send_test_email", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getRadius: function(callback, identifier) {
            if (!identifier) {identifier = "";}
            $http.get(radiusServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getRadiusNames: function(callback) {
            $http.get(systemUrl + "/names/radius", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delRadius: function(identifier, callback) {
            $http.delete(radiusServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        addRadius: function(params, callback) {
            var identifier = params["identifier"];
            $http.post(radiusServerUrl + "/" + identifier, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        testRadius: function(params, callback) {
            $http.post(radiusServerUrl + "/test_request", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getTokengroup: function(groupname, callback) {
            $http.get(tokengroupUrl + "/" + groupname, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        addTokengroup: function(params, callback) {
            $http.post(tokengroupUrl + "/" + params["groupname"], params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delTokengroup: function(groupname, callback) {
            $http.delete(tokengroupUrl + "/" + groupname, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getServiceid: function(sname, callback) {
            $http.get(serviceidUrl + "/" + sname, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        addServiceid: function(params, callback) {
            $http.post(serviceidUrl + "/" + params["servicename"], params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delServiceid: function(sname, callback) {
            $http.delete(serviceidUrl + "/" + sname, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        getPrivacyidea: function(callback, identifier) {
            if (!identifier) {identifier = "";}
            $http.get(privacyideaServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        delPrivacyidea: function(identifier, callback) {
            $http.delete(privacyideaServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        addPrivacyidea: function(params, callback) {
            var identifier = params["identifier"];
            $http.post(privacyideaServerUrl + "/" + identifier, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        },
        testPrivacyidea: function(params, callback) {
            $http.post(privacyideaServerUrl + "/test_request", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).then(function(response) { callback(response.data) }, function(error) { AuthFactory.authError(error.data) });
        }
    };
}]);
