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

        $scope.params = {};
        // Holds a freshly generated API key so it can be shown to the admin
        // exactly once (after create or rotate). It is never fetched again.
        $scope.newApiKey = null;

        $scope.getClients = function () {
            ConfigFactory.getClients(null, function (data) {
                $scope.clients = data.result.value;
            });
        };

        $scope.getClients();

        // --- persistent "remember device" sessions ---
        $scope.sessions = [];
        $scope.sessionsClientId = $stateParams.clientid || "";
        $scope.sessionsClientName = $scope.sessionsClientId;

        $scope.loadSessions = function (clientId) {
            $scope.sessionsClientId = clientId;
            ConfigFactory.getClientSessions(clientId, function (data) {
                $scope.sessions = data.result.value;
            });
        };

        $scope.showSessions = function (client) {
            $scope.sessionsClientName = client.display_name;
            $scope.loadSessions(client.id);
            $state.go('config.clients.sessions', {clientid: client.id});
        };

        $scope.revokeSession = function (seriesId) {
            ConfigFactory.revokeClientSession($scope.sessionsClientId, seriesId, function (data) {
                if (data.result.status === true) {
                    inform.add(gettextCatalog.getString("Session revoked."), {type: "info"});
                    $scope.loadSessions($scope.sessionsClientId);
                }
            });
        };

        // Deep-link or page refresh directly onto the sessions view.
        if ($stateParams.clientid) {
            $scope.loadSessions($stateParams.clientid);
        }

        $scope.saveClient = function () {
            // Create a new client. The response carries the plaintext API key,
            // which we surface once on the list page.
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
        };

        $scope.setClientStatus = function (client) {
            // Inline status change from the list (active / suspended / revoked).
            ConfigFactory.updateClient(client.id, {status: client.status}, function (data) {
                if (data.result.status === true) {
                    inform.add(gettextCatalog.getString("Client status updated."),
                        {type: "info"});
                    $scope.getClients();
                }
            });
        };

        $scope.rotateClientKey = function (clientId) {
            ConfigFactory.rotateClientKey(clientId, function (data) {
                if (data.result.status === true) {
                    var client = data.result.value;
                    $scope.newApiKey = {
                        display_name: client.display_name,
                        api_key: client.api_key
                    };
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

        $scope.copyApiKey = function () {
            var text = $scope.newApiKey ? $scope.newApiKey.api_key : "";
            if (!text) {
                return;
            }
            var copied = function () {
                inform.add(gettextCatalog.getString("API key copied to clipboard."),
                    {type: "info"});
            };
            var failed = function () {
                inform.add(gettextCatalog.getString("Could not copy the API key to the clipboard."),
                    {type: "danger"});
            };
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(copied, failed);
            } else {
                // Fallback for non-secure contexts (e.g. plain HTTP) where the
                // async Clipboard API is unavailable.
                var textarea = document.createElement("textarea");
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                try {
                    document.execCommand("copy");
                    copied();
                } catch (e) {
                    failed();
                }
                document.body.removeChild(textarea);
            }
        };

        $scope.deselectClient = function () {
            $scope.params = {};
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getClients);
    }]);
