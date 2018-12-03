myApp.factory("RecoveryFactory", function ($http, $state, $rootScope,
                                           recoveryUrl, inform) {
    /**
     Each service - just like this service factory - is a singleton.
     */
    return {
        recover: function (params, callback) {
            // THis sends the recovery code to reset the password
            $http.post(recoveryUrl, params, {}
            ).success(callback
            ).error(AuthFactory.authError);
        },
        reset: function (params, callback) {
            $http.post(recoveryUrl + "/reset", params, {}
            ).success(callback).error(AuthFactory.authError);
        }
    };
});
