/**
 * (c) NetKnights GmbH 2024,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-FileCopyrightText: 2024 Nils Behlen <nils.behlen@netknights.it>
 * SPDX-FileCopyrightText: 2024 Jelina Unger <jelina.unger@netknights.it>
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

myApp.service('ContainerUtils', function () {

    this.createDisplayList = function (stringList) {
        // Creates a comma separated list as a single string out of a list of string objects.
        // Each string is capitalized.

        let displayList = "";
        angular.forEach(stringList, function (element) {
            displayList += element.charAt(0).toUpperCase() + element.slice(1) + ", ";
        });
        displayList = displayList.slice(0, -2);

        return displayList;
    }

    this.setAllowedTokenTypes = function (containerType, tokensForContainerTypes, allTokenTypes) {
        let allowedTokenTypes = {};
        allowedTokenTypes.displayPhrase = tokensForContainerTypes[containerType].token_types_display;
        allowedTokenTypes.list = tokensForContainerTypes[containerType].token_types;
        allowedTokenTypes.displaySelection = {};
        angular.forEach(allowedTokenTypes.list, function (tokenType) {
            let displayString = allTokenTypes[tokenType];
            if (displayString) {
                allowedTokenTypes.displaySelection [tokenType] = displayString;
            }
        });

        // Set default type
        const types = Object.keys(allowedTokenTypes.displaySelection);
        if (types.indexOf('hotp') >= 0) {
            // Set hotp as default
            allowedTokenTypes.default = 'hotp';
        } else {
            // Set the first token type as default
            allowedTokenTypes.default = types[0];
        }
        return allowedTokenTypes;
    };

});

myApp.controller("containerCreateController", ['$scope', '$http', '$q', 'ContainerFactory', '$stateParams',
    'AuthFactory', 'ConfigFactory', 'UserFactory', '$state', 'TokenFactory', 'ContainerUtils',
    function createContainerController($scope, $http, $q, ContainerFactory, $stateParams,
                                       AuthFactory, ConfigFactory, UserFactory, $state, TokenFactory, ContainerUtils) {
        $scope.formData = {
            containerTypes: {},
        };
        $scope.form = {
            containerType: "generic",
            description: "",
            template: ""
        };

        $scope.containerRegister = false;
        $scope.initRegistration = false;
        $scope.passphrase = {"ad": false, "prompt": "", "response": ""};

        $scope.allowedTokenTypes = {
            list: [],
            displayPhrase: "All",
            displaySelection: [],
        };

        $scope.tokenSettings = {
            tokenTypes: {},
            timesteps: [30, 60],
            otplens: [6, 8],
            hashlibs: ["sha1", "sha256", "sha512"],
            service_ids: {},
            selectedType: ""
        };

        $scope.selection = {tokens: []};
        $scope.functionObject = {};
        $scope.editTemplate = false;

        $scope.$watch('form.containerType', function (newVal, oldVal) {
            if (newVal && $scope.formData.containerTypes[newVal]) {
                $scope.allowedTokenTypes = ContainerUtils.setAllowedTokenTypes($scope.form.containerType,
                    $scope.formData.containerTypes, $scope.tokenSettings.tokenTypes);
                $scope.tokenSettings.selectedTokenType = $scope.allowedTokenTypes.default;

                $scope.getTemplates();
                $scope.editTemplate = false;
                $scope.selection = {tokens: []};
            }
        }, true);

        // Get the supported token types for each container type once
        $scope.getContainerTypes = function () {
            ContainerFactory.getTokenTypes(function (data) {
                $scope.formData.containerTypes = data.result.value;

                // Create display string for supported token types of each container type
                angular.forEach($scope.formData.containerTypes, function (_, containerType) {
                    if (containerType === 'generic') {
                        $scope.formData.containerTypes[containerType]["token_types_display"] = 'All';
                    } else {
                        $scope.formData.containerTypes[containerType]["token_types_display"] = ContainerUtils.createDisplayList(
                            $scope.formData.containerTypes[containerType].token_types);
                    }
                });

                // Sets the supported token types for the selected container type in different formats
                // (list, display list, display selection of each type, default type for the selection)
                $scope.allowedTokenTypes = ContainerUtils.setAllowedTokenTypes($scope.form.containerType,
                    $scope.formData.containerTypes, $scope.tokenSettings.tokenTypes);
                $scope.tokenSettings.selectedTokenType = $scope.allowedTokenTypes.default;
            });
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

        $scope.getTemplates = function () {
            let params = {"container_type": $scope.form.containerType};
            ContainerFactory.getTemplates(params, function (data) {
                let templatesList = data.result.value.templates;
                $scope.templates = {"No Template": {"name": "defaultSelection"}};
                $scope.form.template = $scope.templates["No Template"];
                angular.forEach(templatesList, function (template) {
                    $scope.templates[template.name] = template;
                    if (template.default) {
                        // select default template
                        $scope.form.template = template;
                        $scope.selectTemplate();
                    }
                });
            });
        };

        $scope.createContainer = function () {
            let ctype = $scope.form.containerType;
            let params = {"type": ctype};
            if ($scope.form.template && $scope.form.template.name !== "defaultSelection") {
                params["template"] = $scope.form.template;
            }
            if ($scope.newUser.user) {
                params["user"] = fixUser($scope.newUser.user);
                params["realm"] = $scope.newUser.realm;
            }
            if ($scope.form.description) {
                params["description"] = $scope.form.description;
            }

            ContainerFactory.createContainer(params, function (data) {
                $scope.containerSerial = data.result.value.container_serial;
                if ($scope.initRegistration && AuthFactory.checkRight('container_register')) {
                    let registrationParams =
                        {
                            "container_serial": $scope.containerSerial,
                            "passphrase_ad": $scope.passphrase.ad,
                            "passphrase_prompt": $scope.passphrase.prompt,
                            "passphrase_response": $scope.passphrase.response
                        };
                    ContainerFactory.initializeRegistration(registrationParams, function (registrationData) {
                        $scope.containerRegister = true;
                        $scope.containerRegistrationURL = registrationData.result.value['container_url']['value'];
                        $scope.containerRegistrationQR = registrationData.result.value['container_url']['img'];
                    });
                } else {
                    $state.go("token.containerdetails", {"containerSerial": $scope.containerSerial});
                }

            });
        };

        // Read the tokentypes and container types from the server
        $scope.getTokenAndContainerTypes = function () {
            TokenFactory.getEnrollTokens(function (data) {
                $scope.tokenSettings["tokenTypes"] = data.result.value;
                $scope.getContainerTypes();
            });
        };

        $scope.selectTemplate = function () {
            $scope.selection.tokens = $scope.templates[$scope.form.template.name].template_options.tokens;
        };

        $scope.getTemplates();
        $scope.getTokenAndContainerTypes();
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

myApp.controller("containerDetailsController", ['$scope', '$http', '$stateParams', '$q', 'ContainerFactory',
    'AuthFactory', 'ConfigFactory', 'TokenFactory', '$state', '$rootScope', '$timeout', '$location',
    function containerDetailsController($scope, $http, $stateParams, $q, ContainerFactory, AuthFactory, ConfigFactory,
                                        TokenFactory, $state, $rootScope, $timeout, $location) {
        $scope.init = true;
        $scope.containerSerial = $stateParams.containerSerial;
        $scope.loggedInUser = AuthFactory.getUser();

        $scope.container = {
            users: [],
            last_authentication: "",
            last_synchronization: "",
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
        $scope.getContainer = function () {
            ContainerFactory.getContainerForSerial($scope.containerSerial, function (data) {
                if (data.result.value.containers.length > 0) {
                    $scope.container = data.result.value.containers[0];
                    $scope.containerOwner = $scope.container.users[0];

                    // If the last authentication or synchronization date is not set, display a dash
                    if ($scope.container.last_authentication != null) {
                        $scope.container.last_authentication = new Date($scope.container.last_authentication);
                    } else {
                        $scope.container.last_authentication = "-";
                    }
                    if ($scope.container.last_synchronization != null) {
                        $scope.container.last_synchronization = new Date($scope.container.last_synchronization);
                    } else {
                        $scope.container.last_synchronization = "-";
                    }


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

                    $scope.userRealms = [];
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
            if ($scope.addTokens) {
                $scope.get();
            }
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

        $scope.deleteContainerButton = false;
        $scope.deleteContainerMode = function (deleteTokens) {
            if (deleteTokens) {
                // First all tokens have to be deleted, then the container
                $scope.deleteAllTokens($scope.deleteContainer);
            } else {
                $scope.deleteContainer();
            }
        };

        $scope.returnTo = function () {
            $state.go("token.containerlist");
        }

        $scope.deleteContainer = function () {
            ContainerFactory.deleteContainer($scope.containerSerial, $scope.returnTo);
        }

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

        $scope.registrationOptions = {"open": false};
        $scope.passphrase = {"required": false, "ad": false, "prompt": "", "response": ""};
        $scope.registerContainer = function () {
            let registrationParams =
                {
                    "container_serial": $scope.containerSerial,
                    "passphrase_ad": $scope.passphrase.ad,
                    "passphrase_prompt": $scope.passphrase.prompt,
                    "passphrase_response": $scope.passphrase.response
                };
            ContainerFactory.initializeRegistration(registrationParams, function (data) {
                if ($scope.container.type === "smartphone") {
                    $scope.showQR = true;
                    $scope.containerRegistrationURL = data.result.value['container_url']['value'];
                    $scope.containerRegistrationQR = data.result.value['container_url']['img'];
                }
                $scope.registrationOptions = {"open": false};
                $scope.getContainer();
                $scope.pollContainerDetails();
            });
        };

        $scope.unregisterContainer = function () {
            ContainerFactory.terminateRegistration($scope.containerSerial, function () {
                $scope.showQR = false;
                $scope.getContainer();
            });
        };

        $scope.pollContainerDetails = function () {
            let details_base_path = "/token/container/details";
            if ($scope.container.info['registration_state'] === "client_wait" && $location.path().indexOf(details_base_path) > -1) {
                // stop polling if the page changed or the container was (un)registered
                $scope.getContainer();
                $timeout($scope.pollContainerDetails, 2500);
            }
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
            // list all token serials the user is allowed to manage
            let tokenSerials = [];
            angular.forEach($scope.container.tokens, function (token) {
                if (token.tokentype) {
                    // If the user is allowed to manage a token, the token type is provided (otherwise only the serial)
                    tokenSerials.push(token.serial);
                }
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
            angular.forEach(tokenSerialList, function (serial) {
                $scope.disableToken(serial);
            });
        };

        $scope.enableAllTokens = function () {
            let tokenSerialList = $scope.getAllTokenSerials();
            angular.forEach(tokenSerialList, function (serial) {
                $scope.enableToken(serial);
            });
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
        $scope.deleteAllTokens = function (callback) {
            let tokenSerialList = $scope.getAllTokenSerials();
            angular.forEach(tokenSerialList, function (token, index) {
                if (index == tokenSerialList.length - 1) {
                    // last token: pass callback function
                    TokenFactory.delete(token, callback);
                } else {
                    TokenFactory.delete(token, function () {
                    });
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
                $scope.tokenParams.type_list = $scope.supportedTokenTypes.join(",");
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
            });
        };

        // ----------- Initial calls -------------
        $scope.getContainer();
    }]);

myApp.controller("containerTemplateListController", ['$scope', '$http', '$q', 'ContainerFactory', 'AuthFactory',
    'ConfigFactory', 'TokenFactory', '$location', '$state',
    function containerTemplateListController($scope, $http, $q, ContainerFactory, AuthFactory, ConfigFactory, TokenFactory, $location, $state) {
        $scope.templatesPerPage = $scope.token_page_size;
        $scope.loggedInUser = AuthFactory.getUser();
        $scope.params = {sortdir: "asc"};
        $scope.templatedata = [];

        if ($location.path() === "token.containertemplates") {
            $location.path("token.containertemplates.list");
        }

        // Change the pagination
        $scope.pageChanged = function () {
            //debug: console.log('Page changed to: ' + $scope.params.page);
            $scope.get();
        };

        $scope.editTemplate = function (templateName) {
            $state.go("token.containertemplates.edit", {"templateName": templateName});
        };

        // Get all containers
        $scope.get = function () {
            $scope.params.sortby = $scope.sortby;
            if ($scope.reverse) {
                $scope.params.sortdir = "desc";
            } else {
                $scope.params.sortdir = "asc";
            }
            $scope.params.pagesize = $scope.token_page_size;

            ContainerFactory.getTemplates($scope.params,
                function (data) {
                    $scope.templatedata = data.result.value;
                });
        };

        $scope.deleteTemplate = function (templateName) {
            ContainerFactory.deleteTemplate(templateName, $scope.get);
        };

        $scope.get();

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.get);
    }]);

myApp.controller("containerTemplateCreateController", ['$scope', '$http', '$q', 'ContainerFactory', 'AuthFactory',
    'ConfigFactory', 'TokenFactory', '$location', '$state', 'ContainerUtils',
    function containerTemplateCreateController($scope, $http, $q, ContainerFactory, AuthFactory, ConfigFactory,
                                               TokenFactory, $location, $state, ContainerUtils) {
        $scope.loggedInUser = AuthFactory.getUser();
        $scope.params = {};
        $scope.templatedata = [];

        $scope.containerTypes = {};
        $scope.selection = {
            templateName: "",
            containerType: "generic",
            tokens: []
        };

        $scope.allowedTokenTypes = {
            list: [],
            displayPhrase: "All",
            displaySelection: {},
        };

        $scope.functionObject = {};

        $scope.tokenSettings = {
            tokenTypes: {},  // will be set later with response from server
            timesteps: [30, 60],
            otplens: [6, 8],
            hashlibs: ["sha1", "sha256", "sha512"],
            service_ids: {},
            selectedTokenType: ""
        };

        $scope.$watch('selection.containerType', function (newType, oldType) {
            if (newType && $scope.containerTypes[newType]) {
                $scope.allowedTokenTypes = ContainerUtils.setAllowedTokenTypes($scope.selection.containerType,
                    $scope.containerTypes, $scope.tokenSettings.tokenTypes);
                $scope.tokenSettings.selectedTokenType = $scope.allowedTokenTypes.default;
            }
        }, true);

        // Get the supported token types for each container type once
        $scope.getContainerTypes = function () {
            ContainerFactory.getTokenTypes(function (data) {
                // Get all container types and corresponding token types
                $scope.containerTypes = data.result.value;

                // Create display string for supported token types of each container type
                angular.forEach($scope.containerTypes, function (val, containerType) {
                    if (containerType == 'generic') {
                        $scope.containerTypes[containerType].token_types_display = 'All';
                    } else {
                        $scope.containerTypes[containerType].token_types_display = ContainerUtils.createDisplayList(
                            $scope.containerTypes[containerType].token_types);
                    }
                });

                // Sets the supported token types for the selected container type in different formats
                // (list, display list, display selection of each type, default type for the selection)
                $scope.allowedTokenTypes = ContainerUtils.setAllowedTokenTypes($scope.selection.containerType,
                    $scope.containerTypes, $scope.tokenSettings.tokenTypes);
                $scope.tokenSettings.selectedTokenType = $scope.allowedTokenTypes.default;
            });
        };

        $scope.createTemplate = function () {
            $scope.functionObject.saveOpenProperties();
            $scope.params.name = $scope.selection.templateName;
            $scope.params.type = $scope.selection.containerType;
            $scope.params.template_options = {"tokens": $scope.selection.tokens};
            $scope.params.default = $scope.selection.default;

            ContainerFactory.createTemplate($scope.params, function (data) {
                $state.go("token.containertemplates.list");
            });
        };

        // Read the tokentypes from the server
        $scope.getAllContainerAndTokenTypes = function () {
            TokenFactory.getEnrollTokens(function (data) {
                $scope.tokenSettings["tokenTypes"] = data.result.value;
                $scope.getContainerTypes();
            });
        };

        // Initial call
        $scope.getAllContainerAndTokenTypes();

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getAllContainerAndTokenTypes);
    }]);

myApp.controller("containerTemplateEditController", ['$scope', '$http', '$q', 'ContainerFactory', 'AuthFactory',
    'ConfigFactory', 'TokenFactory', '$location', '$state', '$stateParams', 'ContainerUtils',
    function containerTemplateEditController($scope, $http, $q, ContainerFactory, AuthFactory, ConfigFactory,
                                             TokenFactory, $location, $state, $stateParams, ContainerUtils) {
        $scope.loggedInUser = AuthFactory.getUser();
        $scope.params = {};
        $scope.templateData = {};

        $scope.allowedTokenTypes = {
            list: [],
            displayPhrase: "All",
            displaySelection: [],
        };

        $scope.tokenSettings = {
            tokenTypes: {},
            timesteps: [30, 60],
            otplens: [6, 8],
            hashlibs: ["sha1", "sha256", "sha512"],
            service_ids: {},
            selectedType: ""
        };

        $scope.selection = {tokens: []};
        $scope.functionObject = {};

        $scope.get = function () {
            ContainerFactory.getTemplates({"name": $stateParams.templateName},
                function (data) {
                    $scope.templateData = data.result.value["templates"][0];
                    $scope.selection.tokens = $scope.templateData.template_options.tokens;
                    $scope.selection.default = $scope.templateData.default;
                    $scope.getTokenAndContainerTypes();
                });
        };

        // Get the supported token types for each container type once
        $scope.getContainerTypes = function () {
            ContainerFactory.getTokenTypes(function (data) {
                let containerTypes = data.result.value;

                // Create display string for supported token types by the template
                if ($scope.templateData.container_type == 'generic') {
                    containerTypes[$scope.templateData.container_type].token_types_display = 'All';
                } else {
                    containerTypes[$scope.templateData.container_type].token_types_display =
                        ContainerUtils.createDisplayList(containerTypes[$scope.templateData.container_type].token_types);
                }

                // Sets the supported token types for the template in different formats (list, display list,
                // display selection of each type, default type for the selection)
                $scope.allowedTokenTypes = ContainerUtils.setAllowedTokenTypes($scope.templateData.container_type,
                    containerTypes, $scope.tokenSettings.tokenTypes);
                $scope.tokenSettings.selectedTokenType = $scope.allowedTokenTypes.default;
            });
        };

        $scope.saveTemplate = function () {
            $scope.functionObject.saveOpenProperties();
            $scope.params.name = $scope.templateData.name;
            $scope.params.type = $scope.templateData.container_type;
            let tokenList = [];
            angular.forEach($scope.selection.tokens, function (token) {
                if (token.state !== "remove") {
                    if (token.state) {
                        delete token.state;
                    }
                    tokenList.push(token);
                }
            });
            $scope.params.template_options = {"tokens": tokenList};
            $scope.params.default = $scope.selection.default;

            ContainerFactory.createTemplate($scope.params, function (data) {
                $state.go("token.containertemplates.list");
            });
        };

        // Read the token types and container types from the server
        $scope.getTokenAndContainerTypes = function () {
            TokenFactory.getEnrollTokens(function (data) {
                $scope.tokenSettings["tokenTypes"] = data.result.value;
                $scope.getContainerTypes();
            });
        };

        // Initial call
        $scope.get();

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.get);
    }]);
