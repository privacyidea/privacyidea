/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2016-09-01 Cornelius Kölbel <cornelius.koelbel@netknights.it>
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
myApp.controller("componentController", function (ComponentFactory, $scope,
                                              $stateParams, $http,
                                              AuthFactory, instanceUrl,
                                              $location) {
    $scope.instanceUrl = instanceUrl;

    $scope.getClientType = function () {
        console.log("Requesting client application types.");
        ComponentFactory.getClientType(function(data) {
            $scope.clientdata = data.result.value;
            console.log($scope.clientdata);
        });
    };

    if ($location.path() === "/component/clienttype") {
        $scope.getClientType();
    }


    if ($location.path() === "/component") {
        $location.path("/component/clienttype");
    }


});
