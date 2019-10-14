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

    $scope.registerUserAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["easy"],
            "Register Account",
            "Please make sure the entered info is correct before proceeding.",
            "Register",
            $scope.registerUser);
    };

    $scope.registerUser = function () {
        RegisterFactory.register($scope.newUser, function() {
            inform.add(gettextCatalog.getString("User account created. An" +
                " Email has been sent to you."), {type: "info"})
        })
    };
});
