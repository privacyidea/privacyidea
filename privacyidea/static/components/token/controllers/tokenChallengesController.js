
myApp.controller("tokenChallengesController", function ($scope,
                                                    TokenFactory, UserFactory,
                                                    $stateParams,
                                                    $state, $rootScope,
                                                    ValidateFactory,
                                                    AuthFactory) {
    $scope.tokenSerial = "";
    // This is the parents object
    $scope.loggedInUser = AuthFactory.getUser();
    $scope.params = {page: 1};
    $scope.form = {options: {}};

    // scroll to the top of the page
    document.body.scrollTop = document.documentElement.scrollTop = 0;

    // define functions
    $scope.get = function () {
        $scope.params.serial = "*" + ($scope.serialFilter || "") + "*";
        if ($scope.reverse) {
            $scope.params.sortdir = "desc";
        } else {
            $scope.params.sortdir = "asc";
        }
        TokenFactory.getChallenges(function (data) {
            $scope.challengedata = data.result.value;
            console.log(data.result.value);
        }, $scope.params.serial, $scope.params);
    };

    // Change the pagination
    $scope.challengePageChanged = function () {
        console.log('Page changed to: ' + $scope.params.page);
        $scope.get();
    };

    $scope.get();

    $scope.return_to = function () {
        // After deleting the token, we return here.
        // history.back();
        $state.go($rootScope.previousState.state,
            $rootScope.previousState.params);
    };

    // initialize
    $scope.get();

});
