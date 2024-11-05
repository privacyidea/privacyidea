/**
 *
 * 2023-03-20 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
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
myApp.controller("serviceidController", ["$scope", "$stateParams", "inform",
    "gettextCatalog", "$state", "$location", "ConfigFactory",
    function ($scope, $stateParams, inform, gettextCatalog, $state, $location, ConfigFactory) {
        // Set the default route
        if ($location.path() === "/config/serviceid") {
            $location.path("/config/serviceid/list");
        }

        $scope.servicename = $stateParams.servicename;
        if (!$scope.servicename) {
            $scope.servicename = "";
        }
        $scope.params = {};

        $scope.getServiceIds = function () {
            ConfigFactory.getServiceid($scope.servicename, function (data) {
                $scope.serviceids = data.result.value;
                if ($scope.servicename) {
                    $scope.params.servicename = $scope.servicename;
                    $scope.params.description = $scope.serviceids[$scope.servicename].description;
                    $scope.params.id = $scope.serviceids[$scope.servicename].id;
                }
            });
        };

        $scope.getServiceIds();

        $scope.delServiceid = function (sname) {
            ConfigFactory.delServiceid(sname, function (data) {
                $scope.getServiceids();
            });
        };

        $scope.saveServiceid = function () {
            ConfigFactory.addServiceid($scope.params, function (data) {
                if (data.result.status === true) {
                    inform.add(gettextCatalog.getString("Service ID saved."),
                        {type: "info"});
                    $scope.deselectServiceId();
                    $state.go('config.serviceid.list');
                    $scope.reload();
                }
            });
        };

        $scope.deselectServiceId = function () {
            $scope.servicename = "";
            $scope.params = {};
            $scope.getServiceIds();
        };

        $scope.editServiceId = function (serviceName) {
            $scope.servicename = serviceName;
            $scope.getServiceIds();
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getServiceIds);
    }]);
