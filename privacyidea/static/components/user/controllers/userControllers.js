/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2016-04-10 Martin Wheldon <martin.wheldon@greenhills-it.co.uk>
 *            On initialisation generate object describing the fields
 *            required by the add user form for each resolver.
 *            Add function to update form on switching of resolver
 *            on the add user form.
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
    .controller("userAddController", ['$scope', 'userUrl', '$state', '$location', 'ConfigFactory', 'UserFactory',
        'inform', 'gettextCatalog',
        function ($scope, userUrl, $state, $location, ConfigFactory, UserFactory, inform, gettextCatalog) {

            $scope.formInit = {};
            $scope.User = {};
            $scope.editUser = true;

            /// Translation in dynamic user creation
            const myString = gettextCatalog.getString("password");

            ConfigFactory.getEditableResolvers(function (data) {
                let resolvers = data.result.value;
                let resolvernames = [];
                for (let rname in resolvers) {
                    resolvernames.push(rname);
                }
                $scope.formInit.resolvernames = resolvernames;
                if (resolvernames.length > 0) {
                    $scope.resolvername = resolvernames[0];
                    $scope.userAttributes = $scope.getUserAttributes(resolvers);
                    //debug: console.log("Getting View Attributes for " + $scope.resolvername);
                    $scope.getUserAttributesView($scope.resolvername, $scope.userAttributes);
                }
            });

            $scope.createUser = function () {
                //debug: console.log($scope.User);
                UserFactory.createUser($scope.resolvername, $scope.User,
                    function (data) {
                        //debug: console.log(data.result);
                        inform.add(gettextCatalog.getString("User created."),
                            {type: "info"});

                        // reload the users
                        $scope._getUsers();
                        $location.path("/user/list");
                    });
            };

            // listen to the reload broadcast
            $scope.$on("piReload", $scope.getEditableResolvers);
        }]);

angular.module("privacyideaApp")
    .controller("userPasswordController", ['$scope', 'userUrl', 'UserFactory', 'inform', 'gettextCatalog',
        function ($scope, userUrl, UserFactory, inform, gettextCatalog) {

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
                ////debug: console.log($scope.User);
                UserFactory.updateUser($scope.User.resolver,
                    {
                        username: $scope.User.username,
                        password: $scope.User.password
                    }, function (data) {
                        inform.add(gettextCatalog.getString("Password set successfully."),
                            {type: "info"});
                        $scope.User.password = "";
                        $scope.password2 = "";
                    });
            };

            // listen to the reload broadcast
            $scope.$on("piReload", $scope.getUserDetails);
        }]);

angular.module("privacyideaApp")
    .controller("userDetailsController", ['$scope', 'userUrl', 'realmUrl', 'tokenUrl', '$rootScope', 'TokenFactory',
        'UserFactory', 'ContainerFactory', 'AuthFactory', '$state', 'ConfigFactory', 'instanceUrl', '$location',
        'inform', 'gettextCatalog', '$stateParams',
        function ($scope, userUrl, realmUrl, tokenUrl, $rootScope, TokenFactory, UserFactory, ContainerFactory,
                  AuthFactory, $state, ConfigFactory, instanceUrl, $location, inform, gettextCatalog, $stateParams) {
            $scope.username = $stateParams.username;
            $scope.realmname = $stateParams.realmname;
            $scope.resolvername = $stateParams.resolvername;
            $scope.editable = $stateParams.editable;
            $scope.tokensPerPage = 5;

            $scope.containersPerPage = 5;
            $scope.newToken = {"serial": "", pin: ""};
            $scope.params = {page: 1};
            $scope.containerParams = {page: 1};
            $scope.instanceUrl = instanceUrl;
            $scope.editUser = false;
            document.body.scrollTop = document.documentElement.scrollTop = 0;
            $scope.enableAddTokenToContainer = false;
            $scope._getUserToken = function () {
                TokenFactory.getTokenForUser({
                    user: $scope.username,
                    realm: $scope.realmname,
                    pagesize: $scope.tokensPerPage,
                    page: $scope.params.page
                }, function (data) {
                    $scope.tokendata = data.result.value;
                    //debug: console.log("Token for user " + $scope.username);
                    $scope.enableAddTokenToContainer = $scope.tokendata.tokens.length > 0;
                });
            };

            $scope.getUserContainer = function () {
                if (AuthFactory.checkRight("container_list")) {
                    ContainerFactory.getContainerForUser({
                        user: $scope.username,
                        realm: $scope.realmname,
                        pagesize: $scope.containersPerPage,
                        page: $scope.containerParams.page
                    }, function (data) {
                        $scope.containerdata = data.result.value.containers;
                    });
                } else {
                    $scope.containerdata = [];
                }
            };

            // Change the pagination
            $scope.pageChanged = function () {
                //debug: console.log('Page changed to: ' + $scope.params.page);
                $scope._getUserToken();
                $scope.getUserContainer();
            };

            $scope.getResolverDetails = function (resolverName) {
                ConfigFactory.getResolver(resolverName, function (data) {
                    const resolvers = data.result.value;
                    $scope.userAttributes = $scope.getUserAttributes(resolvers);
                    $scope.getUserAttributesView(resolverName, $scope.userAttributes);
                });
            };

            $scope.getUserDetails = function () {
                UserFactory.getUserDetails({
                    username: $scope.username,
                    realm: $scope.realmname
                }, function (data) {
                    $scope.User = data.result.value[0];
                    $scope.User.password = "";
                    $scope.getResolverDetails($scope.User.resolver);
                });
            };

            $scope.getEditableAttributes = function () {
                UserFactory.getEditableAttributes({
                    user: $scope.username,
                    resolver: $scope.resolver,
                    realm: $scope.realmname
                }, function (data) {
                    $scope.allowedCustomAttributes = data.result.value;
                });
            };

            $scope.addCustomAttribute = function () {
                let key = $scope.selectedAttrKey;
                let value = $scope.selectedAttrValue;
                if ($scope.selectedAttrKey === '*') {
                    key = $scope.newCustomAttributeKey;
                }
                if ($scope.selectedAttrValue === '*') {
                    value = $scope.newCustomAttributeValue;
                }
                UserFactory.setCustomAttribute($scope.username, $scope.realmname, key, value,
                    function (data) {
                        $scope.getUserDetails();
                        $scope.getCustomAttributes();
                    });
            };

            $scope.getCustomAttributes = function () {
                UserFactory.getCustomAttributes($scope.username, $scope.realmname,
                    function (data) {
                        $scope.custom_attributes = data.result.value;
                    });
            };

            $scope.deleteCustomAttribute = function (key) {
                UserFactory.deleteCustomAttribute($scope.username, $scope.realmname, key,
                    function (data) {
                        $scope.getUserDetails();
                        $scope.getCustomAttributes();
                    });
            }

            $scope.onCustomAttributeKeyChange = function () {
                $scope.newCustomAttributeValue = "";
                $scope.selectedAttrValue = "";
                $scope.allowed_values = $scope.allowedCustomAttributes['set'][$scope.selected_attr_key]
                $scope.customAttributeValueSelectVisible = true;
                if ($scope.allowed_values.length === 1) {
                    // If there is only one value, set it!
                    $scope.selected_attr_value = $scope.allowed_values[0];
                    // if this value is "*", then we hide the
                    $scope.customAttributeValueSelectVisible = false;
                }
            }

            $scope.updateUser = function () {
                UserFactory.updateUser($scope.resolvername, $scope.User,
                    function (data) {
                        if (data.result.value) {
                            inform.add(gettextCatalog.getString("User updated " +
                                    "successfully."),
                                {type: "info"});
                            // in case we changed the username:
                            $scope.username = $scope.User.username;
                            $state.go("user.details", {
                                realmname: $scope.realmname,
                                username: $scope.username
                            });
                            // we also need to update the user list
                            $scope._getUsers();
                            // ...and update the user details
                            $scope.getUserDetails();
                            $scope.getUserContainer()
                        } else {
                            inform.add(gettextCatalog.getString("Failed to update user."), {type: "danger"});
                        }
                    });
            };

            $scope.deleteUserAsk = function () {
                $('#dialogUserDelete').modal();
            };

            $scope.deleteUser = function () {
                UserFactory.deleteUser($scope.resolvername, $scope.User.username,
                    function (data) {
                        if (data.result.value) {
                            inform.add(gettextCatalog.getString("User deleted " +
                                    "successfully."),
                                {type: "info"});
                            $scope._getUsers();
                            $location.path("/user/list");
                        } else {
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
                    $('html,body').scrollTop(0);
                    $scope.newToken = {"serial": "", pin: ""};
                });
            };

            $scope.enrollToken = function () {
                // go to token.enroll with the users data
                $state.go("token.enroll", {
                    realmname: $scope.realmname,
                    username: $scope.username
                });
                $rootScope.returnTo = "user.details({realmname:$scope.realmname, username:$scope.username})";
            };

            // single token function
            $scope.reset = function (serial) {
                TokenFactory.reset(serial, $scope._getUserToken);
            };
            $scope.disable = function (serial) {
                TokenFactory.disable(serial, $scope._getUserToken);
            };
            $scope.enable = function (serial) {
                TokenFactory.enable(serial, $scope._getUserToken);
            };
            $scope.showDialog = {};
            $scope.deleteToken = function (token_serial, dialog) {
                if (dialog) {
                    $scope.showDialog[token_serial] = true;
                } else {
                    TokenFactory.delete(token_serial, $scope._getUserToken);
                }
            };
            $scope.unassign = function (serial) {
                TokenFactory.unassign(serial, $scope._getUserToken);
            };

            $scope.getUserDetails();
            $scope._getUserToken();
            $scope.getEditableAttributes();
            $scope.getCustomAttributes();
            $scope.getUserContainer();

            // listen to the reload broadcast
            $scope.$on("piReload", function () {
                $scope.getUserDetails();
                $scope._getUserToken();
                $scope.getCustomAttributes();
                $scope.getUserContainer();
            });

            // Container
            $scope.containerSerial = "";
            $scope.showTokenOfUser = true;
            $scope.containerSelected = false;
            // Enable the button only if a container is selected
            $scope.$watch('containerSerial', function (newValue, oldValue) {
                $scope.containerSelected = (newValue != null && newValue != undefined && newValue != "createnew");
            });

            // Selection looks like this {"TOTP0001B29F":{"totp":true}, "OATH0002EB1F":{"hotp":false}}
            $scope.tokenSelection = {};
            $scope.selectedTokenTypes = [];
            $scope.$watch("tokenSelection", function (newValue, oldValue) {
                // Convert the selection data to an array of tokentypes to pass to the select-or-create-token directive
                let selectedTypes = [];
                for (let [key, value] of Object.entries(newValue)) {
                    const type = Object.keys(value)[0];
                    if (value[type] && !selectedTypes.includes(type)) {
                        selectedTypes.push(type);
                    }
                }
                $scope.selectedTokenTypes = selectedTypes;
            }, true); // true = deep watch

            // Button actions
            $scope.addTokensToContainerMode = function () {
                $scope.showTokenOfUser = false;
                $scope.tokenWithoutContainer = [];
                for (let token of $scope.tokendata.tokens) {
                    if (!token.container_serial) {
                        $scope.tokenWithoutContainer.push(token);
                    }
                }
            };

            $scope.cancelAddTokensToContainerMode = function () {
                $scope.showTokenOfUser = true;
                $scope.tokenSelection = {};
                $scope.containerSerial = null;
            }

            $scope.addTokensToContainerAction = function () {
                let selectedSerials = "";
                for (let [key, value] of Object.entries($scope.tokenSelection)) {
                    if (selectedSerials !== "") {
                        selectedSerials += ","
                    }
                    selectedSerials += key;
                }
                let params = {serial: selectedSerials, container_serial: $scope.containerSerial};
                ContainerFactory.addTokenToContainer(params, function (data) {

                });
                // Reload the token to show the container
                $scope._getUserToken();
                $scope.showTokenOfUser = true;
                $scope.containerSerial = null;
            };
        }
    ]);

angular.module("privacyideaApp")
    .controller("userController", ['$scope', '$location', 'userUrl', 'realmUrl',
        '$rootScope', 'ConfigFactory', 'UserFactory', 'gettextCatalog', 'AuthFactory',
        function ($scope, $location, userUrl, realmUrl, $rootScope, ConfigFactory, UserFactory, gettextCatalog,
                  AuthFactory) {

            $scope.usersPerPage = $scope.user_page_size;
            $scope.params = {
                page: 1,
                usernameFilter: "",
                surnameFilter: "",
                givennameFilter: "",
                emailFilter: ""
            };
            $scope.loggedInUser = AuthFactory.getUser();
            // scroll to the top of the page
            document.body.scrollTop = document.documentElement.scrollTop = 0;
            // go to the list view by default
            if ($location.path() === "/user") {
                $location.path("/user/list");
            }

            $scope._getUsers = function (live_search) {
                if ((!$rootScope.search_on_enter) || ($rootScope.search_on_enter && !live_search)) {
                    // We shall only search, if either we do not search on enter or
                    // if we search_on_enter and the enter key is pressed.
                    const params = {realm: $scope.selectedRealm};
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
                            //debug: console.log("success");
                            const userList = data.result.value;
                            // The userList is the complete list of the users.
                            $scope.userCount = userList.length;
                            const start = ($scope.params.page - 1) * $scope.usersPerPage;
                            const stop = start + $scope.usersPerPage;
                            $scope.userlist = userList.slice(start, stop);
                            //debug: console.log($scope.userlist);
                        });
                }
            };

            // Change the pagination
            $scope.pageChanged = function () {
                //debug: console.log('Page changed to: ' + $scope.params.page);
                $scope._getUsers();
            };

            $scope.getRealms = function () {
                ConfigFactory.getRealms(function (data) {
                    $scope.realms = data.result.value;
                    let realmCount = Object.keys($scope.realms).length;
                    angular.forEach($scope.realms, function (realm, realmname) {
                        if (realmCount === 1) {
                            // If the admin is allowed to see only one realm, we make this the
                            // default realm in the UI
                            realm.default = true;
                        }
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

            /*
            This function returns a list with all possible user attributes
            in these resolvers. Possible attributes are a dictionary with
            the keys data, label, name, required, type.
            */
            $scope.getUserAttributes = function (resolvers) {
                let userinfo;
                const allResolverAttributes = [];

                for (const rname in resolvers) {
                    const resolver = resolvers[rname];
                    switch (resolver.type) {
                        case "ldapresolver":
                            userinfo = JSON.parse(resolver.data.USERINFO);
                            break;
                        case "sqlresolver":
                            userinfo = JSON.parse(resolver.data.Map);
                            delete userinfo["userid"];
                            break;
                    }
                    const fields = [];
                    const r = {};
                    angular.forEach(userinfo, function (value, key) {
                        let field = {
                            "type": "text",
                            "name": key,
                            "label": gettextCatalog.getString(key),
                            "data": "",
                            "required": true
                        };
                        switch (key) {
                            case "username":
                                this.push(field);
                                break;
                            case "email":
                                field["type"] = "email";
                                this.push(field);
                                break;
                            case "password":
                                field["type"] = "password";
                                this.push(field);
                                break;
                            default:
                                field["required"] = false;
                                this.push(field);
                                break;
                        }
                    }, fields);
                    r[rname] = fields;
                    allResolverAttributes.push(r);
                }
                return allResolverAttributes;
            };

            $scope.getUserAttributesView = function (resolvername, userAttributes) {
                /*
                This function returns the display information of the user attributes
                */

                let userFields = [];
                angular.forEach(userAttributes, function (value, key) {
                    if (value.hasOwnProperty(resolvername)) {
                        userFields = value[resolvername];
                    }
                });

                const start = 0;
                const middle = Math.ceil(userFields.length / 2);
                const end = userFields.length + 1;
                $scope.leftColumn = userFields.slice(start, middle);
                $scope.rightColumn = userFields.slice(middle, end);
            };

            $scope.$on("piReload", function () {
                $scope._getUsers(false);
            });
        }]);
