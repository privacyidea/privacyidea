/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2016-09-01 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
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

myApp.factory("ComponentFactory", function (AuthFactory,
                                        $http, $state, $rootScope,
                                        clientUrl, inform) {
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
            getClientType: function(callback) {
                $http.get(clientUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).success(callback
                ).error(error_func);
            }
        }
    });


myApp.factory("SubscriptionFactory", function (AuthFactory, $http, $state,
                                               $rootScope, subscriptionsUrl,
                                               inform){
    var error_func = function (error) {
        if (error.result.error.code === -401) {
            $state.go('login');
        } else {
            inform.add(error.result.error.message, {type: "danger", ttl: 10000});
        }
    };

    return {
        get: function(callback) {
            $http.get(subscriptionsUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);
        },
        delete: function(application, callback) {
            $http.delete(subscriptionsUrl + "/" + application, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
            ).error(error_func);

        }
    }
});
