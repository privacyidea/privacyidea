/**
 *
 * 2022-09-29 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
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
myApp.controller("tokengroupController", ["$scope", "$stateParams", "inform",
    "gettextCatalog", "$state", "$location", "ConfigFactory",
    function ($scope, $stateParams, inform, gettextCatalog, $state, $location, ConfigFactory) {
        // Set the default route
        if ($location.path() === "/config/tokengroup") {
            $location.path("/config/tokengroup/list");
        }

        // Get all groups
        $scope.getTokengroups = function () {
            ConfigFactory.getTokengroup("", function (data) {
                $scope.tokengroups = data.result.value;
            });
        };

        // get one special group
        $scope.groupname = $stateParams.groupname;
        $scope.params = {};
        $scope.getTokengroup = function () {
            if ($scope.groupname) {
                ConfigFactory.getTokengroup($scope.groupname, function (data) {
                    let group = data.result.value
                    $scope.params.groupname = $scope.groupname;
                    $scope.params.description = group[$scope.groupname].description;
                    $scope.params.id = group[$scope.groupname].id;
                });
            }
        }

        if ($location.path() === "/config/tokengroup/list") {
            // In the case of list, we fetch all radius servers
            $scope.getTokengroups();
        }

        if ($scope.groupname) {
            // We are editing an existing Tokengroup
            $scope.getTokengroup($scope.groupname);
        }

        $scope.delTokengroup = function (groupname) {
            ConfigFactory.delTokengroup(groupname, function (data) {
                $scope.getTokengroups();
            });
        };

        $scope.saveTokengroup = function () {
            ConfigFactory.addTokengroup($scope.params, function (data) {
                if (data.result.status === true) {
                    inform.add(gettextCatalog.getString("Tokengroup saved."),
                        {type: "info"});
                    $scope.deselectTokenGroup();
                    $state.go('config.tokengroup.list');
                    $scope.reload();
                }
            });
        };

        $scope.deselectTokenGroup = function () {
            $scope.groupname = null;
            $scope.params = {};
        };

        $scope.editTokengroup = function (groupName) {
            $scope.groupname = groupName;
            $scope.getTokengroup();
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getTokengroups);
        $scope.$on("piReload", $scope.getTokengroup);
    }]);
