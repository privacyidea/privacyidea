myApp.controller("containerCreateController", ['$scope', '$http', '$q', 'ContainerFactory', '$stateParams',
    'AuthFactory', 'ConfigFactory', 'UserFactory', '$state',
    function createContainerController($scope, $http, $q, ContainerFactory, $stateParams,
                                       AuthFactory, ConfigFactory, UserFactory, $state) {
        $scope.formData = {
            containerTypes: {},
        };
        $scope.form = {
            containerType: "generic",
            description: "",
            token_types: ""
        };

        $scope.$watch('form', function (newVal, oldVal) {
            if (newVal && allContainerTypes[newVal.containerType]) {
                $scope.form.token_types = allContainerTypes[newVal.containerType]["token_types_display"];
            }
        }, true);

        ContainerFactory.getContainerTypes(function (data) {
            $scope.formData.containerTypes = data.result.value;
        });

        // Get the supported token types for each container type once
        let allContainerTypes = {};
        ContainerFactory.getTokenTypes(function (data) {
            allContainerTypes = data.result.value;

            angular.forEach(allContainerTypes, function (_, containerType) {
                if (containerType === 'generic') {
                    allContainerTypes[containerType]["token_types_display"] = 'All';
                } else {
                    allContainerTypes[containerType]["token_types_display"] = $scope.tokenTypesToDisplayString(
                        allContainerTypes[containerType].token_types);
                }
            });
            $scope.form.token_types = allContainerTypes[$scope.form.containerType]["token_types_display"];
        });

        // converts the supported token types to a display string
        $scope.tokenTypesToDisplayString = function (containerTokenTypes) {
            let displayString = "";
            // create comma separated list out of token names
            angular.forEach(containerTokenTypes, function (type) {
                displayString += type.charAt(0).toUpperCase() + type.slice(1) + ", ";
            });
            displayString = displayString.slice(0, -2);

            return displayString;
        };

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
                // init the user, if token.containercreate was called from the user.details
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
                            $scope.get_user_infos(data);
                        });
                }
            });
        } else if (AuthFactory.getRole() === 'user') {
            // init the user, if token.containercreate was called as a normal user
            $scope.newUser = {user: AuthFactory.getUser().username, realm: AuthFactory.getUser().realm};
            if ($scope.checkRight('userlist')) {
                UserFactory.getUserDetails({}, function (data) {
                    $scope.User = data.result.value[0];
                    $scope.form.email = $scope.User.email;
                    if (typeof $scope.User.mobile === "string") {
                        $scope.form.phone = $scope.User.mobile;
                    } else {
                        $scope.phone_list = $scope.User.mobile;
                        if ($scope.phone_list && $scope.phone_list.length === 1) {
                            $scope.form.phone = $scope.phone_list[0];
                        }
                    }
                });
            }
        }

        $scope.createContainer = function () {
            let ctype = $scope.form.containerType;
            let params = {"type": ctype};
            if ($scope.newUser.user) {
                params["user"] = fixUser($scope.newUser.user);
                params["realm"] = $scope.newUser.realm;
            }
            if ($scope.form.description) {
                params["description"] = $scope.form.description;
            }

            ContainerFactory.createContainer(params, function (data) {
                $state.go("token.containerdetails", {"containerSerial": data.result.value.container_serial});
            });
        };
    }]);

myApp.controller("containerListController", ['$scope', '$http', '$q', 'ContainerFactory', 'AuthFactory',
    'ConfigFactory', 'TokenFactory',
    function containerListController($scope, $http, $q, ContainerFactory, AuthFactory, ConfigFactory, TokenFactory) {
        $scope.containersPerPage = $scope.token_page_size;
        $scope.loggedInUser = AuthFactory.getUser();
        $scope.params = {sortdir: "asc"};
        $scope.containerdata = [];

        // Change the pagination
        $scope.pageChanged = function () {
            //debug: console.log('Page changed to: ' + $scope.params.page);
            $scope.get();
        };

        // Get all containers
        $scope.get = function () {
            $scope.expandedRows = [];
            $scope.params.sortby = $scope.sortby;
            if ($scope.reverse) {
                $scope.params.sortdir = "desc";
            } else {
                $scope.params.sortdir = "asc";
            }
            $scope.params.pagesize = $scope.token_page_size;

            ContainerFactory.getContainers($scope.params,
                function (data) {
                    $scope.containerdata = data.result.value;
                });
        };
        $scope.get();

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

        $scope.adminOrUserIsOwner = function (username, realm) {
            let allow = false;
            if ($scope.loggedInUser.role === 'admin') {
                allow = true;
            } else {
                if (username == $scope.loggedInUser.username
                    && realm == $scope.loggedInUser.realm) {
                    allow = true;
                }
            }
            return allow;
        }

        // Expand token view
        $scope.expandedRows = [];
        $scope.expandTokenView = function (containerRow) {
            if (containerRow < 0) {
                for (let i = 0; i < $scope.containerdata.containers.length; i++) {
                    if ($scope.containerdata.containers[i].tokens.length > 0) {
                        $scope.expandedRows.push(i);
                    }
                }
            } else {
                $scope.expandedRows.push(containerRow);
            }
        };

        // Collapse token view
        $scope.collapseTokenView = function (containerRow) {
            if (containerRow < 0) {
                while ($scope.expandedRows.length > 0) {
                    $scope.expandedRows.pop();
                }
            } else {
                $scope.expandedRows.splice($scope.expandedRows.indexOf(containerRow), 1);
            }
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.get);
    }]);

myApp.controller("containerDetailsController", ['$scope', '$http', '$stateParams', '$q', 'ContainerFactory', 'AuthFactory', 'ConfigFactory', 'TokenFactory', '$state', '$rootScope',
    function containerDetailsController($scope, $http, $stateParams, $q, ContainerFactory, AuthFactory, ConfigFactory, TokenFactory, $state, $rootScope) {
        $scope.init = true;
        $scope.containerSerial = $stateParams.containerSerial;
        $scope.loggedInUser = AuthFactory.getUser();

        $scope.container = {
            users: [],
            last_seen: "",
            last_updated: "",
        };
        $scope.containerOwner = {};
        // Get possible container states
        $scope.stateTypes = [];
        $scope.containerStates = {};
        $scope.displayState = {};
        ContainerFactory.getStateTypes(function (data) {
            $scope.stateTypes = data.result.value;
            angular.forEach($scope.stateTypes, function (val, state) {
                // Set the state to false, if it is displayed next to states that exclude each other
                if (!(state in $scope.displayState)) {
                    $scope.displayState[state] = true;
                    angular.forEach($scope.stateTypes[state], function (excludedState) {
                        $scope.displayState[excludedState] = false;
                    });
                }
                // Set default value for the container states if it is not set yet
                if (!$scope.containerStates[state]) {
                    $scope.containerStates[state] = false;
                }
            });
        });

        // Get the supported token types of the container
        $scope.supportedTokenTypes = [];
        $scope.getSupportedTokenTypes = function () {
            ContainerFactory.getTokenTypes(function (data) {
                let allContainerTypes = data.result.value;
                $scope.supportedTokenTypes = allContainerTypes[$scope.container.type]["token_types"];
            });
        };

        // Get the container
        $scope.container = {};
        $scope.containerOwner = {};
        $scope.showDialog = {};
        $scope.userRealms = [];
        $scope.getContainer = function () {
            ContainerFactory.getContainerForSerial($scope.containerSerial, function (data) {
                if (data.result.value.containers.length > 0) {
                    $scope.container = data.result.value.containers[0];
                    $scope.containerOwner = $scope.container.users[0];
                    $scope.container.last_seen = new Date($scope.container.last_seen);
                    $scope.container.last_updated = new Date($scope.container.last_updated);

                    angular.forEach($scope.container.states, function (state) {
                        $scope.excludeStates(state);
                    });

                    $scope.stateSelectionChanged = false;
                    angular.forEach($scope.container.tokens, function (token) {
                        $scope.showDialog[token.serial] = false;
                    });
                    if ($scope.supportedTokenTypes.length == 0) {
                        // Get supported token types only once
                        $scope.getSupportedTokenTypes();
                    }

                    angular.forEach($scope.container.users, function (user) {
                        $scope.userRealms.push(user.user_realm);
                    });
                } else {
                    // If there is nothing returned, the user should not be on this page
                    // (the details page of a non-visible container)
                    $scope.containerOwner = null;
                    $state.go("token.containerlist");
                }
            });
            $scope.get();
        };

        $scope.excludeStates = function (state) {
            // Deselect excluded states based on the selected state
            $scope.containerStates[state] = true;
            angular.forEach($scope.stateTypes[state], function (disableType) {
                $scope.containerStates[disableType] = false;
            });
        };

        $scope.$watch("containerStates", function (newValue, oldValue) {
            $scope.stateSelectionChanged = true;
            for (let [key, value] of Object.entries(newValue)) {
                if (value && !oldValue[key]) {
                    $scope.excludeStates(key);
                }
            }
        }, true); // true = deep watch

        $scope.saveStates = function () {
            let states = "";
            angular.forEach($scope.containerStates, function (value, key) {
                if (value) {
                    if (states !== "") {
                        states += ",";
                    }
                    states += key;
                }
            });
            let params = {"container_serial": $scope.containerSerial, "states": states};
            ContainerFactory.setStates(params, $scope.getContainer);
            $scope.stateSelectionChanged = false;
        };

        $scope.returnTo = function () {
            // After deleting the container, we return here.
            $state.go($rootScope.previousState.state,
                $rootScope.previousState.params);
        };

        $scope.deleteContainerButton = false;
        $scope.deleteContainerMode = function (deleteTokens) {
            if (deleteTokens) {
                $scope.deleteAllTokens();
            }
            ContainerFactory.deleteContainer($scope.containerSerial, $scope.returnTo);
        };

        $scope.setDescription = function (description) {
            ContainerFactory.setDescription($scope.containerSerial, description, $scope.getContainer);
        };

        $scope.editContainerRealms = false;
        $scope.startEditRealms = function () {
            // fill the selectedRealms with the realms of the container
            $scope.selectedRealms = {};
            $scope.editContainerRealms = true;
            angular.forEach($scope.container.realms, function (realmName, _index) {
                $scope.selectedRealms[realmName] = true;
            });
        };

        $scope.saveRealms = function () {
            let realmList = "";
            for (const realm in $scope.selectedRealms) {
                if ($scope.selectedRealms[realm] === true) {
                    realmList += realm + ",";
                }
            }
            realmList = realmList.slice(0, -1);
            const realmParams = {"container_serial": $scope.containerSerial, "realms": realmList};
            ContainerFactory.setRealms(realmParams, $scope.getContainer);
            $scope.cancelEditRealms();
        };

        $scope.cancelEditRealms = function () {
            $scope.editContainerRealms = false;
            $scope.selectedRealms = {};
        };

        $scope.newUser = {user: "", realm: $scope.defaultRealm};
        $scope.assignUser = function () {
            ContainerFactory.assignUser(
                {
                    container_serial: $scope.containerSerial,
                    user: fixUser($scope.newUser.user),
                    realm: $scope.newUser.realm,
                }
                , $scope.getContainer);
        };

        $scope.unassignUser = function () {
            ContainerFactory.unassignUser(
                {
                    container_serial: $scope.containerSerial,
                    user: fixUser($scope.containerOwner.user_name),
                    realm: $scope.containerOwner.realm,
                    pin: $scope.containerOwner.pin
                }
                , $scope.getContainer);
        };

        $scope.editContainerInfo = false;
        $scope.startEditContainerInfo = function () {
            $scope.editContainerInfo = true;
        };

        $scope.saveContainerInfo = function () {
            $scope.editContainerInfo = false;
        };

        if ($scope.loggedInUser.isAdmin) {
            // These are functions that can only be used by administrators.
            // If the user is admin, we can fetch all realms
            // If the loggedInUser is only a user, we do not need the realm list,
            // as we do not assign a user
            ConfigFactory.getRealms(function (data) {
                $scope.realms = data.result.value;
            });
        }

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getContainer);

        // ------------------- Token Actions -------------------------------
        $scope.tokensPerPage = $scope.token_page_size;
        $scope.tokenParams = {page: 1, sortdir: "asc"};
        $scope.reverse = false;

        // --- Actions for tokens in the container ---
        $scope.getAllTokenSerials = function () {
            let tokenSerials = [];
            angular.forEach($scope.container.tokens, function (token) {
                tokenSerials.push(token.serial);
            });
            return tokenSerials;
        };

        $scope.enrollToken = function () {
            // go to token.enroll with the users data of the container owner
            $scope.enrollParams = {};
            if ($scope.containerOwner) {
                $scope.enrollParams = {
                    realmname: $scope.containerOwner.user_realm,
                    username: $scope.containerOwner.user_name,
                };
            }
            $scope.enrollParams.containerSerial = $scope.containerSerial;
            $state.go("token.enroll", $scope.enrollParams);
            $rootScope.returnTo = "token.containerdetails({containerSerial:$scope.containerSerial})";
        };

        $scope.disableAllTokens = function () {
            let tokenSerialList = $scope.getAllTokenSerials();
            let tokenSerialStr = tokenSerialList.join(',');
            if (tokenSerialList.length > 0) {
                TokenFactory.disableMultiple({'serial': tokenSerialStr}, $scope.getContainer);
            }
        };

        $scope.enableAllTokens = function () {
            let tokenSerialList = $scope.getAllTokenSerials();
            let tokenSerialStr = tokenSerialList.join(',');
            if (tokenSerialList.length > 0) {
                TokenFactory.enableMultiple({'serial': tokenSerialStr}, $scope.getContainer);
            }
        };

        $scope.removeAllTokens = function () {
            let tokenSerialList = $scope.getAllTokenSerials();
            let tokenSerialStr = tokenSerialList.join(',');
            if (tokenSerialList.length > 0) {
                ContainerFactory.removeAllTokensFromContainer({
                    'container_serial': $scope.containerSerial,
                    'serial': tokenSerialStr
                }, $scope.getContainer);
            }
        };

        $scope.showDialogAll = false;
        $scope.deleteAllTokens = function () {
            let tokenSerialList = $scope.getAllTokenSerials();
            angular.forEach(tokenSerialList, function (token, index) {
                if (index == tokenSerialList.length - 1) {
                    // last token: update container with callback
                    TokenFactory.delete(token, $scope.getContainer);
                } else {
                    TokenFactory.delete(token);
                }
            });
            $scope.showDialogAll = false;
        };

        // --- Add token functions ---
        $scope.addTokens = false;
        $scope.showTokensWithoutContainer = true;
        $scope.search_container_serial = "";

        $scope.activateAddTokens = function () {
            $scope.addTokens = true;
            $scope.get();
        };

        $scope.$watch('showTokensWithoutContainer', function (newVal, oldVal) {
            if (newVal) {
                $scope.search_container_serial = "";
            } else {
                $scope.search_container_serial = null;
            }
            $scope.get();
        });

        // Note: This function has to be named "get", since it is called by the pifilter directive
        $scope.get = function (live_search) {
            if ((!$rootScope.search_on_enter) || ($rootScope.search_on_enter && !live_search)) {
                $scope.tokenParams.serial = "*" + ($scope.serialFilter || "") + "*";
                $scope.tokenParams.tokenrealm = "*" + ($scope.tokenrealmFilter || "") + "*";
                $scope.tokenParams.type = "*" + ($scope.typeFilter || "") + "*";
                $scope.tokenParams.type_list = $scope.supportedTokenTypes;
                $scope.tokenParams.description = "*" + ($scope.descriptionFilter || "") + "*";
                $scope.tokenParams.rollout_state = "*" + ($scope.rolloutStateFilter || "") + "*";
                $scope.tokenParams.userid = "*" + ($scope.userIdFilter || "") + "*";
                $scope.tokenParams.resolver = "*" + ($scope.resolverFilter || "") + "*";
                $scope.tokenParams.pagesize = $scope.token_page_size;
                $scope.tokenParams.sortby = $scope.sortby;
                $scope.tokenParams.container_serial = $scope.search_container_serial;
                if ($scope.reverse) {
                    $scope.tokenParams.sortdir = "desc";
                } else {
                    $scope.tokenParams.sortdir = "asc";
                }
                TokenFactory.getTokens(function (data) {
                    if (data) {
                        $scope.tokendata = data.result.value;
                    }
                }, $scope.tokenParams);
            }
        };

        // Change the pagination for the add token list
        $scope.pageChanged = function () {
            $scope.get(false);
        };

        // --- single token functions for token list ---
        $scope.resetFailcount = function (serial) {
            TokenFactory.reset(serial, $scope.getContainer);
        };
        $scope.disableToken = function (serial) {
            TokenFactory.disable(serial, $scope.getContainer);
        };
        $scope.enableToken = function (serial) {
            TokenFactory.enable(serial, $scope.getContainer);
        };
        $scope.removeOneToken = function (token_serial) {
            let params = {
                "container_serial": $scope.containerSerial,
                "serial": token_serial
            };
            ContainerFactory.removeTokenFromContainer(params, $scope.getContainer);
        }
        $scope.deleteOneToken = function (token_serial, dialog) {
            if (dialog) {
                $scope.showDialog[token_serial] = true;
            } else {
                TokenFactory.delete(token_serial, $scope.getContainer);
            }
        }
        $scope.addToken = function (token_serial) {
            ContainerFactory.addTokenToContainer({
                "container_serial": $scope.containerSerial,
                "serial": token_serial
            }, function () {
                $scope.getContainer();
                $scope.get();
            });
        };
        $scope.adminOrUserIsOwner = function (username, realm) {
            let allow = false;
            if ($scope.loggedInUser.role === 'admin') {
                allow = true;
            } else {
                if (username == $scope.loggedInUser.username
                    && realm == $scope.loggedInUser.realm) {
                    allow = true;
                }
            }
            return allow;
        }

        // ----------- Initial calls -------------
        $scope.getContainer();
        ContainerFactory.updateLastSeen($scope.containerSerial);
    }]);