/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2015-07-16 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *     Add statistics
 * 2015-01-20 Cornelius Kölbel, <cornelius@privacyidea.org>
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
myApp.controller("auditController", function (AuditFactory, $scope,
                                              $stateParams, $http,
                                              AuthFactory, instanceUrl,
                                              $location, gettextCatalog) {
    $scope.params = {sortorder: "desc",
                     page_size: 10,
                     page: 1};
    $scope.instanceUrl = instanceUrl;
    $scope.statsTime = {7: "Last Week",
        28: "Last 4 Weeks"};
    $scope.dateFormat = gettextCatalog.getString("M/d/yy HH:mm:ss");

    if ($location.path() === "/audit/statistics") {
        $scope.getStatistics();
    }

    // If the state is called with some filter values
    if ($stateParams.serial) {
        $scope.serialFilter = $stateParams.serial;
    }
    if ($stateParams.user) {
        $scope.userFilter = $stateParams.user;
    }

    // get statistics
    $scope.getStatistics = function() {
        AuditFactory.statistics($scope.params, function(data) {
            $scope.stats = data.result.value;
            console.log($scope.stats);
        });
    };

    $scope.getParams = function () {
        $scope.params.serial = "*" + ($scope.serialFilter || "") + "*";
        $scope.params.user = "*" + ($scope.userFilter || "") + "*";
        $scope.params.administrator = "*" + ($scope.administratorFilter || "") + "*";
        $scope.params.tokentype = "*" + ($scope.typeFilter || "") + "*";
        $scope.params.action = "*" + ($scope.actionFilter || "") + "*";
        $scope.params.success = "*" + ($scope.successFilter || "") + "*";
        $scope.params.action_detail = "*" + ($scope.action_detailFilter || "") + "*";
        $scope.params.realm = "*" + ($scope.realmFilter || "") + "*";
        $scope.params.resolver = "*" + ($scope.resolverFilter || "") + "*";
        $scope.params.client = "*" + ($scope.clientFilter || "") + "*";
        $scope.params.privacyidea_server = "*" + ($scope.serverFilter || "") + "*";
        $scope.params.info = "*" + ($scope.infoFilter || "") + "*";
        $scope.params.date = "*" + ($scope.dateFilter || "") + "*";
        console.log("Request Audit Trail with params");
        console.log($scope.params);
    };

    $scope.getAuditList = function () {
        $scope.getParams();
        AuditFactory.get($scope.params, function(data) {
            $scope.auditdata = data.result.value;
            console.log($scope.auditdata);
        });
    };

    // Change the pagination
    $scope.pageChanged = function () {
        console.log('Page changed to: ' + $scope.params.page);
        $scope.getAuditList();
    };

    // download function
    $scope.download = function () {
        var filename = "audit.csv";
        console.log("download audit log");
        $scope.getParams();
        AuditFactory.download($scope.params, filename, function(data){
            alert("Data received.")
        });
    };

    if ($location.path() === "/audit/log") {
        $scope.getAuditList();
    }

    if ($location.path() === "/audit") {
        $location.path("/audit/log");
    }

});
