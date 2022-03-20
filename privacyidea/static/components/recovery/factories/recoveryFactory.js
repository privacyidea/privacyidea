myApp.factory("RecoveryFactory", ['$http', '$state', '$rootScope',
                                  'recoveryUrl',
                                  function ($http, $state, $rootScope,
                                            recoveryUrl) {
    /**
     Each service - just like this service factory - is a singleton.
     */
    return {
        recover: function (params, callback) {
            // THis sends the recovery code to reset the password
            $http.post(recoveryUrl, params, {}
            ).then(function (response) { callback(response.data) },
                function(error) { AuthFactory.authError(error.data) });
        },
        reset: function (params, callback) {
            $http.post(recoveryUrl + "/reset", params, {}
            ).then(function (response) { callback(response.data) },
                function(error) { AuthFactory.authError(error.data) });
        }
    };
}]);
