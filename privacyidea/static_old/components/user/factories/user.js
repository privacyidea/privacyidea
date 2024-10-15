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

myApp.factory("UserFactory", ['AuthFactory', '$http', '$state', '$rootScope',
                              'userUrl', 'inform', '$q',
                              function (AuthFactory, $http, $state, $rootScope,
                                        userUrl, inform, $q) {

        var canceller = $q.defer();

        return {
            getUsers: function(params, callback) {
                // We only need ONE getUsers call at once.
                // If another getUsers call is running, we cancel it.
                canceller.resolve();
                canceller = $q.defer();
                $http.get(userUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken() },
                    params: params,
                    timeout: canceller.promise
                }).then(function(response) { callback(response.data)},
                        function(error) { AuthFactory.authError(error.data) });
            },
            getUserDetails: function(params, callback) {
                // get user information without cancelling the call.
                $http.get(userUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken() },
                    params: params
                }).then(function(response) { callback(response.data)},
                        function(error) { AuthFactory.authError(error.data) });
            },
            updateUser: function(resolver, params, callback) {
                params.resolver = resolver;
                params.user = params.username;
                $http.put(userUrl + "/", params,
                    {headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function(response) { callback(response.data)},
                            function(error) { AuthFactory.authError(error.data) });
            },
            deleteUser: function(resolver, username, callback) {
                $http.delete(userUrl + "/" + resolver + "/" + encodeURIComponent(username),
                    {headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function(response) { callback(response.data)},
                            function(error) { AuthFactory.authError(error.data) });
            },
            createUser: function(resolver, User, callback) {
                var params = User;
                params.user = User.username;
                params.resolver = resolver;
                $http.post(userUrl + "/", params,
                    {headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function(response) { callback(response.data)},
                            function(error) { AuthFactory.authError(error.data) });
            },
            getEditableAttributes: function(params, callback) {
                $http.get(userUrl + "/editable_attributes/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken() },
                    params: params
                }).then(function(response) { callback(response.data)},
                        function(error) { AuthFactory.authError(error.data) });
            },
            setCustomAttribute: function(username, realmname, key, value, callback) {
                var params = {
                    "user": username, "realm": realmname,
                    "key": key, "value": value};
                $http.post(userUrl + "/attribute", params,
                    {headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function(response) {callback(response.data)},
                    function(error) {AuthFactory.authError(error.data)});
            },
            deleteCustomAttribute: function(username, realmname, key, callback) {
                $http.delete(userUrl + "/attribute/" + encodeURIComponent(key) + "/" + encodeURIComponent(username) + "/" + realmname,
                    {headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function(response) {callback(response.data)},
                    function(error) {AuthFactory.authError(error.data)});
            },
            getCustomAttributes: function(username, realmname, callback) {
                var params = {
                    "user": username, "realm": realmname};
                $http.get(userUrl + "/attribute",
                    {headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                     params: params
                    }).then(function(response) {callback(response.data)},
                    function(error) {AuthFactory.authError(error.data)});
            }

        };

}]);
