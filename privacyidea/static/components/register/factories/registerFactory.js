myApp.factory("RegisterFactory", function ($http, $state, $rootScope,
                                           registerUrl, inform) {
    /**
     Each service - just like this service factory - is a singleton.
     */
    var error_func = function (error) {
        if (error.result.error.code === -401) {
            $state.go('register');
        } else {
            inform.add(error.result.error.message, {
                type: "danger",
                ttl: 10000
            });
        }
    };

    return {
        register: function (params, callback) {
            $http.post(registerUrl, params, {}
            ).success(callback
            ).error(error_func);
        },
        status: function (callback) {
            $http.get(registerUrl).success(callback).error(error_func);
        }
    };
});
