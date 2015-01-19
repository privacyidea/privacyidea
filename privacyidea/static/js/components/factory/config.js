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
myApp.factory("ConfigFactory", function (auth, $http, $state, $rootScope,
                                         resolverUrl, realmUrl, defaultRealmUrl) {
    /**
     Each service - just like this service factory - is a singleton.
     */
    var error_func = function (error) {
        if (error.result.error.code == -401) {
            $state.go('login');
        } else {
            $rootScope.restError = error.result;
        }
    };

    return {
        getResolvers: function (callback) {
            $http.get(resolverUrl, {
                headers: {'Authorization': auth.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getResolver: function(resolvername, callback) {
            $http.get(resolverUrl + "/" + resolvername, {
                headers: {'Authorization': auth.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        getRealms: function (callback) {
            $http.get(realmUrl, {
                headers: {'Authorization': auth.getAuthToken()}
            }).success(callback)
                .error(error_func);
        },
        setResolver: function (name, params, callback) {
            $http.post(resolverUrl + "/" + name, params,
                {headers: {'Authorization': auth.getAuthToken(),
                          'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        testResolver: function (params, callback) {
            $http.post(resolverUrl + "/test", params,
                {headers: {'Authorization': auth.getAuthToken(),
                          'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        delResolver: function(name, callback) {
            $http.delete(resolverUrl + "/" + name, {
                headers: {'Authorization': auth.getAuthToken() }
            }).success(callback).error(error_func);

        },
        setRealm: function(name, params, callback) {
            $http.post(realmUrl + "/" + name, params, {
                    headers: {'Authorization': auth.getAuthToken(),
                          'Content-Type': 'application/json'}}).success(
                callback).error(error_func);
        },
        delRealm: function(name, callback) {
            $http.delete(realmUrl +  "/" + name, {
                headers: {'Authorization': auth.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        },
        setDefaultRealm: function(name, callback) {
            $http.post(defaultRealmUrl + "/" + name, {},
                {headers: {'Authorization': auth.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func)
        },
        clearDefaultRealm: function(callback) {
            $http.delete(defaultRealmUrl, {
                headers: {'Authorization': auth.getAuthToken(),
                          'Content-Type': 'application/json'}
            }).success(callback).error(error_func);
        }
    };
});
