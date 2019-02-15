/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2015-02-27 Cornelius Kölbel, <cornelius@privacyidea.org>
 *            Add machines to Web UI
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

myApp.factory("MachineFactory", function (AuthFactory, $http, $state,
                                          $rootScope, machineUrl,
                                          applicationUrl, inform) {
        return {
            getMachines: function(params, callback) {
                $http.get(machineUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken() },
                    params: params
                }).success(callback
                ).error(AuthFactory.authError);
            },
            getMachineTokens: function(params, callback) {
                $http.get(machineUrl + "/token", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    params: params
            }).success(callback
                ).error(AuthFactory.authError);
            },
            attachTokenMachine: function(params, callback) {
                $http.post(machineUrl + "/token", params, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).success(callback).error(AuthFactory.authError);
            },
            detachTokenMachine: function(params, callback) {
                // /token/<serial>/<machineid>/<resolver>/<application>
                $http.delete(machineUrl + "/token/" + params.serial + "/" +
                    params.machineid + "/" + params.resolver + "/" +
                    params.application,
                    { headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).success(callback).error(AuthFactory.authError);
            },
            getApplicationDefinition: function(callback) {
                $http.get(applicationUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
            }).success(callback
                ).error(AuthFactory.authError);
            },
            saveOptions: function(params, callback) {
                $http.post(machineUrl + "/tokenoption", params, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).success(callback).error(AuthFactory.authError);
            }
        };

});
