
myApp.controller("tokenApplicationsController", ['$scope', 'TokenFactory', 'MachineFactory',
                                               'UserFactory', '$stateParams',
                                               '$state', '$rootScope',
                                               'ValidateFactory', 'AuthFactory', 'gettextCatalog',
                                               function ($scope, TokenFactory, MachineFactory,
                                                         UserFactory, $stateParams,
                                                         $state, $rootScope,
                                                         ValidateFactory,
                                                         AuthFactory, gettextCatalog) {
    $scope.tokenSerial = "";
    // This is the parents object
    $scope.loggedInUser = AuthFactory.getUser();
    $scope.form = {filter: {}};
    $scope.sortby = "serial";
    $scope.reverse = false;
    $scope.formInit = {
        applications: {"ssh": gettextCatalog.getString("SSH: Attaching ssh keys to services."),
            "offline": gettextCatalog.getString("offline: Use HOTP token for offline login to notebooks.")
        }}

    // scroll to the top of the page
    document.body.scrollTop = document.documentElement.scrollTop = 0;

    // define functions
    $scope.changeApplication = function() {
        $scope.get();
    };
    // Change the pagination
    $scope.pageChanged = function () {
        //debug: console.log('Page changed to: ' + $scope.params.page);
        $scope.get();
    };

    $scope.get = function (live_search) {
        if ((!$rootScope.search_on_enter) || ($rootScope.search_on_enter && !live_search)) {
            $scope.params = {};
            $scope.params.application = $scope.currentApplication;
            for (kf in $scope.form.filter) {
                $scope.params[kf] = "*" + ($scope.form.filter[kf] || "") + "*";
            }
            $scope.params.pagesize = 15;
            $scope.params.sortby = this.sortby;
            if (this.reverse) {
                $scope.params.sortdir = "desc";
            } else {
                $scope.params.sortdir = "asc";
            }

            MachineFactory.getMachineTokens($scope.params, function (data) {
                $scope.machinetokens = data.result.value;
            });
        }
    };

    // Change the pagination
    $scope.machinetokenPageChanged = function () {
        //debug: console.log('Page changed to: ' + $scope.params.page);
        $scope.get();
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
