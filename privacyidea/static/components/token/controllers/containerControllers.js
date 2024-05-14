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

myApp.controller("containerListController", ['$scope', '$http', '$q', 'ContainerFactory', 'AuthFactory', 'ConfigFactory',
    function containerListController($scope, $http, $q, ContainerFactory, AuthFactory, ConfigFactory) {
        $scope.containers = []
        ContainerFactory.getContainers(function (data) {
            $scope.containers = data.result.value
        })
    }]);

myApp.controller("containerDetailsController", ['$scope', '$http', '$stateParams', '$q', 'ContainerFactory', 'AuthFactory', 'ConfigFactory',
    function containerDetailsController($scope, $http, $stateParams, $q, ContainerFactory, AuthFactory, ConfigFactory) {
        $scope.containerSerial = $stateParams.containerSerial
    }]);