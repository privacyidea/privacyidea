angular.module("privacyideaApp")
    .controller("registerController",
                            function (Idle,
                                      $scope, $http, $location,
                                      authUrl, RegisterFactory, $rootScope,
                                      $state, inform, gettextCatalog,
                                      hotkeys,
                                      instanceUrl) {

    $scope.instanceUrl = instanceUrl;
    $scope.newUser = {};

    $scope.registerUser = function () {
        RegisterFactory.register($scope.newUser, function() {
            inform.add(gettextCatalog.getString("User account created. An" +
                " Email has been sent to you."), {type: "info"})
        })
    };
});
