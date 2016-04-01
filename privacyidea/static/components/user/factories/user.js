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

myApp.factory("UserFactory", function (AuthFactory, $http, $state, $rootScope,
                                       userUrl, inform, $q) {
        var error_func = function (error) {
                        if (error.result.error.code === -401) {
                            $state.go('login');
                        } else {
                            inform.add(error.result.error.message,
                                {type: "danger", ttl: 10000});
                        }
                    };

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
                }).success(callback
                ).error(error_func);
            },
            getUserDetails: function(params, callback) {
                // get user information without cancelling the call.
                $http.get(userUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken() },
                    params: params
                }).success(callback
                ).error(error_func);
            },
            updateUser: function(resolver, params, callback) {
                params.resolver = resolver;
                params.user = params.username;
                $http.put(userUrl, params,
                    {headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).success(callback).error(error_func);
            },
            deleteUser: function(resolver, username, callback) {
                $http.delete(userUrl + "/" + resolver + "/" + username,
                    {headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).success(callback).error(error_func);
            },
            createUser: function(resolver, User, callback) {
                var params = User;
                params.user = User.username;
                params.resolver = resolver;
                $http.post(userUrl + '/', params,
                    {headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).success(callback).error(error_func);
            }
        };

});
