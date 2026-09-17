
myApp.controller("tokenChallengesController", ['$scope', 'TokenFactory',
                                               'UserFactory', '$stateParams',
                                               '$state', '$rootScope',
                                               'ValidateFactory', 'AuthFactory',
                                               'inform', 'gettextCatalog',
                                               function ($scope, TokenFactory,
                                                         UserFactory, $stateParams,
                                                         $state, $rootScope,
                                                         ValidateFactory,
                                                         AuthFactory, inform, gettextCatalog) {
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
        $scope.params.sortby = $scope.sortby;
        if ($scope.reverse) {
            $scope.params.sortdir = "desc";
        } else {
            $scope.params.sortdir = "asc";
        }
        TokenFactory.getChallenges(function (data) {
            $scope.challengedata = data.result.value;
            //debug: console.log(data.result.value);
        }, $scope.params.serial, $scope.params);
    };

    // Change the pagination
    $scope.challengePageChanged = function () {
        //debug: console.log('Page changed to: ' + $scope.params.page);
        $scope.get();
    };

    $scope.deleteExpiredChallenges = function () {
        TokenFactory.deleteExpiredChallenges(function (data) {
            if (data.result.status === true) {
                if (data.result.value.deleted > 0) {
                    inform.add(gettextCatalog.getString(
                            "Total expired challenges deleted: " + data.result.value.deleted),
                        {type: "success", ttl: 4000});
                } else {
                    inform.add(gettextCatalog.getString(
                            "No expired challenges were deleted."),
                        {type: "info", ttl: 4000});
                }
                $scope.get(); // Refresh data after successful deletion
            } else {
                inform.add(gettextCatalog.getString(
                        "Could not delete expired challenges."),
                    {type: "danger", ttl: 8000});
            }
        });
    };

    $scope.return_to = function () {
        // After deleting the token, we return here.
        // history.back();
        $state.go($rootScope.previousState.state,
            $rootScope.previousState.params);
    };

    // initialize
    $scope.get();

    // listen to the reload broadcast
    $scope.$on("piReload", $scope.get);

}]);
