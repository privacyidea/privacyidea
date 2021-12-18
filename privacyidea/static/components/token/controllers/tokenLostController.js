myApp.controller("tokenLostController", ['$scope', 'TokenFactory',
                                         'UserFactory', '$stateParams',
                                         function ($scope, TokenFactory,
                                                   UserFactory, $stateParams) {
    $scope.selectedToken.serial = $stateParams.tokenSerial;
    $scope.tokenLost = false;

    $scope.setTokenLost = function() {
        TokenFactory.lost($scope.selectedToken.serial, function (data) {
            $scope.tokenLost = true;
            $scope.lostResult = data.result.value;
        });
    };
}]);
