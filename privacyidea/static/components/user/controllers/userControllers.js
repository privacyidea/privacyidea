/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2015-01-11 Cornelius Kölbel, <cornelius@privacyidea.org>
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */
angular.module("privacyideaApp")
    .controller("userAddController", function ($scope, userUrl, $state,
                                               $location, ConfigFactory,
                                               UserFactory, inform,
                                               gettextCatalog){

        $scope.formInit = {};
        ConfigFactory.getEditableResolvers(function (data){
            var resolvers = data.result.value;
            var resolvernames = [];
            for (var rname in resolvers) {
                resolvernames.push(rname);
            }
            $scope.formInit.resolvernames = resolvernames;
            if (resolvernames.length > 0) {
                $scope.resolvername = resolvernames[0];
            }
        });

        $scope.createUser = function () {
            UserFactory.createUser($scope.resolvername, $scope.User,
                function (data) {
                    console.log(data.result);
                    inform.add(gettextCatalog.getString("User created."),
                                {type: "info"});

                    // reload the users
                    $scope._getUsers();
                    $location.path("/user/list");
            });
        };
    });

angular.module("privacyideaApp")
    .controller("userPasswordController", function ($scope, userUrl,
                                                    UserFactory, inform,
                                                    gettextCatalog) {

        // The user can fetch his own information.
        $scope.getUserDetails = function () {
            UserFactory.getUserDetails({}, function (data) {
                $scope.User = data.result.value[0];
                $scope.User.password = "";
            });
        };
        $scope.getUserDetails();

        // Set the password
        $scope.setPassword = function () {
            console.log($scope.User);
            UserFactory.updateUser($scope.User.resolver,
                {username: $scope.User.username,
                 password: $scope.User.password}, function (data) {
                    inform.add(gettextCatalog.getString("Password set successfully."),
                               {type: "info"});
                    $scope.User.password = "";
                    $scope.password2 = "";
                });
        };
    });

angular.module("privacyideaApp")
    .controller("userDetailsController", function ($scope, userUrl,
                                                   realmUrl, tokenUrl,
                                                   $rootScope, TokenFactory,
                                                   UserFactory, $state,
                                                   instanceUrl,  $location,
                                                   inform, gettextCatalog) {
        $scope.tokensPerPage = 5;
        $scope.newToken = {"serial": "", pin: ""};
        $scope.params = {page: 1};
        $scope.instanceUrl = instanceUrl;
        // scroll to the top of the page
        document.body.scrollTop = document.documentElement.scrollTop = 0;

        $scope._getUserToken = function () {
            TokenFactory.getTokenForUser({
                user: $scope.username,
                realm: $scope.realmname,
                pagesize: $scope.tokensPerPage,
                page: $scope.params.page
            }, function (data) {
                $scope.tokendata = data.result.value;
                console.log("Token for user " + $scope.username);
                console.log($scope.tokens);
            });
        };

        // Change the pagination
        $scope.pageChanged = function () {
            console.log('Page changed to: ' + $scope.params.page);
            $scope._getUserToken();
        };

        $scope.getUserDetails = function () {
            UserFactory.getUserDetails({
                username: $scope.username,
                realm: $scope.realmname
            }, function (data) {
                $scope.User = data.result.value[0];
                $scope.User.password = "";
            });
        };

        $scope.updateUser = function () {
            UserFactory.updateUser($scope.resolvername, $scope.User,
            function (data) {
                if (data.result.value==true) {
                    inform.add(gettextCatalog.getString("User updated " +
                        "successfully."),
                                {type: "info"});
                    // we also need to update the user list
                    $scope._getUsers();
                } else {
                    inform.add(gettextCatalog.getString("Failed to update user."), {type: "danger"});
                }
            });
        };

        $scope.deleteUserAsk = function() {
            $('#dialogUserDelete').modal();
        };
        $scope.deleteUser = function () {
            UserFactory.deleteUser($scope.resolvername, $scope.User.username,
            function (data) {
                if (data.result.value==true) {
                    inform.add(gettextCatalog.getString("User deleted " +
                        "successfully."),
                                {type: "info"});
                    $scope._getUsers();
                    $location.path("/user/list");
                }  else {
                    inform.add(gettextCatalog.getString("Failed to delete user."), {type: "danger"});
                }
            });
        };

        $scope.assignToken = function () {
            TokenFactory.assign({
                serial: fixSerial($scope.newToken.serial),
                realm: $scope.realmname,
                user: $scope.username,
                pin: $scope.newToken.pin
            }, function () {
                $scope._getUserToken();
                $scope.newToken = {"serial": "", pin: ""};
            });
        };

        $scope.getUserDetails();
        $scope._getUserToken();

        $scope.enrollToken = function() {
            // go to token.enroll with the users data
            $state.go("token.enroll", {realmname:$scope.realmname,
                                       username:$scope.username});
            $rootScope.returnTo="user.details({realmname:$scope.realmname, username:$scope.username})";
        };
    });

angular.module("privacyideaApp")
    .controller("userController", function ($scope, $location, userUrl,
                                            realmUrl, $rootScope,
                                            ConfigFactory, UserFactory,
                                            AuthFactory) {

        $scope.usersPerPage = $scope.user_page_size;
        $scope.params = {page: 1,
                        usernameFilter: "",
                        surnameFilter: "",
                        givennameFilter: "",
                        emailFilter: ""};
        $scope.loggedInUser = AuthFactory.getUser();
        // scroll to the top of the page
        document.body.scrollTop = document.documentElement.scrollTop = 0;
        // go to the list view by default
        if ($location.path() == "/user") {
            $location.path("/user/list");
        }

        $scope._getUsers = function () {
            var params = {realm: $scope.selectedRealm};
            if ($scope.params.usernameFilter) {
                params.username = "*" + $scope.params.usernameFilter + "*";
            }
            if ($scope.params.surnameFilter) {
                params.surname = "*" + $scope.params.surnameFilter + "*";
            }
            if ($scope.params.givennameFilter) {
                params.givenname = "*" + $scope.params.givennameFilter + "*";
            }
            if ($scope.params.emailFilter) {
                params.email = "*" + $scope.params.emailFilter + "*";
            }
            UserFactory.getUsers(params,
                function (data) {
                    console.log("success");
                    var userlist = data.result.value;
                    // The userlist is the complete list of the users.
                    $scope.usercount = userlist.length;
                    var start = ($scope.params.page - 1) * $scope.usersPerPage;
                    var stop = start + $scope.usersPerPage;
                    $scope.userlist = userlist.slice(start, stop);
                    console.log($scope.userlist);
                });
        };

        // Change the pagination
        $scope.pageChanged = function () {
            console.log('Page changed to: ' + $scope.params.page);
            $scope._getUsers();
        };

        $scope.getRealms = function () {
            ConfigFactory.getRealms(function (data) {
                $scope.realms = data.result.value;
                angular.forEach($scope.realms, function (realm, realmname) {
                    if (realm.default) {
                        $scope.defaultRealm = realmname;
                        if (!$scope.selectedRealm) {
                            $scope.selectedRealm = $scope.defaultRealm;
                            // Only load the users, if we know, what the
                            // default realm is
                            $scope._getUsers();
                        }
                    }
                });
            });
        };

        if ($scope.loggedInUser.role === "admin") {
            $scope.getRealms();
        }

        $scope.changeRealm = function () {
            $scope.params = {page: 1};
            $scope._getUsers();
        };

    });
