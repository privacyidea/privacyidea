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
myApp.factory("PolicyTemplateFactory", function($http, inform, gettextCatalog){
    var URL = "https://raw.githubusercontent.com/privacyidea/policy-templates/master/templates/";
    return {
        setUrl: function(url) {
            URL = url;
        },
        getTemplates: function(callback) {
            //debug: console.log("Going to fetch Policy Templates");
            $http.get(URL + "index.json")
                .success(callback).error(function (error) {
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
                .success(callback).error(function (error) {
                    //debug: console.log(error);
                    inform.add(gettextCatalog.getString("Error fetching" +
                            " policy template ")
                        + templateName,
                                {type: "danger", ttl:10000});
            });
        }
    };
});
myApp.factory("ConfigFactory", function (AuthFactory, $http, $state, $rootScope,
                                         resolverUrl, realmUrl,
                                         machineResolverUrl,
                                         policyUrl, eventUrl, smtpServerUrl,
                                         radiusServerUrl, smsgatewayUrl,
                                         defaultRealmUrl, systemUrl,
                                         periodicTaskUrl,
                                         privacyideaServerUrl,
                                         CAConnectorUrl, inform) {
    /**
     Each service - just like this service factory - is a singleton.
     */
    return {
        getPGPKeys: function(callback) {
            $http.get(systemUrl + "/gpgkeys", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback).error(AuthFactory.authError);
        },
        getSMSProviders: function(callback) {
            $http.get(smsgatewayUrl + "/providers", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getSMSGateways: function(gwid, callback) {
            $http.get(smsgatewayUrl + "/" + gwid, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        setSMSGateway: function(params, callback) {
            $http.post(smsgatewayUrl, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        delSMSGateway: function(name, callback) {
            $http.delete(smsgatewayUrl+ "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(AuthFactory.authError);
        },
        delEvent: function(eventId, callback) {
            $http.delete(eventUrl + "/" + eventId, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(AuthFactory.authError);
        },
        enableEvent: function(eventId, callback) {
            $http.post(eventUrl + "/enable/" + eventId, {},
                {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(AuthFactory.authError);
        },
        disableEvent: function(eventId, callback) {
            $http.post(eventUrl + "/disable/" + eventId, {},
                {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(AuthFactory.authError);
        },
        setEvent: function(params, callback) {
            $http.post(eventUrl, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getEvents: function(callback) {
            $http.get(eventUrl, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getEvent: function(eventid, callback) {
            $http.get(eventUrl + "/" + eventid, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getHandlerActions: function(handlername, callback) {
            $http.get(eventUrl + "/actions/" + handlername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getHandlerConditions: function(handlername, callback) {
            $http.get(eventUrl + "/conditions/" + handlername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getHandlerPositions: function(handlername, callback) {
            $http.get(eventUrl + "/positions/" + handlername, {
              headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        delPeriodicTask: function (ptaskid, callback) {
            $http.delete(periodicTaskUrl + "/" + ptaskid, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(AuthFactory.authError);
        },
        getPeriodicTasks: function(callback) {
            $http.get(periodicTaskUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getPeriodicTaskmodules: function(callback) {
            $http.get(periodicTaskUrl + "/taskmodules/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getPeriodicTaskmoduleOptions: function(taskmodule, callback) {
            $http.get(periodicTaskUrl + "/options/" + taskmodule, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getPeriodicTask: function(ptaskid, callback) {
            $http.get(periodicTaskUrl + "/" + ptaskid, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        setPeriodicTask: function(params, callback) {
            $http.post(periodicTaskUrl + "/", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        enablePeriodicTask: function(ptaskid, callback) {
            $http.post(periodicTaskUrl + "/enable/" + ptaskid, {},
                { headers: {'PI-Authorization': AuthFactory.getAuthToken()} }
            ).success(callback
            ).error(AuthFactory.authError);
        },
        disablePeriodicTask: function(ptaskid, callback) {
            $http.post(periodicTaskUrl + "/disable/" + ptaskid, {},
                { headers: {'PI-Authorization': AuthFactory.getAuthToken()} }
            ).success(callback
            ).error(AuthFactory.authError);
        },
        getNodes: function(callback) {
            $http.get(periodicTaskUrl + "/nodes/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        delPolicy: function (policyName, callback) {
            $http.delete(policyUrl + "/" + policyName, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(AuthFactory.authError);
        },
        setPolicy: function (policyName, params, callback) {
            $http.post(policyUrl + "/" + policyName, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getPolicies: function (callback) {
            $http.get(policyUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getPolicy: function (policyname, callback) {
            $http.get(policyUrl + "/" + policyname, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        enablePolicy: function (policyname, callback) {
            $http.post(policyUrl + "/enable/" + policyname, {}, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        disablePolicy: function (policyname, callback) {
            $http.post(policyUrl + "/disable/" + policyname, {}, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getPolicyDefs: function (callback) {
            // Return the policy definitions
            $http.get(policyUrl + "/defs", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getResolvers: function (callback) {
            $http.get(resolverUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getEditableResolvers: function (callback) {
            $http.get(resolverUrl + "/?editable=1", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getResolver: function(resolvername, callback) {
            $http.get(resolverUrl + "/" + resolvername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getMachineResolver: function (resolvername, callback) {
            $http.get(machineResolverUrl + "/" + resolvername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getMachineResolvers: function (callback) {
            $http.get(machineResolverUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getCAConnectors: function (callback) {
            $http.get(CAConnectorUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getCAConnector: function (connectorname, callback) {
            $http.get(CAConnectorUrl + "/" + connectorname, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(AuthFactory.authError);
        },
        getRealms: function (callback) {
            $http.get(realmUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback)
                .error(AuthFactory.authError);
        },
        getAdminRealms: function(callback) {
            $http.get(realmUrl + "/superuser", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback).error(AuthFactory.authError);
        },
        setResolver: function (name, params, callback) {
            $http.post(resolverUrl + "/" + name, params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}}).success(
                callback).error(AuthFactory.authError);
        },
        setMachineResolver: function (name, params, callback) {
            $http.post(machineResolverUrl + "/" + name, params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(AuthFactory.authError);
        },
        setCAConnector: function(name, params, callback) {
            $http.post(CAConnectorUrl + "/" + name, params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(AuthFactory.authError);
        },
        testResolver: function (params, callback) {
            $http.post(resolverUrl + "/test", params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(AuthFactory.authError);
        },
        testMachineResolver: function (params, callback) {
            $http.post(machineResolverUrl + "/test", params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(AuthFactory.authError);
        },
        delResolver: function(name, callback) {
            $http.delete(resolverUrl + "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken() }
            }).success(callback).error(AuthFactory.authError);

        },
        delMachineResolver: function(name, callback) {
            $http.delete(machineResolverUrl + "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken() }
            }).success(callback).error(AuthFactory.authError);

        },
        delCAConnector: function(name, callback) {
            $http.delete(CAConnectorUrl + "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken() }
            }).success(callback).error(AuthFactory.authError);
        },
        setRealm: function(name, params, callback) {
            $http.post(realmUrl + "/" + name, params, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}}).success(
                callback).error(AuthFactory.authError);
        },
        delRealm: function(name, callback) {
            $http.delete(realmUrl +  "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        setDefaultRealm: function(name, callback) {
            $http.post(defaultRealmUrl + "/" + name, {},
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError)
        },
        clearDefaultRealm: function(callback) {
            $http.delete(defaultRealmUrl, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        getDocumentation: function(callback) {
            $http.get(systemUrl + "/documentation", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        saveSystemConfig: function(params, callback) {
            $http.post(systemUrl + "/setConfig", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        delSystemConfig: function(key, callback) {
            $http.delete(systemUrl + "/" + key, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        getRandom: function(len, encode, callback) {
            $http.get(systemUrl +
                encodeURI("/random?len=" + len + "&encode=" + encode), {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        testTokenConfig: function(tokentype, params, callback) {
            $http.post(systemUrl + "/test/" + tokentype, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        loadSystemConfig: function(callback, key) {
            if (!key) {key = "";}
            $http.get(systemUrl + "/" + key, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        getSystemConfig: function(callback) {
            $http.get(systemUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        getSmtp: function(callback, identifier) {
            if (!identifier) {identifier = "";}
            $http.get(smtpServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        delSmtp: function(identifier, callback) {
            $http.delete(smtpServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        addSmtp: function(params, callback) {
            var identifier = params["identifier"];
            $http.post(smtpServerUrl + "/" + identifier, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        testSmtp: function(params, callback) {
            $http.post(smtpServerUrl + "/send_test_email", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        getRadius: function(callback, identifier) {
            if (!identifier) {identifier = "";}
            $http.get(radiusServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        delRadius: function(identifier, callback) {
            $http.delete(radiusServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        addRadius: function(params, callback) {
            var identifier = params["identifier"];
            $http.post(radiusServerUrl + "/" + identifier, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        testRadius: function(params, callback) {
            $http.post(radiusServerUrl + "/test_request", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        getPrivacyidea: function(callback, identifier) {
            if (!identifier) {identifier = "";}
            $http.get(privacyideaServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        delPrivacyidea: function(identifier, callback) {
            $http.delete(privacyideaServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        addPrivacyidea: function(params, callback) {
            var identifier = params["identifier"];
            $http.post(privacyideaServerUrl + "/" + identifier, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        },
        testPrivacyidea: function(params, callback) {
            $http.post(privacyideaServerUrl + "/test_request", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(AuthFactory.authError);
        }
    };
});
