/**
 * http://www.privacyidea.org
 *
 * 2020-05-14 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
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


myApp.controller("dashboardController", function (ConfigFactory, TokenFactory,
                                              SubscriptionFactory, AuditFactory,
                                              $scope, $location, AuthFactory,
                                              instanceUrl,
                                              $rootScope, gettextCatalog,
                                              hotkeys) {

    $scope.tokens = {};
    $scope.policies = {"active": [], "num_active": 0,
                       "inactive": [], "num_inactive": 0};
    $scope.events = {"active": [], "num_active": 0,
                     "inactive": [], "num_inactive": 0};
    $scope.subscriptions = {};
    $scope.authentications = {"success": 0, "fail": 0};

    $scope.get_total_token_number = function () {
        TokenFactory.getTokens(function (data) {
                if (data) {
                    $scope.tokens.total = data.result.value.count;
                }
            }, {});
    };

    $scope.get_policies = function () {
        ConfigFactory.getPolicies(function(data) {
            $scope.policies = {"active": [], "num_active": 0,
                       "inactive": [], "num_inactive": 0};
            var policies = data.result.value;
            angular.forEach(policies, function(policy) {
                if (policy.active) {
                    $scope.policies.active.push(policy.name);
                    $scope.policies.num_active += 1;
                } else {
                    $scope.policies.inactive.push(policy.name);
                    $scope.policies.num_inactive += 1;
                }
            });
        });
    };

    $scope.get_events = function () {
        $scope.events = {"active": [], "num_active": 0,
                     "inactive": [], "num_inactive": 0};
        ConfigFactory.getEvents(function(data) {
            var events = data.result.value;
            angular.forEach(events, function(event) {
                if (event.active) {
                    $scope.events.active.push(event);
                    $scope.events.num_active += 1;
                } else {
                    $scope.events.inactive.push(event);
                    $scope.events.num_inactive += 1;
                }
            });
        });
    };


     $scope.getSubscriptions = function() {
        SubscriptionFactory.get(function (data) {
            $scope.subscriptions = data.result.value;
        });
     };

     $scope.getAuthentication = function () {
        $scope.authentications = {"success": 0, "fail": 0};
        AuditFactory.get({"timelimit": "1d", "action": "*validate*"},
            function (data) {
            var authentications = data.result.value.auditdata;
            angular.forEach(authentications, function(authlog) {
                if (authlog.success) {
                    $scope.authentications.succes += 1;
                } else {
                    $scope.authentications.fail += 1;
                }
            });
        });
     };


    $scope.get_total_token_number();
    $scope.get_policies();
    $scope.get_events();
    $scope.getSubscriptions();
    $scope.getAuthentication();

        // listen to the reload broadcast
    $scope.$on("piReload", function() {
        $scope.get_total_token_number();
        $scope.get_policies();
        $scope.get_events();
        $scope.getSubscriptions();
        $scope.getAuthentication();
    });
});