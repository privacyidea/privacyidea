/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2015-02-27 Cornelius Kölbel, <cornelius@privacyidea.org>
 *            Add Machines to Web UI
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

angular.module("privacyideaApp")
    .controller("machineController", ['$scope', '$location', 'machineUrl',
                                      'realmUrl', '$rootScope', 'MachineFactory',
                                      '$stateParams',
                                      function ($scope, $location, machineUrl,
                                                realmUrl, $rootScope,
                                                MachineFactory, $stateParams) {

        $scope.machinesPerPage = 15;
        $scope.params = {page: 1,
                         hostnameFilter: "",
                         ipFilter: "",
                         resolverFilter: ""};
        // scroll to the top of the page
        document.body.scrollTop = document.documentElement.scrollTop = 0;
        // go to the list view by default
        if ($location.path() === "/machine") {
            $location.path("/machine/list");
        }

        // listen to the reload broadcast
        $scope.$on("piReload", function() {
            $scope._getMachines();
        });

        if ($stateParams.resolver) {
            $scope.params.resolverFilter = $stateParams.resolver;
        }

        $scope._getMachines = function () {
            var params = {};
            if ($scope.params.hostnameFilter) {
                params.hostname = $scope.params.hostnameFilter;
            }
            if ($scope.params.ipFilter) {
                params.ip = $scope.params.ipFilter;
            }
            if ($scope.params.idFilter) {
                params.id = $scope.params.idFilter;
            }
            if ($scope.params.resolverFilter) {
                params.resolver = $scope.params.resolverFilter;
            }
            MachineFactory.getMachines(params,
                function (data) {
                    var machinelist = data.result.value;
                    // The machinelist is the complete list of all machines!
                    $scope.machinecount = machinelist.length;
                    var start = ($scope.params.page - 1) * $scope.machinesPerPage;
                    var stop = start + $scope.machinesPerPage;
                    $scope.machinelist = machinelist.slice(start, stop);
                });
        };

        $scope._getMachines();

        // Change the pagination
        $scope.pageChanged = function () {
            //debug: console.log('Page changed to: ' + $scope.params.page);
            $scope._getMachines();
        };

    }]);
