myApp.factory("RegisterFactory", ['$http', '$state', '$rootScope',
                                  'registerUrl', 'AuthFactory',
                                  function ($http, $state, $rootScope,
                                            registerUrl, AuthFactory) {
    /**
     Each service - just like this service factory - is a singleton.
     */
    return {
        register: function (params, callback) {
            $http.post(registerUrl, params, {}
            ).then(function (response) { callback(response.data) },
                function(error) { AuthFactory.authError(error.data) });
        },
        status: function (callback) {
            $http.get(registerUrl).then(function (response) { callback(response.data) },
                function(error) { AuthFactory.authError(error.data) });
        }
    };
}]);
