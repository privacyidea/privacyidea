/**
 * (c) NetKnights GmbH 2024,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-FileCopyrightText: 2024 Nils Behlen <nils.behlen@netknights.it>
 * SPDX-FileCopyrightText: 2024 Jelina Unger <jelina.unger@netknights.it>
 * SPDX-License-Identifier: AGPL-3.0-or-later
**/

myApp.factory("ContainerFactory", ['AuthFactory', '$http', 'containerUrl', '$q', '$state', '$rootScope',
    function (AuthFactory, $http, containerUrl, $q, $state, $rootScope) {
        let canceller = $q.defer();
        return {
            getContainers: function (params, callback) {
                canceller.resolve();
                canceller = $q.defer();
                $http.get(containerUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    params: params,
                    timeout: canceller.promise
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data);
                });
            },
            getContainerForSerial: function (serial, callback) {
                $http.get(containerUrl + "/?container_serial=" + serial, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            getContainerTypes: function (callback) {
                canceller.resolve();
                canceller = $q.defer();
                $http.get(containerUrl + "/types", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    timeout: canceller.promise
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data);
                });
            },
            createContainer: function (params, callback) {
                canceller.resolve();
                canceller = $q.defer();
                $http.post(containerUrl + "/init", params, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    timeout: canceller.promise
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data);
                });
            },
            addTokenToContainer: function (params, callback) {
                $http.post(containerUrl + "/" + params["container_serial"] + "/add", {serial: params["serial"]}, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            addAllTokensToContainer: function (params, callback) {
                $http.post(containerUrl + "/" + params["container_serial"] + "/addall", {serial: params["serial"]}, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            removeTokenFromContainer: function (params, callback) {
                $http.post(containerUrl + "/" + params["container_serial"] + "/remove", {serial: params["serial"]}, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            removeAllTokensFromContainer: function (params, callback) {
                $http.post(containerUrl + "/" + params["container_serial"] + "/removeall", {serial: params["serial"]}, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            assignUser: function (params, callback) {
                $http.post(containerUrl + "/" + params["container_serial"] + "/assign", params, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            unassignUser: function (params, callback) {
                $http.post(containerUrl + "/" + params["container_serial"] + "/unassign", params, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            getContainerForUser: function (params, callback) {
                $http.get(containerUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    params: params
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data);
                });
            },
            deleteContainer: function (serial, callback) {
                $http.delete(containerUrl + "/" + serial, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            setDescription: function (serial, description, callback) {
                $http.post(containerUrl + "/" + serial + "/description",
                    {"description": description}, {
                        headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            updateLastSeen: function (serial) {
                $http.post(containerUrl + "/" + serial + "/lastseen",
                    {}, {
                        headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function (response) {
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            setStates: function (params, callback) {
                $http.post(containerUrl + "/" + params["container_serial"] + "/states", params, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            getStateTypes: function (callback) {
                $http.get(containerUrl + "/statetypes", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            getTokenTypes: function (callback) {
                $http.get(containerUrl + "/types", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data);
                });
            },
            setRealms: function (params, callback) {
                $http.post(containerUrl + "/" + params["container_serial"] + "/realms", params, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            }
        }
    }]);