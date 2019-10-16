angular.module("privacyideaApp")
    .controller("recoveryController",
                            function (Idle,
                                      $scope, $http, $location,
                                      authUrl, $rootScope,
                                      $state, inform, gettextCatalog,
                                      hotkeys, $stateParams,
                                      RecoveryFactory,
                                      instanceUrl) {

    $scope.instanceUrl = instanceUrl;
    $scope.newUser = {};
    $scope.params = {recoverycode: $stateParams.recoverycode,
                     user: $stateParams.user};

    $scope.sendRecoveryCodeAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["always"],
            gettextCatalog.getString("Send Password Recovery Code"),
            gettextCatalog.getString(
                "An email will be sent to you with instructions to reset your password. Proceed?"),
            gettextCatalog.getString("Send Code"),
            $scope.sendRecoveryCode);
    };

    $scope.sendRecoveryCode = function () {
        RecoveryFactory.recover($scope.newUser, function(data) {
            //debug: console.log(data);
            inform.add(gettextCatalog.getString("An Email to reset the" +
                " password has been sent to you."), {type: "info"});
        })
    };

    $scope.resetPasswordAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["easy"],
            gettextCatalog.getString("Password Reset"),
            gettextCatalog.getString("Your password will be reset. Proceed?"),
            gettextCatalog.getString("Reset Password"),
             $scope.resetPassword);
    };

    $scope.resetPassword = function () {
        RecoveryFactory.reset($scope.params, function(data) {
            //debug: console.log(data);
            $scope.params = {};
            if (data.result.value) {
                inform.add(gettextCatalog.getString("Your password has been" +
                    " reset successfully.", {type: "success"}))
            } else {
                inform.add(gettextCatalog.getString("Failed to reset your" +
                    " password.", {type: "danger"}))
            }
            $state.go("login");
        })
    };
});
