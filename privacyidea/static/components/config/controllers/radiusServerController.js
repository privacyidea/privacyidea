/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2016-02-20 Cornelius Kölbel, <cornelius@privacyidea.org>
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
myApp.controller("radiusServerController", ["$scope", "$stateParams", "inform",
                                            "gettextCatalog", "$state",
                                            "$location", "ConfigFactory",
                                            function($scope, $stateParams,
                                                     inform, gettextCatalog,
                                                     $state, $location,
                                                     ConfigFactory) {
    // Set the default route
    if ($location.path() === "/config/radius") {
        $location.path("/config/radius/list");
    }
    $scope.identifier = $stateParams.identifier;
    $scope.params = {};

    // Get all servers
    $scope.getRadiusServers = function () {
        ConfigFactory.getRadius(function(data) {
            $scope.radiusServers = data.result.value;
            //debug: console.log("Fetched all radius servers");
            //debug: console.log($scope.radiusServers);
            // return one single RADIUS server
            if ($scope.identifier) {
                // We are editing an existing radius server
                $scope.params = $scope.radiusServers[$scope.identifier];
                $scope.params["identifier"] = $scope.identifier;
            }
            else {
                $scope.params = {};
            }
        });
    };

    $scope.getRadiusServers();

    $scope.delRadiusServer = function (identifier) {
        ConfigFactory.delRadius(identifier, function(data) {
            $scope.getRadiusServers();
        });
    };

    $scope.addRadiusServer = function (params) {
        ConfigFactory.addRadius(params, function(data) {
            $scope.getRadiusServers();
        });
    };

    $scope.testRadiusRequest = function() {
        ConfigFactory.testRadius($scope.params, function(data) {
           if (data.result.value === true) {
               inform.add(gettextCatalog.getString("RADIUS request" +
                   " successful."),
                   {type: "info"});
           } else {
               inform.add(gettextCatalog.getString("RADIUS request failed!"),
                   {type: "danger"});
           }
        });
    };

    $scope.saveRadiusServer= function() {
        ConfigFactory.addRadius($scope.params, function(data){
            if (data.result.status === true) {
                inform.add(gettextCatalog.getString("RADIUS Config saved."),
                                {type: "info"});
                $scope.deselectRadiusServer();
                $state.go('config.radius.list');
                $scope.reload();
            }
        });
    };

    $scope.deselectRadiusServer = function() {
        $scope.params = {};
        $scope.identifier = null;
        $scope.getRadiusServers();
    };

    $scope.editRadiusServer = function(identifier) {
        $scope.identifier = identifier;
        $scope.getRadiusServers();
    };

    // listen to the reload broadcast
    $scope.$on("piReload", $scope.getRadiusServers);
}]);
