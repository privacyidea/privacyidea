angular.module("privacyideaApp")
    .controller("recoveryController",
                            function (Idle,
                                      $scope, $http, $location,
                                      authUrl, $rootScope,
                                      $state, inform, gettextCatalog,
                                      hotkeys,
                                      RecoveryFactory,
                                      instanceUrl) {

    $scope.instanceUrl = instanceUrl;
    $scope.newUser = {};

    $scope.resetPassword = function () {
        alert("reset");
        RecoveryFactory.reset($scope.newUser, function() {
            inform.add(gettextCatalog.getString("An Email to reset the" +
                " password has been sent to you."), {type: "info"})
        })
    };
});
