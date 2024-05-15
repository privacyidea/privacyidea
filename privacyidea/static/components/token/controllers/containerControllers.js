myApp.controller("containerCreateController", ['$scope', '$http', '$q', 'ContainerFactory', '$stateParams',
    'AuthFactory', 'ConfigFactory',

    function createContainerController($scope, $http, $q, ContainerFactory, $stateParams, AuthFactory, ConfigFactory) {
        $scope.formData = {
            containerTypes: {},
        }
        $scope.form = {
            containerType: "generic",
            description: ""
        }
        ContainerFactory.getContainerTypes(function (data) {
            $scope.formData.containerTypes = data.result.value
        })

        $scope.changeContainerType = function () {

        }

        // User+Realm: Get the realms and fill the realm dropdown box
        if (AuthFactory.getRole() === 'admin') {
            ConfigFactory.getRealms(function (data) {
                $scope.realms = data.result.value;
                // Set the default realm
                const size = Object.keys($scope.realms).length;
                angular.forEach($scope.realms, function (realm, realmname) {
                    if (size === 1) {
                        // if there is only one realm, preset it
                        $scope.newUser = {user: "", realm: realmname};
                    }
                    // if there is a default realm, preset the default realm
                    if (realm.default && !$stateParams.realmname) {
                        $scope.newUser = {user: "", realm: realmname};
                        //debug: console.log("tokenEnrollController");
                        //debug: console.log($scope.newUser);
                    }
                });
                // init the user, if token.enroll was called from the user.details
                if ($stateParams.realmname) {
                    $scope.newUser.realm = $stateParams.realmname;
                }
                if ($stateParams.username) {
                    $scope.newUser.user = $stateParams.username;
                    // preset the mobile and email for SMS or EMAIL token
                    UserFactory.getUsers({
                            realm: $scope.newUser.realm,
                            username: $scope.newUser.user
                        },
                        function (data) {
                            $scope.get_user_infos(data)
                        });
                }
            });
        } else if (AuthFactory.getRole() === 'user') {
            // init the user, if token.enroll was called as a normal user
            $scope.newUser.user = AuthFactory.getUser().username;
            $scope.newUser.realm = AuthFactory.getUser().realm;
            if ($scope.checkRight('userlist')) {
                UserFactory.getUserDetails({}, function (data) {
                    $scope.User = $scope.get_user_infos(data);
                });
            }
        }

        $scope.createContainer = function () {
            let ctype = $scope.form.containerType
            let params = {"type": ctype}
            if ($scope.newUser.user) {
                params["user"] = fixUser($scope.newUser.user)
                params["realm"] = $scope.newUser.realm
            }
            if ($scope.form.description) {
                params["description"] = $scope.form.description
            }

            ContainerFactory.createContainer(params, function (data) {
                // TODO where to go after creation?
            })
        }
    }]);

myApp.controller("containerListController", ['$scope', '$http', '$q', 'ContainerFactory', 'AuthFactory', 'ConfigFactory', 'TokenFactory', '$rootScope',
    function containerListController($scope, $http, $q, ContainerFactory, AuthFactory, ConfigFactory, TokenFactory, $rootScope) {
        $scope.loggedInUser = AuthFactory.getUser();
        $scope.params = {sortdir: "asc"};
        $scope.containers = []

        // Get all containers
        $scope.get = function () {

            $scope.params.sortby = $scope.sortby;
            if ($scope.reverse) {
                $scope.params.sortdir = "desc";
            } else {
                $scope.params.sortdir = "asc";
            }

            ContainerFactory.getContainers($scope.params,
                function (data) {
                    $scope.containers = data.result.value
                })

        }
        $scope.get()

        // single token function
        $scope.reset = function (serial) {
            TokenFactory.reset(serial, $scope.get);
        };
        $scope.disable = function (serial) {
            TokenFactory.disable(serial, $scope.get);
        };
        $scope.enable = function (serial) {
            TokenFactory.enable(serial, $scope.get);
        };

        // Expand token view
        $scope.expandedRows = []
        $scope.expandTokenView = function (containerRow) {
            if (containerRow < 0) {
                for (let i = 0; i < $scope.containers.length; i++) {
                    if ($scope.containers[i].tokens_paginated.count > 0) {
                        $scope.expandedRows.push(i)
                    }
                }
            } else {
                $scope.expandedRows.push(containerRow)
            }
        }

        // Collapse token view
        $scope.collapseTokenView = function (containerRow) {
            if (containerRow < 0) {
                while ($scope.expandedRows.length > 0) {
                    $scope.expandedRows.pop()
                }
            } else {
                $scope.expandedRows.splice($scope.expandedRows.indexOf(containerRow), 1)
            }
        }

    }]);

myApp.controller("containerDetailsController", ['$scope', '$http', '$stateParams', '$q', 'ContainerFactory', 'AuthFactory', 'ConfigFactory', 'TokenFactory', '$state', '$rootScope',
    function containerDetailsController($scope, $http, $stateParams, $q, ContainerFactory, AuthFactory, ConfigFactory, TokenFactory, $state, $rootScope) {
        $scope.containerSerial = $stateParams.containerSerial
        $scope.loggedInUser = AuthFactory.getUser();
        $scope.newToken = {"serial": "", pin: ""};

        $scope.container = {}
        $scope.containerOwner = {}
        ContainerFactory.getContainerForSerial($scope.containerSerial, function (data) {
            $scope.container = data.result.value[0]
            $scope.containerOwner = $scope.container.users[0]
        })

        $scope.params.container_serial = $scope.containerSerial
        $scope.tokendata = {}
        TokenFactory.getTokens(
            function (data) {
                $scope.tokendata = data.result.value
            }, $scope.params)

        $scope.enrollToken = function () {
            // go to token.enroll with the users data of the container owner
            $scope.userParams = {}
            if ($scope.containerOwner) {
                $scope.userParams = {
                    realmname: $scope.containerOwner.user_realm,
                    username: $scope.containerOwner.user_name
                }
            }
            $state.go("token.enroll", $scope.userParams);
            $rootScope.returnTo = "token.containerdetails({containerSerial:$scope.containerSerial})";
        };
    }]);