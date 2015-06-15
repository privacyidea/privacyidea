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
myApp.factory("ConfigFactory", function (AuthFactory, $http, $state, $rootScope,
                                         resolverUrl, realmUrl,
                                         machineResolverUrl,
                                         policyUrl,
                                         defaultRealmUrl, systemUrl,
                                         CAConnectorUrl, inform) {
    /**
     Each service - just like this service factory - is a singleton.
     */
    var error_func = function (error) {
        if (error.result.error.code == -401) {
            $state.go('login');
        } else {
            inform.add(error.result.error.message, {type: "danger", ttl: 10000});
        }
    };

    return {
        delPolicy: function (policyName, callback) {
            $http.delete(policyUrl + "/" + policyName, {
                headers: {'Authorization': AuthFactory.getAuthToken()}}
            ).success(callback
            ).error(error_func);
        },
        setPolicy: function (policyName, params, callback) {
            $http.post(policyUrl + "/" + policyName, params, {
                headers: {'Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback
            ).error(error_func);
        },
        getPolicies: function (callback) {
            $http.get(policyUrl, {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getPolicy: function (policyname, callback) {
            $http.get(policyUrl + "/" + policyname, {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        enablePolicy: function (policyname, callback) {
            $http.post(policyUrl + "/enable/" + policyname, {}, {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        disablePolicy: function (policyname, callback) {
            $http.post(policyUrl + "/disable/" + policyname, {}, {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getPolicyDefs: function (callback) {
            // Return the policy definitions
            $http.get(policyUrl + "/defs", {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getResolvers: function (callback) {
            $http.get(resolverUrl, {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getEditableResolvers: function (callback) {
            $http.get(resolverUrl + "/?editable=1", {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getResolver: function(resolvername, callback) {
            $http.get(resolverUrl + "/" + resolvername, {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getMachineResolver: function (resolvername, callback) {
            $http.get(machineResolverUrl + "/" + resolvername, {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getMachineResolvers: function (callback) {
            $http.get(machineResolverUrl, {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getCAConnectors: function (callback) {
            $http.get(CAConnectorUrl, {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getCAConnector: function (connectorname, callback) {
            $http.get(CAConnectorUrl + "/" + connectorname, {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getRealms: function (callback) {
            $http.get(realmUrl, {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback)
                .error(error_func);
        },
        getAdminRealms: function(callback) {
            $http.get(realmUrl + "/superuser", {
                headers: {'Authorization': AuthFactory.getAuthToken()}
            }).success(callback).error(error_func)
        },
        setResolver: function (name, params, callback) {
            $http.post(resolverUrl + "/" + name, params,
                {headers: {'Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        setMachineResolver: function (name, params, callback) {
            $http.post(machineResolverUrl + "/" + name, params,
                {headers: {'Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        setCAConnector: function(name, params, callback) {
            $http.post(CAConnectorUrl + "/" + name, params,
                {headers: {'Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        testResolver: function (params, callback) {
            $http.post(resolverUrl + "/test", params,
                {headers: {'Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        testMachineResolver: function (params, callback) {
            $http.post(machineResolverUrl + "/test", params,
                {headers: {'Authorization': AuthFactory.getAuthToken(),
                           'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        delResolver: function(name, callback) {
            $http.delete(resolverUrl + "/" + name, {
                headers: {'Authorization': AuthFactory.getAuthToken() }
            }).success(callback).error(error_func);

        },
        delMachineResolver: function(name, callback) {
            $http.delete(machineResolverUrl + "/" + name, {
                headers: {'Authorization': AuthFactory.getAuthToken() }
            }).success(callback).error(error_func);

        },
        delCAConnector: function(name, callback) {
            $http.delete(CAConnectorUrl + "/" + name, {
                headers: {'Authorization': AuthFactory.getAuthToken() }
            }).success(callback).error(error_func);
        },
        setRealm: function(name, params, callback) {
            $http.post(realmUrl + "/" + name, params, {
                    headers: {'Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        delRealm: function(name, callback) {
            $http.delete(realmUrl +  "/" + name, {
                headers: {'Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        setDefaultRealm: function(name, callback) {
            $http.post(defaultRealmUrl + "/" + name, {},
                {headers: {'Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func)
        },
        clearDefaultRealm: function(callback) {
            $http.delete(defaultRealmUrl, {
                headers: {'Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        saveSystemConfig: function(params, callback) {
            $http.post(systemUrl + "/setConfig", params, {
                headers: {'Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        loadSystemConfig: function(callback, key) {
            if (!key) { key = ""};
            $http.get(systemUrl + "/" + key, {
                headers: {'Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        getSystemConfig: function(callback) {
            $http.get(systemUrl, {
                headers: {'Authorization': AuthFactory.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        }
    };
});
