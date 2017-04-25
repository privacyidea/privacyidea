/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2015-03-03 Cornelius Kölbel, <cornelius@privacyidea.org>
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

myApp.controller("ldapMachineResolverController", function ($scope,
                                                      ConfigFactory, inform,
                                                      $state, $stateParams) {
    $scope.params = {
        type: 'ldap',
        AUTHTYPE: "Simple",
        TLS_VERIFY: true,
        START_TLS: true
    };
    $scope.authtypes = ["Simple", "SASL Digest-MD5"];


    $scope.resolvername = $stateParams.resolvername;
    if ($scope.resolvername) {
        /* If we have a resolvername, we do an Edit
         and we need to fill all the $scope.params */
        ConfigFactory.getMachineResolver($scope.resolvername, function (data) {
            var resolver = data.result.value[$scope.resolvername];
            $scope.params = resolver.data;
            $scope.params.type = 'ldap';
            $scope.params.NOREFERRALS = isTrue($scope.params.NOREFERRALS);
            $scope.params.TLS_VERIFY = isTrue($scope.params.TLS_VERIFY);
            $scope.params.START_TLS = isTrue($scope.params.START_TLS);
        });
    }

    $scope.presetAD = function () {
        $scope.params.SEARCHFILTER = "(objectClass=computer)";
        //$scope.params.IDATTRIBUTE = "objectSid";
        $scope.params.IDATTRIBUTE = "DN";
        $scope.params.IPATTRIBUTE = "";
        $scope.params.HOSTNAMEATTRIBUTE = "dNSHostName";
        $scope.params.NOREFERRALS = true;
    };

    $scope.setLDAPMachineResolver = function () {
        ConfigFactory.setMachineResolver($scope.resolvername, $scope.params, function (data) {
            $scope.set_result = data.result.value;
            $scope.getMachineResolvers();
            $state.go("config.mresolvers.list");
        });
    };

    $scope.testResolver = function () {
        ConfigFactory.testMachineResolver($scope.params, function (data) {
            if (data.result.value === true) {
                inform.add(data.detail.description,
                    {type: "success", ttl: 10000});
            } else {
                inform.add(data.detail.description,
                    {type: "danger", ttl: 10000});
            }
        });
    };

});

