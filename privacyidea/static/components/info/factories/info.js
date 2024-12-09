
myApp.factory("InfoFactory", ["AuthFactory", "$http", "$state", "$rootScope",
    "infoUrl",
    function (AuthFactory, $http, $state, $rootScope,
              infoUrl) {
        /**
         Each service - just like this service factory - is a singleton.
         */
        return {
            getRSS: function (callback) {
                $http.get(infoUrl + "/rss", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data.result.value)
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            }
        };
    }]);
