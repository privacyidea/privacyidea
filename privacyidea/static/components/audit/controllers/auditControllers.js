/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2018-11-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *            Remove audit based statistics
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
myApp.controller("auditController", ["AuditFactory", "$scope", "$rootScope",
    "$stateParams", "$http", "AuthFactory",
    "instanceUrl", "$location",
    function (AuditFactory, $scope, $rootScope,
              $stateParams, $http, AuthFactory,
              instanceUrl, $location) {
        $scope.params = {
            sortorder: "desc",
            page_size: $scope.audit_page_size,
            page: 1
        };
        $scope.instanceUrl = instanceUrl;
        $scope.dateFormat = "yyyy-MM-dd HH:mm:ss";

        $scope.filter = {};

        // If the state is called with some filter values
        if ($stateParams.serial) {
            $scope.filter.serial = $stateParams.serial;
        }
        if ($stateParams.user) {
            $scope.filter.user = $stateParams.user;
        }

        $scope.getParams = function () {
            $scope.params.serial = "*" + ($scope.filter.serial || "") + "*";
            $scope.params.user = "*" + ($scope.filter.user || "") + "*";
            $scope.params.administrator = "*" + ($scope.filter.administrator || "") + "*";
            $scope.params.token_type = "*" + ($scope.filter.type || "") + "*";
            $scope.params.action = "*" + ($scope.filter.action || "") + "*";
            $scope.params.success = "*" + ($scope.filter.success || "") + "*";
            $scope.params.authentication = "*" + ($scope.filter.authentication || "") + "*";
            $scope.params.action_detail = "*" + ($scope.filter.action_detail || "") + "*";
            $scope.params.realm = "*" + ($scope.filter.realm || "") + "*";
            $scope.params.resolver = "*" + ($scope.filter.resolver || "") + "*";
            $scope.params.policies = "*" + ($scope.filter.policies || "") + "*";
            $scope.params.client = "*" + ($scope.filter.client || "") + "*";
            $scope.params.user_agent = "*" + ($scope.filter.user_agent || "") + "*";
            $scope.params.user_agent_version = "*" + ($scope.filter.user_agent_version || "") + "*";
            $scope.params.privacyidea_server = "*" + ($scope.filter.server || "") + "*";
            $scope.params.info = "*" + ($scope.filter.info || "") + "*";
            $scope.params.date = "*" + ($scope.filter.date || "") + "*";
            $scope.params.startdate = "*" + ($scope.filter.startdate || "") + "*";
            $scope.params.duration = "*" + ($scope.filter.duration || "") + "*";
            $scope.params.container_serial = "*" + ($scope.filter.containerSerial || "") + "*";
            $scope.params.container_type = "*" + ($scope.filter.containerType || "") + "*";
            //debug: console.log("Request Audit Trail with params");
            //debug: console.log($scope.params);
        };

        $scope.getAuditList = function (live_search) {
            if ((!$rootScope.search_on_enter) || ($rootScope.search_on_enter && !live_search)) {
                $scope.getParams();
                AuditFactory.get($scope.params, function (data) {
                    $scope.auditdata = data.result.value;
                    $scope.audit_columns = data.result.value.auditcolumns;
                    // We split the policies, which come as comma separated string to an array.
                    angular.forEach($scope.auditdata.auditdata, function (auditentry, key) {
                        if ($scope.auditdata.auditdata[key].policies != null) {
                            const polname_list = $scope.auditdata.auditdata[key].policies.split(",");
                            // Duplicates in a repeater are not allowed!
                            let uniquePolnameList = [];
                            angular.forEach(polname_list, function (pol, i) {
                                if (uniquePolnameList.includes(pol) === false) uniquePolnameList.push(pol);
                            });
                            $scope.auditdata.auditdata[key].policies = uniquePolnameList;
                        }
                        if (auditentry.serial != null) {
                            auditentry.serial_list = auditentry.serial.split(",");
                        }
                    });
                });
            }
        };

        // Change the pagination
        $scope.pageChanged = function () {
            //debug: console.log('Page changed to: ' + $scope.params.page);
            $scope.getAuditList();
        };

        // download function
        $scope.download = function () {
            const filename = "audit.csv";
            //debug: console.log("download audit log");
            $scope.getParams();
            AuditFactory.download($scope.params, filename, function (data) {
                alert("Data received.")
            });
        };

        if ($location.path() === "/audit") {
            $location.path("/audit/log");
        }

        if ($location.path() === "/audit/log") {
            $scope.getAuditList();
        }

        $scope.$on("piReload", function () {
            if ($location.path() === "/audit/log") {
                $scope.getAuditList();
            }
        });

    }]);
