myApp.factory("RecoveryFactory", function ($http, $state, $rootScope,
                                           recoveryUrl, inform) {
    /**
     Each service - just like this service factory - is a singleton.
     */
    var error_func = function (error) {
        if (error.result.error.code === -401) {
            $state.go('recovery');
        } else {
            inform.add(error.result.error.message, {
                type: "danger",
                ttl: 10000
            });
        }
    };

    return {
        recover: function (params, callback) {
            // THis sends the recovery code to reset the password
            $http.post(recoveryUrl, params, {}
            ).success(callback
            ).error(error_func);
        },
        reset: function (params, callback) {
            $http.post(recoveryUrl + "/reset", params, {}
            ).success(callback).error(error_func);
        }
    };
});
