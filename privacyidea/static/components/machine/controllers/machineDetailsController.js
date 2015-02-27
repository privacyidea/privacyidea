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
    .controller("machineDetailsController", function ($scope, MachineFactory) {
        $scope.tokensPerPage = 5;
        $scope.newToken = {"serial": "", pin: ""};
        $scope.params = {page: 1};
        // scroll to the top of the page
        document.body.scrollTop = document.documentElement.scrollTop = 0;

        $scope._getMachineToken = function () {
        };
        $scope._getMachineApplication = function () {
        };

        // Change the pagination
        $scope.pageChanged = function () {
            console.log('Page changed to: ' + $scope.params.page);
            $scope._getMachineToken();
        };

        $scope.getMachineDetails = function () {
            MachineFactory.getMachines({
                id: $scope.machineid,
                resolver: $scope.machineresolver},
            function (data) {
                $scope.machine = data.result.value[0];
            })
        };

        $scope.getMachineDetails();

    });
