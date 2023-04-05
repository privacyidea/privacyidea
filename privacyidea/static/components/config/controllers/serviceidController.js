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
                                         "gettextCatalog", "$state",
                                         "$location", "ConfigFactory",
                                         function($scope, $stateParams,
                                                  inform, gettextCatalog,
                                                  $state, $location,
                                                  ConfigFactory) {
    // Set the default route
    if ($location.path() === "/config/serviceid") {
        $location.path("/config/serviceid/list");
    }


    // Get all services
    $scope.getServiceids = function () {
        ConfigFactory.getServiceid("", function(data) {
            $scope.serviceids = data.result.value;
        });
    };
    // get one special service
    $scope.getServiceid = function (sname) {
        ConfigFactory.getServiceid(sname, function(data){
            var serviceids = data.result.value
            $scope.params.servicename = sname;
            $scope.params.description = serviceids[sname].description;
            $scope.params.id = serviceids[sname].id;
        });
    }

    if ($location.path() === "/config/serviceid/list") {
        // In the case of list, we fetch all Service IDs
        $scope.getServiceids();
    }

    $scope.servicename = $stateParams.servicename;
    if ($scope.servicename) {
        // We are editing an existing Service ID
        $scope.getServiceid($scope.servicename);
    } else {
        // This is a new service
        $scope.params = { };
    }

    $scope.delServiceid = function (sname) {
        ConfigFactory.delServiceid(sname, function(data) {
            $scope.getServiceids();
        });
    };

    $scope.saveServiceid = function() {
        ConfigFactory.addServiceid($scope.params, function(data){
            if (data.result.status === true) {
                inform.add(gettextCatalog.getString("Service ID saved."),
                                {type: "info"});
                $state.go('config.serviceid.list');
            }
        });
    };

    // listen to the reload broadcast
    $scope.$on("piReload", $scope.getServiceids);
}]);
