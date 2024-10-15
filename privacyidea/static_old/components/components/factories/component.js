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

myApp.factory("ComponentFactory", ["AuthFactory", "$http", "$state",
                                   "$rootScope", "clientUrl", "inform",
                                   function (AuthFactory, $http, $state,
                                             $rootScope, clientUrl, inform) {
        /**
         Each service - just like this service factory - is a singleton.
         */
        return {
            getClientType: function(callback) {
                $http.get(clientUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function(response) { callback(response.data) },
                    function(error) { AuthFactory.authError(error.data) });
            }
        }
    }]);


myApp.factory("SubscriptionFactory", ["AuthFactory", "$http", "$state",
                                      "$rootScope", "subscriptionsUrl", "inform",
                                      function (AuthFactory, $http, $state,
                                                $rootScope, subscriptionsUrl,
                                                inform){
    return {
        get: function(callback) {
            $http.get(subscriptionsUrl + "/", {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) },
                function(error) { AuthFactory.authError(error.data) });
        },
        delete: function(application, callback) {
            $http.delete(subscriptionsUrl + "/" + application, {
                headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).then(function(response) { callback(response.data) },
                function(error) { AuthFactory.authError(error.data) });

        }
    }
}]);
