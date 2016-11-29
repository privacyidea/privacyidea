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
            console.log("Going to fetch Policy Templates");
            $http.get(URL + "index.json")
                .success(callback).error(function (error) {
                    console.log("Error fetching Policy Templates.");
                    console.log(error);
                    inform.add(gettextCatalog.getString("Error fetching" +
                        " policy templates."),
                                {type: "danger", ttl:10000});
            });
        },
        getTemplate: function(templateName, callback) {
            console.log("Going to fetch Policy Template " + templateName);
            $http.get(URL + templateName + ".json")
                .success(callback).error(function (error) {
                    console.log(error);
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
                                         CAConnectorUrl, inform) {
    /**
     Each service - just like this service factory - is a singleton.
     */
    var error_func = function (error) {
        if (error.result.error.code === -401) {
            $state.go('login');
        } else {
            inform.add(error.result.error.message, {type: "danger", ttl: 10000});
        }
    };

    return {
        getSMSProviders: function(callback) {
            $http.get(smsgatewayUrl + "/providers", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getSMSGateways: function(gwid, callback) {
            $http.get(smsgatewayUrl + "/" + gwid, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        setSMSGateway: function(params, callback) {
            $http.post(smsgatewayUrl, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback
            ).error(error_func);
        },
        delSMSGateway: function(name, callback) {
            $http.delete(smsgatewayUrl+ "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(error_func);
        },
        delEvent: function(eventId, callback) {
            $http.delete(eventUrl + "/" + eventId, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(error_func);
        },
        enableEvent: function(eventId, callback) {
            $http.post(eventUrl + "/enable/" + eventId, {},
                {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(error_func);
        },
        disableEvent: function(eventId, callback) {
            $http.post(eventUrl + "/disable/" + eventId, {},
                {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(error_func);
        },
        setEvent: function(params, callback) {
            $http.post(eventUrl, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback
            ).error(error_func);
        },
        getEvents: function(callback) {
            $http.get(eventUrl, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getEvent: function(eventid, callback) {
            $http.get(eventUrl + "/" + eventid, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getHandlerActions: function(handlername, callback) {
            $http.get(eventUrl + "/actions/" + handlername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getHandlerConditions: function(handlername, callback) {
            $http.get(eventUrl + "/conditions/" + handlername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        delPolicy: function (policyName, callback) {
            $http.delete(policyUrl + "/" + policyName, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(error_func);
        },
        setPolicy: function (policyName, params, callback) {
            $http.post(policyUrl + "/" + policyName, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback
            ).error(error_func);
        },
        getPolicies: function (callback) {
            $http.get(policyUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getPolicy: function (policyname, callback) {
            $http.get(policyUrl + "/" + policyname, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        enablePolicy: function (policyname, callback) {
            $http.post(policyUrl + "/enable/" + policyname, {}, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        disablePolicy: function (policyname, callback) {
            $http.post(policyUrl + "/disable/" + policyname, {}, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getPolicyDefs: function (callback) {
            // Return the policy definitions
            $http.get(policyUrl + "/defs", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getResolvers: function (callback) {
            $http.get(resolverUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getEditableResolvers: function (callback) {
            $http.get(resolverUrl + "/?editable=1", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getResolver: function(resolvername, callback) {
            $http.get(resolverUrl + "/" + resolvername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getMachineResolver: function (resolvername, callback) {
            $http.get(machineResolverUrl + "/" + resolvername, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getMachineResolvers: function (callback) {
            $http.get(machineResolverUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getCAConnectors: function (callback) {
            $http.get(CAConnectorUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getCAConnector: function (connectorname, callback) {
            $http.get(CAConnectorUrl + "/" + connectorname, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getRealms: function (callback) {
            $http.get(realmUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback)
                .error(error_func);
        },
        getAdminRealms: function(callback) {
            $http.get(realmUrl + "/superuser", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback).error(error_func);
        },
        setResolver: function (name, params, callback) {
            $http.post(resolverUrl + "/" + name, params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        setMachineResolver: function (name, params, callback) {
            $http.post(machineResolverUrl + "/" + name, params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        setCAConnector: function(name, params, callback) {
            $http.post(CAConnectorUrl + "/" + name, params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        testResolver: function (params, callback) {
            $http.post(resolverUrl + "/test", params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        testMachineResolver: function (params, callback) {
            $http.post(machineResolverUrl + "/test", params,
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        delResolver: function(name, callback) {
            $http.delete(resolverUrl + "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken() }
            }).success(callback).error(error_func);

        },
        delMachineResolver: function(name, callback) {
            $http.delete(machineResolverUrl + "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken() }
            }).success(callback).error(error_func);

        },
        delCAConnector: function(name, callback) {
            $http.delete(CAConnectorUrl + "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken() }
            }).success(callback).error(error_func);
        },
        setRealm: function(name, params, callback) {
            $http.post(realmUrl + "/" + name, params, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        delRealm: function(name, callback) {
            $http.delete(realmUrl +  "/" + name, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        setDefaultRealm: function(name, callback) {
            $http.post(defaultRealmUrl + "/" + name, {},
                {headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func)
        },
        clearDefaultRealm: function(callback) {
            $http.delete(defaultRealmUrl, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        getDocumentation: function(callback) {
            $http.get(systemUrl + "/documentation", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        saveSystemConfig: function(params, callback) {
            $http.post(systemUrl + "/setConfig", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        delSystemConfig: function(key, callback) {
            $http.delete(systemUrl + "/" + key, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        getRandom: function(len, encode, callback) {
            $http.get(systemUrl +
                encodeURI("/random?len=" + len + "&encode=" + encode), {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        testTokenConfig: function(tokentype, params, callback) {
            $http.post(systemUrl + "/test/" + tokentype, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        loadSystemConfig: function(callback, key) {
            if (!key) {key = "";}
            $http.get(systemUrl + "/" + key, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        getSystemConfig: function(callback) {
            $http.get(systemUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        getSmtp: function(callback, identifier) {
            if (!identifier) {identifier = "";}
            $http.get(smtpServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        delSmtp: function(identifier, callback) {
            $http.delete(smtpServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        addSmtp: function(params, callback) {
            var identifier = params["identifier"];
            $http.post(smtpServerUrl + "/" + identifier, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        testSmtp: function(params, callback) {
            $http.post(smtpServerUrl + "/send_test_email", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        getRadius: function(callback, identifier) {
            if (!identifier) {identifier = "";}
            $http.get(radiusServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        delRadius: function(identifier, callback) {
            $http.delete(radiusServerUrl + "/" + identifier, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        addRadius: function(params, callback) {
            var identifier = params["identifier"];
            $http.post(radiusServerUrl + "/" + identifier, params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        testRadius: function(params, callback) {
            $http.post(radiusServerUrl + "/test_request", params, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        }
    };
});
