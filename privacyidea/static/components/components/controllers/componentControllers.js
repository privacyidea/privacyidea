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
                                              SubscriptionFactory, subscriptionsUrl,
                                              $location, $upload, inform) {
    $scope.instanceUrl = instanceUrl;

    $scope.getClientType = function () {
        console.log("Requesting client application types.");
        ComponentFactory.getClientType(function (data) {
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

    /*
    Functions for subscriptions
     */
     $scope.upload = function (files) {
        if (files && files.length) {
            for (var i = 0; i < files.length; i++) {
                var file = files[i];
                $upload.upload({
                    url: subscriptionsUrl + "/",
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    file: file
                }).success(function (data, status, headers, config) {
                    inform.add("File uploaded successfully.",
                        {type: "success", ttl: 3000});
                    $scope.getSubscriptions();
                }).error(function (error) {
                    if (error.result.error.code === -401) {
                        $state.go('login');
                    } else {
                        inform.add(error.result.error.message,
                                {type: "danger", ttl: 10000});
                    }
                });
            }
        }
     };

     $scope.getSubscriptions = function() {
        SubscriptionFactory.get(function (data) {
            $scope.subscriptions = data.result.value;
            console.log($scope.subscriptions);
        });
     };

     $scope.deleteSubscription = function(application) {
         SubscriptionFactory.delete(application, function(data){
             console.log(data);
             inform.add("Subscription deleted successfully.",
                 {type: "info", ttl: 3000});
             $scope.getSubscriptions();
         });

     };

    $scope.getSubscriptions();
});
