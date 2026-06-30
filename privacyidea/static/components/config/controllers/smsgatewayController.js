/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2016-06-15 Cornelius Kölbel, <cornelius@privacyidea.org>
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

myApp.controller("smsgatewayController", ["$scope", "$stateParams", "$state",
    "$location", "ConfigFactory",
    function ($scope, $stateParams, $state, $location, ConfigFactory) {
        if ($location.path() === "/config/smsgateway") {
            $location.path("/config/smsgateway/list");
        }

        // Get all gateway definitions
        $scope.getSMSGateways = function (gwid) {
            ConfigFactory.getSMSGateways(gwid, function (data) {
                $scope.smsgateways = data.result.value;
            });
        };

        $scope.getSMSGateways();

        $scope.deleteSMSgateway = function (name) {
            ConfigFactory.delSMSGateway(name, function () {
                $scope.getSMSGateways();
            });
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getSMSGateways);
    }]);

myApp.controller("smsgatewayDetailsController", ["$scope", "$stateParams", "$state",
    "$location", "ConfigFactory",
    function ($scope, $stateParams, $state, $location, ConfigFactory) {
        $scope.form = {};
        $scope.gateway_id = $stateParams.gateway_id;
        $scope.opts = {};
        $scope.headers = {};
        $scope.optSecrets = {};
        $scope.headerSecrets = {};

        $scope.getSMSGateway = function () {
            if ($scope.gateway_id) {
                ConfigFactory.getSMSGateways($scope.gateway_id, function (data) {
                    $scope.smsgateways = data.result.value;
                    //debug: console.log("Fetched all SMS gateways");
                    //debug: console.log($scope.smsgateways);
                    $scope.form = $scope.smsgateways[0];
                    $scope.form.module = $scope.form.providermodule;
                    let option_array = Object.keys($scope.smsproviders[$scope.form.module].parameters);
                    // fill all parameters (default options and additional options)
                    angular.forEach(Object.keys($scope.form.options),
                        function (optionName) {
                            if (option_array.indexOf(optionName) > -1) {
                                $scope.form["option." + optionName] = $scope.form.options[optionName];
                            } else {
                                // file the optionals!
                                $scope.opts[optionName] = $scope.form.options[optionName];
                            }
                        });
                    // fill all parameters (headers)
                    $scope.headers = $scope.form.headers;

                    // Restore the secret checkbox state from the API response
                    $scope.optSecrets = {};
                    angular.forEach($scope.form.secret_options || [], function (key) {
                        if (option_array.indexOf(key) === -1) {
                            $scope.optSecrets[key] = true;
                        }
                    });
                    $scope.headerSecrets = {};
                    angular.forEach($scope.form.secret_headers || [], function (key) {
                        $scope.headerSecrets[key] = true;
                    });
                });
            }
        };

        // Get all provider definitions
        $scope.getSMSProviders = function () {
            ConfigFactory.getSMSProviders(function (data) {
                $scope.smsproviders = data.result.value;
                //debug: console.log("Fetched all SMS providers");
                //debug: console.log($scope.smsproviders);
                $scope.getSMSGateway();
            });
        };

        $scope.getSMSProviders();

        $scope.createSMSgateway = function () {
            // This is called to save the SMS gateway
            if ($scope.gateway_id) {
                $scope.form.id = $scope.gateway_id;
            }

            // Set secret flags for provider parameters declared as secret
            let providerParams = $scope.smsproviders[$scope.form.module] ?
                $scope.smsproviders[$scope.form.module].parameters : {};
            for (let paramname in providerParams) {
                if (providerParams.hasOwnProperty(paramname) && providerParams[paramname].secret) {
                    $scope.form["secret.option." + paramname] = true;
                }
            }

            // transform the event options to form parameters
            for (let option in $scope.opts) {
                if ($scope.opts.hasOwnProperty(option)) {
                    $scope.form["option." + option] = $scope.opts[option];
                    if ($scope.optSecrets[option]) {
                        $scope.form["secret.option." + option] = true;
                    }
                }
            }
            // transform the event headers to form parameters
            for (let header in $scope.headers) {
                if ($scope.headers.hasOwnProperty(header)) {
                    $scope.form["header." + header] = $scope.headers[header];
                    if ($scope.headerSecrets[header]) {
                        $scope.form["secret.header." + header] = true;
                    }
                }
            }

            delete $scope.form.options;
            delete $scope.form.headers;
            ConfigFactory.setSMSGateway($scope.form, function () {
                $state.go("config.smsgateway.list");
                $scope.deselectGateway();
                $('html,body').scrollTop(0);
                $scope.reload();
            });
        };

        $scope.deleteOption = function (optionName) {
            delete $scope.opts[optionName];
            delete $scope.optSecrets[optionName];
        };

        $scope.addOption = function () {
            $scope.opts[$scope.newoption] = $scope.newvalue;
            if ($scope.newoptionsecret) {
                $scope.optSecrets[$scope.newoption] = true;
            }
            $scope.newoption = "";
            $scope.newvalue = "";
            $scope.newoptionsecret = false;
        };

        $scope.deleteHeader = function (headerName) {
            delete $scope.headers[headerName];
            delete $scope.headerSecrets[headerName];
        };

        $scope.addHeader = function () {
            $scope.headers[$scope.newheader] = $scope.newheadervalue;
            if ($scope.newheadersecret) {
                $scope.headerSecrets[$scope.newheader] = true;
            }
            $scope.newheader = "";
            $scope.newheadervalue = "";
            $scope.newheadersecret = false;
        };

        $scope.deselectGateway = function () {
            $scope.form = {};
            $scope.gateway_id = null;
            $scope.opts = {};
            $scope.headers = {};
            $scope.optSecrets = {};
            $scope.headerSecrets = {};
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getSMSGateway);
    }]);
