/**
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
myApp.controller("clientsController", ["$scope", "$stateParams", "inform",
    "gettextCatalog", "$state", "$location", "ConfigFactory",
    function ($scope, $stateParams, inform, gettextCatalog, $state, $location, ConfigFactory) {
        // Set the default route
        if ($location.path() === "/config/clients") {
            $location.path("/config/clients/list");
        }

        // The known client types offered in the creation form.
        $scope.clientTypes = ["windows_cp", "keycloak", "entraid"];
        // The possible client states.
        $scope.clientStates = ["active", "suspended", "revoked"];

        $scope.clientid = $stateParams.clientid;
        $scope.params = {};
        // Holds a freshly generated API key so it can be shown to the admin
        // exactly once (after create or rotate). It is never fetched again.
        $scope.newApiKey = null;

        $scope.getClients = function () {
            ConfigFactory.getClients($scope.clientid, function (data) {
                var value = data.result.value;
                if ($scope.clientid) {
                    // Editing a single client: the list holds exactly one entry.
                    $scope.client = value[0];
                    $scope.params.display_name = $scope.client.display_name;
                    $scope.params.status = $scope.client.status;
                } else {
                    $scope.clients = value;
                }
            });
        };

        $scope.getClients();

        $scope.saveClient = function () {
            if ($scope.clientid) {
                // Update metadata of an existing client.
                ConfigFactory.updateClient($scope.clientid, $scope.params, function (data) {
                    if (data.result.status === true) {
                        inform.add(gettextCatalog.getString("Client saved."),
                            {type: "info"});
                        $scope.deselectClient();
                        $state.go('config.clients.list');
                        $scope.reload();
                    }
                });
            } else {
                // Create a new client. The response carries the plaintext API
                // key, which we surface once on the list page.
                ConfigFactory.addClient($scope.params, function (data) {
                    if (data.result.status === true) {
                        var client = data.result.value;
                        $scope.newApiKey = {
                            display_name: client.display_name,
                            api_key: client.api_key
                        };
                        inform.add(gettextCatalog.getString("Client created."),
                            {type: "info"});
                        $scope.deselectClient();
                        $state.go('config.clients.list');
                        $scope.reload();
                    }
                });
            }
        };

        $scope.rotateClientKey = function (clientId) {
            ConfigFactory.rotateClientKey(clientId, function (data) {
                if (data.result.status === true) {
                    var client = data.result.value;
                    $scope.newApiKey = {
                        display_name: client.display_name,
                        api_key: client.api_key
                    };
                    inform.add(gettextCatalog.getString("API key rotated."),
                        {type: "info"});
                    $scope.getClients();
                }
            });
        };

        $scope.delClient = function (clientId) {
            ConfigFactory.delClient(clientId, function (data) {
                $scope.getClients();
            });
        };

        $scope.dismissApiKey = function () {
            $scope.newApiKey = null;
        };

        $scope.deselectClient = function () {
            $scope.clientid = "";
            $scope.params = {};
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getClients);
    }]);
