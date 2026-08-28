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
    "gettextCatalog", "$state", "$location", "ConfigFactory", "InfoFactory",
    function ($scope, $stateParams, inform, gettextCatalog, $state, $location, ConfigFactory, InfoFactory) {
        // Set the default route
        if ($location.path() === "/config/clients") {
            $location.path("/config/clients/list");
        }

        // The client types offered in the creation form: the integrations from the
        // shared backend catalog (privacyidea.lib.integrations) that are flagged as
        // API clients. The backend accepts any string, but validates it against this
        // same catalog.
        $scope.clientTypes = [];
        InfoFactory.getIntegrations(function (integrations) {
            $scope.clientTypes = integrations
                .filter(function (integration) {
                    return integration.api_client;
                })
                .map(function (integration) {
                    return {name: integration.id, label: integration.label};
                });
            // Preselect the first type so the creation form is never submitted with
            // an empty selection.
            $scope.params.client_type = $scope.clientTypes.length ? $scope.clientTypes[0].name : "";
        });
        // Map a stored client type to its label, falling back to the raw value
        // for types not (or no longer) in the catalog.
        $scope.clientTypeLabel = function (type) {
            for (var i = 0; i < $scope.clientTypes.length; i++) {
                if ($scope.clientTypes[i].name === type) {
                    return $scope.clientTypes[i].label;
                }
            }
            return type;
        };
        // The possible client states. "suspended" is a reversible off-switch;
        // permanent removal is a delete, so there is no separate "revoked".
        $scope.clientStates = ["active", "suspended"];

        // The catalog has not loaded yet when the controller is constructed; it is
        // filled in above once InfoFactory.getIntegrations resolves.
        $scope.params = {client_type: ""};
        // Holds a freshly generated API key so it can be shown to the admin
        // exactly once (after create or rotate). It is never fetched again.
        $scope.newApiKey = null;
        // Per-row inline confirmation state, keyed by client id / device id.
        $scope.showRotateDialog = {};
        $scope.showDeleteDialog = {};
        $scope.showRevokeDialog = {};

        $scope.getClients = function () {
            ConfigFactory.getClients(null, function (data) {
                $scope.clients = data.result.value;
                // Snapshot names so renameClient can tell a real edit from a
                // plain focus/blur and avoid pointless updates.
                $scope.originalNames = {};
                angular.forEach($scope.clients, function (c) {
                    $scope.originalNames[c.id] = c.display_name;
                });
            });
        };

        $scope.getClients();

        $scope.renameClient = function (client) {
            var name = (client.display_name || "").trim();
            if (!name || name === $scope.originalNames[client.id]) {
                // Empty or unchanged: revert to the stored name, do not save.
                client.display_name = $scope.originalNames[client.id];
                return;
            }
            ConfigFactory.updateClient(client.id, {display_name: name}, function (data) {
                if (data.result.status === true) {
                    inform.add(gettextCatalog.getString("Client renamed."), {type: "info"});
                    $scope.getClients();
                }
            });
        };

        $scope.rememberedDevicesClientId = $stateParams.clientid || "";
        $scope.rememberedDevicesClientName = $scope.rememberedDevicesClientId;
        $scope.realmList = [];
        $scope.rememberedDevices = [];
        $scope.rememberedDevicesCount = 0;
        $scope.rememberedDevicesPageSize = 50;
        // This view renders in a *child* scope of the clients controller (the
        // child states render in a nested ui-view). Bare scope primitives set from
        // the template (ng-model / ng-click) would shadow a copy on that child
        // scope and never reach the controller. So all template-mutated view state
        // lives on this single object: a dotted model mutates the shared object.
        // ui.realm null = all realms (the ng-options empty option).
        $scope.ui = {realm: null, revokeAllDialog: false, page: 1};

        $scope.getRealmList = function () {
            ConfigFactory.getRealms(function (data) {
                $scope.realmList = Object.keys(data.result.value || {}).sort();
            });
        };

        // The listing is paginated and realm-filtered server-side (a client can
        // accumulate a very large number of remembered devices), so both the page
        // and the realm selection are sent as query params rather than filtered
        // client-side over an already-loaded list.
        $scope.loadRememberedDevices = function (clientId) {
            $scope.rememberedDevicesClientId = clientId;
            var params = {
                page: $scope.ui.page,
                pagesize: $scope.rememberedDevicesPageSize,
                realm: $scope.ui.realm
            };
            ConfigFactory.getClientRememberedDevices(clientId, params, function (data) {
                $scope.rememberedDevices = data.result.value.devices;
                $scope.rememberedDevicesCount = data.result.value.count;
            });
        };

        $scope.devicesPageChanged = function () {
            $scope.loadRememberedDevices($scope.rememberedDevicesClientId);
        };

        $scope.onRealmFilterChange = function () {
            $scope.ui.page = 1;
            $scope.loadRememberedDevices($scope.rememberedDevicesClientId);
        };

        $scope.showRememberedDevices = function (client) {
            $scope.rememberedDevicesClientName = client.display_name;
            $scope.getRealmList();
            $scope.loadRememberedDevices(client.id);
            $state.go('config.clients.remembered_devices', {clientid: client.id});
        };

        $scope.revokeRememberedDevice = function (deviceId) {
            $scope.showRevokeDialog[deviceId] = false;
            ConfigFactory.revokeClientRememberedDevice($scope.rememberedDevicesClientId, deviceId, function (data) {
                if (data.result.status === true) {
                    inform.add(gettextCatalog.getString("Remembered device revoked."), {type: "info"});
                    $scope.loadRememberedDevices($scope.rememberedDevicesClientId);
                }
            });
        };

        $scope.revokeAllLabel = function () {
            return $scope.ui.realm
                ? gettextCatalog.getString("Revoke all in this realm")
                : gettextCatalog.getString("Revoke all");
        };

        // The trigger button keeps a short, fixed-width label (revokeAllLabel above),
        // but the confirm step names the actual realm and - critically - spells out
        // that a realm-scoped revoke crosses client boundaries, unlike the client-scoped
        // one, so this is not lost at the one place an admin can still back out.
        $scope.revokeAllConfirmText = function () {
            return $scope.ui.realm
                ? gettextCatalog.getString("Revoke all remembered devices in realm {{realm}} (across all clients)",
                    {realm: $scope.ui.realm})
                : gettextCatalog.getString("Revoke all remembered devices for this client");
        };

        // Bulk revoke. "For this client" is scoped to the client being viewed;
        // "in realm" revokes across all clients (realm-wide incident response), so
        // it reloads the current list after. One button drives both: which one
        // runs depends on whether a realm is selected (see revokeAll()).
        $scope.revokeAll = function () {
            $scope.ui.revokeAllDialog = false;
            if ($scope.ui.realm) {
                ConfigFactory.revokeRememberedDevices({realm: $scope.ui.realm}, function (data) {
                    if (data.result.status === true) {
                        inform.add(gettextCatalog.getString("Revoked {{count}} remembered device(s) in the realm.",
                            {count: data.result.value}), {type: "info"});
                        // Reset the realm selection and page so the view returns to
                        // "all realms", page 1 after the revoke.
                        $scope.ui.realm = null;
                        $scope.ui.page = 1;
                        $scope.loadRememberedDevices($scope.rememberedDevicesClientId);
                    }
                });
            } else {
                ConfigFactory.revokeAllClientRememberedDevices($scope.rememberedDevicesClientId, function (data) {
                    if (data.result.status === true) {
                        inform.add(gettextCatalog.getString("Revoked {{count}} remembered device(s).",
                            {count: data.result.value}), {type: "info"});
                        $scope.ui.page = 1;
                        $scope.loadRememberedDevices($scope.rememberedDevicesClientId);
                    }
                });
            }
        };

        $scope.revokeAllForUser = function (device) {
            $scope.showRevokeDialog[device.device_id] = false;
            ConfigFactory.revokeRememberedDevices({user: device.user, realm: device.realm}, function (data) {
                if (data.result.status === true) {
                    inform.add(gettextCatalog.getString("Revoked {{count}} remembered device(s) for the user.",
                        {count: data.result.value}), {type: "info"});
                    $scope.loadRememberedDevices($scope.rememberedDevicesClientId);
                }
            });
        };

        // Deep-link or page refresh directly onto the remembered-devices view: the
        // client's display name is not known yet (it is normally passed in by
        // showRememberedDevices() when navigating from the list), so resolve it
        // from the client itself instead of showing the raw client id.
        if ($stateParams.clientid) {
            ConfigFactory.getClients($stateParams.clientid, function (data) {
                var client = data.result.value[0];
                if (client) {
                    $scope.rememberedDevicesClientName = client.display_name;
                }
            });
            $scope.getRealmList();
            $scope.loadRememberedDevices($stateParams.clientid);
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
            // Inline status change from the list (active / suspended).
            ConfigFactory.updateClient(client.id, {status: client.status}, function (data) {
                if (data.result.status === true) {
                    inform.add(gettextCatalog.getString("Client status updated."),
                        {type: "info"});
                    $scope.getClients();
                }
            });
        };

        $scope.rotateClientKey = function (clientId) {
            $scope.showRotateDialog[clientId] = false;
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
            $scope.showDeleteDialog[clientId] = false;
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
            $scope.params = {client_type: $scope.clientTypes.length ? $scope.clientTypes[0].name : ""};
        };

        // listen to the reload broadcast: refresh whichever view is active.
        $scope.$on("piReload", function () {
            if ($state.includes('config.clients.remembered_devices') && $scope.rememberedDevicesClientId) {
                $scope.loadRememberedDevices($scope.rememberedDevicesClientId);
            } else {
                $scope.getClients();
            }
        });
    }]);
