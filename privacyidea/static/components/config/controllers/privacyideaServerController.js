/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2017-08-24 Cornelius Kölbel, <cornelius@privacyidea.org>
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
myApp.controller("privacyideaServerController", ["$scope", "$stateParams", "inform",
                                                 "gettextCatalog", "$state",
                                                 "$location", "ConfigFactory",
                                                 function($scope, $stateParams,
                                                          inform, gettextCatalog,
                                                          $state, $location,
                                                          ConfigFactory) {
    // Set the default route
    if ($location.path() === "/config/privacyideaserver") {
        $location.path("/config/privacyideaserver/list");
    }

    // Get all servers
    $scope.getPrivacyideaServers = function (identifier) {
        ConfigFactory.getPrivacyidea(function(data) {
            $scope.privacyideaServers = data.result.value;
            //debug: console.log("Fetched all privacyidea servers");
            //debug: console.log($scope.privacyideaServers);
            // return one single privacyIDEA server
            if (identifier) {
                $scope.params = $scope.privacyideaServers[identifier];
                $scope.params["identifier"] = identifier;
            }
        });
    };

    if ($location.path() === "/config/privacyideaserver/list") {
    // in case of list we fetch all servers
        $scope.getPrivacyideaServers();
    }

    $scope.identifier = $stateParams.identifier;
    if ($scope.identifier) {
        // We are editing an existing privacyIDEA Server
        $scope.getPrivacyideaServers($scope.identifier);
        } else {
        // This is a new privacyIDEA server
        $scope.params = {
            tls: true
        }
    }

    $scope.delPrivacyideaServer = function (identifier) {
        ConfigFactory.delPrivacyidea(identifier, function(data) {
            $scope.getPrivacyideaServers();
        });
    };

    $scope.addPrivacyideaServer = function (params) {
        ConfigFactory.addPrivacyidea(params, function(data) {
            $scope.getPrivacyideaServers();
        });
    };

    $scope.testPrivacyideaServer = function() {
        ConfigFactory.testPrivacyidea($scope.params, function(data) {
           if (data.result.value === true) {
               inform.add(gettextCatalog.getString("Request to remote" +
                       " privacyIDEA server successful."),
                   {type: "info"});
           }
        });
    };

    $scope.savePrivacyideaServer= function() {
        ConfigFactory.addPrivacyidea($scope.params, function(data){
            if (data.result.status === true) {
                inform.add(gettextCatalog.getString("privacyIDEA Server" +
                        " Config saved."),
                                {type: "info"});
                $state.go('config.privacyideaserver.list');
            }
        });
    };

    // listen to the reload broadcast
    $scope.$on("piReload", $scope.getPrivacyideaServers);

}]);
