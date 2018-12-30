myApp.factory("RegisterFactory", function ($http, $state, $rootScope,
                                           registerUrl, AuthFactory) {
    /**
     Each service - just like this service factory - is a singleton.
     */
    return {
        register: function (params, callback) {
            $http.post(registerUrl, params, {}
            ).success(callback
            ).error(AuthFactory.authError);
        },
        status: function (callback) {
            $http.get(registerUrl).success(callback).error(AuthFactory.authError);
        }
    };
});
