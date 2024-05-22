myApp.factory("ContainerFactory", ['AuthFactory', '$http', 'containerUrl', '$q', '$state', '$rootScope',
    function (AuthFactory, $http, containerUrl, $q, $state, $rootScope) {
        let canceller = $q.defer();
        return {
            getContainers: function (params, callback) {
                canceller.resolve();
                canceller = $q.defer();
                $http.get(containerUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    params: params,
                    timeout: canceller.promise
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data);
                });
            },
            getContainerForSerial: function (serial, callback) {
                $http.get(containerUrl + "/?serial=" + serial, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data)
                }, function(error) {
                    AuthFactory.authError(error.data)
                });
            },
            getContainerTypes: function (callback) {
                canceller.resolve();
                canceller = $q.defer();
                $http.get(containerUrl + "/types", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    timeout: canceller.promise
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data);
                });
            },
            createContainer: function (params, callback) {
                canceller.resolve();
                canceller = $q.defer();
                $http.post(containerUrl + "/init", params, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    timeout: canceller.promise
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data);
                });
            },
            addTokenToContainer: function (params, callback) {
                $http.post(containerUrl + "/" + params["serial"] + "/add", {serial: params["tokenSerial"]},
                    {
                        headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function (response) {
                    callback(response.data)
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            addAllTokenToContainer: function (params, callback) {
                $http.post(containerUrl + "/" + params["container_serial"] + "/add", {serial_list: params["serial_list"]},
                    {
                        headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function (response) {
                    callback(response.data)
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            removeTokenFromContainer: function (params, callback) {
                $http.post(containerUrl + "/" + params["serial"] + "/remove", {serial: params["tokenSerial"]},
                    {
                        headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function (response) {
                    callback(response.data)
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            assignUser: function (params, callback) {
                $http.post(containerUrl + "/assign", params,
                    {
                        headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function (response) {
                    callback(response.data)
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            unassignUser: function (params, callback) {
                $http.post(containerUrl + "/unassign", params,
                    {
                        headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                    }).then(function (response) {
                    callback(response.data)
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            },
            getContainerForUser: function (params, callback) {
                $http.get(containerUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    params: params
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data);
                });
            },
            getContainerForUser: function (params, callback) {
                $http.get(containerUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    params: params
                }).then(function (response) {
                    callback(response.data);
                }, function (error) {
                    AuthFactory.authError(error.data);
                });
            },
        }
    }]);