/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2019-10-14 Jean-Pierre Höhmann, <jean-pierre.hoehmann@netknights.it>
 *            Add confirmation dialogs
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

// TODO: We can not delete an optional value!

myApp.controller("smsgatewayController", function($scope, $stateParams,
                                                  $state,
                                                  $location, ConfigFactory) {
    if ($location.path() === "/config/smsgateway") {
        $location.path("/config/smsgateway/list");
    }

    $scope.form = {};
    $scope.gateway_id = $stateParams.gateway_id;
    $scope.opts = {};

    // Get all gateway definitions
    $scope.getSMSGateways = function (gwid) {
        ConfigFactory.getSMSGateways(gwid, function(data) {
            $scope.smsgateways = data.result.value;
            //debug: console.log("Fetched all SMS gateways");
            //debug: console.log($scope.smsgateways);
            if (gwid) {
                $scope.form = $scope.smsgateways[0];
                $scope.form.module = $scope.form.providermodule;
                var option_array = Object.keys($scope.smsproviders[$scope.form.module].parameters);
                // fill all parameters
                angular.forEach(Object.keys($scope.form.options),
                    function (optionname) {
                        if (option_array.indexOf(optionname)>-1) {
                            $scope.form["option." + optionname] = $scope.form.options[optionname];
                        } else {
                            // file the optionals!
                            $scope.opts[optionname] = $scope.form.options[optionname];
                        }
                    });
            }
        });
    };

    // Get all provider definitions
    $scope.getSMSProviders = function () {
        ConfigFactory.getSMSProviders(function(data) {
            $scope.smsproviders = data.result.value;
            //debug: console.log("Fetched all SMS providers");
            //debug: console.log($scope.smsproviders);
        });
    };

    $scope.getSMSProviders();
    $scope.getSMSGateways($scope.gateway_id);

    $scope.createSMSgatewayAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["difficult"],
            gettextCatalog.getString("Store SMS Gateway Definition"),
            gettextCatalog.getString("Do you want to apply these settings?"),
            gettextCatalog.getString("Store SMS Gateway"),
            $scope.createSMSgateway);
    };

    $scope.createSMSgateway = function () {
        // This is called to save the SMS gateway
        if ($scope.gateway_id) {
            $scope.form.id = $scope.gateway_id;
        }

        // transform the event options to form parameters
        for (var option in $scope.opts) {
            if ($scope.opts.hasOwnProperty(option)) {
                $scope.form["option." + option] = $scope.opts[option];
            }
        }

        delete $scope.form.options;
        ConfigFactory.setSMSGateway($scope.form, function() {
            $state.go("config.smsgateway.list");
            $('html,body').scrollTop(0);
        });
    };

    $scope.deleteSMSgatewayAsk = function(name) {
        $scope.confirm(
            $scope.confirm_action_levels["severe"],
            gettextCatalog.getString("Delete SMS Gateway Definition"),
            gettextCatalog.getString("Do you really want to delete this SMS gateway?"),
            gettextCatalog.getString("Delete SMS Gateway"),
            function() {
                $scope.deleteSMSgateway(name);
            });
    };

    $scope.deleteSMSgateway = function (name) {
      ConfigFactory.delSMSGateway(name, function() {
            $scope.getSMSGateways();
      });
    };

    $scope.deleteOption = function(optionname) {
        delete $scope.opts[optionname];
    };

    $scope.addOption = function() {
        $scope.opts[$scope.newoption] = $scope.newvalue;
        $scope.newoption = "";
        $scope.newvalue = "";
    };

    // listen to the reload broadcast
    $scope.$on("piReload", $scope.getSMSGateways);
});
