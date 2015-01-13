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
myApp.factory("ConfigFactory", function (auth, $http, $state, $rootScope, realmUrl) {
        /**
         Each service - just like this service factory - is a singleton.
         */
        var user = auth.getUser();
        var auth_token = auth.getAuthToken();
        var error_func = function (error) {
                        if (error.result.error.code == -401) {
                            $state.go('login');
                        } else {
                            $rootScope.restError = error.result;
                        }
                    };

        return {
            getRealms: function (callback) {
                $http.get(realmUrl, {
                    headers: {'Authorization': auth_token }
                }).success(callback)
                .error(error_func);
            }
        }
        });

myApp.factory("UserFactory", function (auth, $http, $state, $rootScope, userUrl) {
        var user = auth.getUser();
        var auth_token = auth.getAuthToken();
        var error_func = function (error) {
                        if (error.result.error.code == -401) {
                            $state.go('login');
                        } else {
                            $rootScope.restError = error.result;
                        }
                    };

        return {
            getUsers: function(params, callback) {
                $http.get(userUrl, {
                    headers: {'Authorization': auth_token },
                    params: params
                }).success(callback
                ).error(error_func)
            }
        }

});
