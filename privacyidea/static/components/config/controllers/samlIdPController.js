/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2016-03-08 Cornelius Kölbel, <cornelius@privacyidea.org>
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
myApp.controller("samlIdPController", function($scope, $stateParams,
                                               inform, gettextCatalog,
                                               $state, $location,
                                               ConfigFactory) {
    if ($location.path() === "/config/saml") {
        $location.path("/config/saml/list");
    }

    $scope.identifier = $stateParams.identifier;
    if ($scope.identifier) {
        // We are editing an existing SAML IdP
        $scope.getSAMLIdPs($scope.identifier);
    }

    // Get all servers
    $scope.getSAMLIdPs = function (identifier) {
        ConfigFactory.getSAML(function(data) {
            $scope.samlIdPs = data.result.value;
            console.log("Fetched all SAML IdPs");
            console.log($scope.samlIdPs);
            // return one single SAML IdP
            if (identifier) {
                $scope.params = $scope.samlIdPs[identifier];
                $scope.params["identifier"] = identifier;
            }
        });
    };

    $scope.delSAMLIdP = function (identifier) {
        ConfigFactory.delSAML(identifier, function(data) {
            $scope.getSAMLIdPs();
        });
    };

    $scope.addSAMLIdP = function (params) {
        ConfigFactory.addSAML(params, function(data) {
            $scope.getSAMLIdPs();
        });
    };

    $scope.getSAMLIdPs();

    $scope.saveSAMLIdP = function() {
        ConfigFactory.addSAML($scope.params, function(data){
            if (data.result.status === true) {
                inform.add(gettextCatalog.getString("SAML IdP Config saved."),
                                {type: "info"});
                $state.go('config.saml.list');
            }
        });
    };

});
