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

    let helperCreateDisplayList = function (stringList, capitalize) {
        // Creates a comma separated list as a single string out of a list of string objects.
        // Each string is capitalized if capitalize is True.

        let displayList = "";
        angular.forEach(stringList, function (element) {
            let firstChar = element.charAt(0);
            if (capitalize) {
                firstChar = firstChar.toUpperCase();
            }
            displayList += firstChar + element.slice(1) + ", ";
        });
        displayList = displayList.slice(0, -2);

        return displayList;
    }

    this.createDisplayList = function (stringList, capitalize) {
        return helperCreateDisplayList(stringList, capitalize);
    };

    this.setAllowedTokenTypes = function (containerType, tokensForContainerTypes, allTokenTypes) {
        // Returns a dictionary containing the allowed token types for the selected container type in different formats:
        // displayPhrase: single string to display the allowed token types list
        // list: list of token types
        // displaySelection: dictionary with token type as key and display string as value (for the drop-down selection)
        // default: default token type for the selection
        let allowedTokenTypes = {};
        allowedTokenTypes.displayPhrase = tokensForContainerTypes[containerType].token_types_display;
        allowedTokenTypes.list = tokensForContainerTypes[containerType].token_types;
        allowedTokenTypes.displaySelection = {};
        angular.forEach(allowedTokenTypes.list, function (tokenType) {
            let displayString = allTokenTypes[tokenType];
            if (displayString) {
                allowedTokenTypes.displaySelection[tokenType] = displayString;
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

    this.containerTemplateDiffCallback = function (data) {
        // Converts the output of the container template comparison API output to a format that can be displayed
        // for each container a single string of missing and additional tokens is created
        let diffList = data.result.value;
        let templateContainerDiff = diffList;

        angular.forEach(diffList, function (containerDiff, serial) {
            angular.forEach(["missing", "additional"], function (key) {
                templateContainerDiff[serial]["tokens"][key] = helperCreateDisplayList(
                    diffList[serial]["tokens"][key], true);
            });
        });
        return templateContainerDiff;
    };

});

myApp.controller("containerCreateController", ['$scope', '$http', '$q', 'ContainerFactory', '$stateParams',
    'AuthFactory', 'ConfigFactory', 'UserFactory', '$state', 'TokenFactory', 'ContainerUtils', '$timeout', '$location',
    function createContainerController($scope, $http, $q, ContainerFactory, $stateParams,
                                       AuthFactory, ConfigFactory, UserFactory, $state, TokenFactory, ContainerUtils,
                                       $timeout, $location) {
        $scope.formData = {
            containerTypes: {},
        };
        $scope.form = {
            containerType: $scope.default_container_type,
            description: "",
            template: {},
            tokens: []
        };
        $scope.containerClassOptions = {};

        $scope.containerRegister = false;
        $scope.initRegistration = $scope.form.containerType === "smartphone";
        if ($scope.container_wizard["enabled"]) {
            $scope.initRegistration = $scope.container_wizard["registration"];
            $scope.form.containerType = $scope.container_wizard["type"];
        }
        $scope.passphrase = {"user": false, "prompt": "", "response": ""};

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

        $scope.functionObject = {};
        $scope.editTemplate = false;
        $scope.showTokenEnrolled = false;
        $scope.qrCodeWidth = 250;

        $scope.$watch('form.containerType', function (newType, oldVal) {
            if (newType && $scope.formData.containerTypes[newType]) {
                $scope.allowedTokenTypes = ContainerUtils.setAllowedTokenTypes($scope.form.containerType,
                    $scope.formData.containerTypes, $scope.tokenSettings.tokenTypes);
                $scope.tokenSettings.selectedTokenType = $scope.allowedTokenTypes.default;

                $scope.selectTemplate(true);
                $scope.editTemplate = false;

                $scope.initRegistration = newType === "smartphone";
            }
        }, true);

        // Get the supported token types for each container type once
        $scope.getContainerTypes = function () {
            ContainerFactory.getTokenTypes(function (data) {
                if ($scope.container_wizard["enabled"]) {
                    // Container wizard only allows to create the defined container type
                    $scope.formData.containerTypes[$scope.container_wizard["type"]] =
                        data.result.value[$scope.container_wizard["type"]];
                } else {
                    $scope.formData.containerTypes = data.result.value;
                }

                // Create display string for supported token types of each container type
                angular.forEach($scope.formData.containerTypes, function (_, containerType) {
                    if (containerType === 'generic') {
                        $scope.formData.containerTypes[containerType]["token_types_display"] = 'All';
                    } else {
                        $scope.formData.containerTypes[containerType]["token_types_display"] = ContainerUtils.createDisplayList(
                            $scope.formData.containerTypes[containerType].token_types, true);
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
                        $scope.newUser = {user: "", realm: realmname, realmOnly: false};
                    }
                    // if there is a default realm, preset the default realm
                    if (realm.default && !$stateParams.realmname) {
                        $scope.newUser = {user: "", realm: realmname, realmOnly: false};
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
            $scope.newUser = {
                user: AuthFactory.getUser().username,
                realm: AuthFactory.getUser().realm,
                realmOnly: false
            };
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

        $scope.defaultTemplates = {};
        $scope.templates = {};
        $scope.getTemplates = function () {
            // Get the templates from the db
            ContainerFactory.getTemplates({}, function (data) {
                let templatesList = data.result.value.templates;
                // sort them by the container type and add for each type a "No Template" option
                angular.forEach(["generic", "smartphone", "yubikey"], function (containerType) {
                    $scope.templates[containerType] = {
                        "No Template": {
                            "name": "noTemplate",
                            "template_display": "No Template"
                        }
                    };
                });
                // default selection
                $scope.form.template = $scope.templates["generic"]["No Template"];
                // Sort the templates by the container type
                angular.forEach(templatesList, function (template) {
                    $scope.templates[template.container_type][template.name] = template;
                    // create display string with all contained token types
                    let templateTokenTypes = [];
                    angular.forEach(template.template_options.tokens, function (token) {
                        templateTokenTypes.push(token.type);
                    });
                    template["template_display"] = template.name + ": "
                        + ContainerUtils.createDisplayList(templateTokenTypes, true);
                    if (template.default) {
                        // save default template
                        $scope.defaultTemplates[template.container_type] = template;
                    }
                });
                $scope.selectTemplate(true);
            });
        };

        $scope.selectTemplate = function (defaultSelection) {
            // Sets all template options according to the selected template
            // optionally first selects the default template if defaultSelection is true
            if ($scope.container_wizard["enabled"]) {
                if ($scope.container_wizard["template"]) {
                    $scope.form.template = $scope.templates[$scope.form.containerType][$scope.container_wizard["template"]];
                }
            } else if (defaultSelection) {
                // select default template if one exists or no template otherwise
                $scope.form.template = $scope.defaultTemplates[$scope.form.containerType];
            }

            if (!$scope.form.template) {
                $scope.form.template = $scope.templates[$scope.form.containerType]["No Template"];
            }

            if ($scope.form.template.name === "noTemplate") {
                // close edit dialog
                $scope.editTemplate = false;
            }

            // set tokens according to the selected template
            let templateOptions = $scope.form.template.template_options;
            if (templateOptions !== undefined) {
                $scope.form.tokens = templateOptions.tokens || [];
            } else {
                // no template is used or the template has no options
                $scope.form.tokens = [];
            }
        };

        $scope.createContainer = function () {
            let ctype = $scope.form.containerType;
            let params = {"type": ctype};
            if (templateListRight && $scope.form.template && $scope.form.template.name !== "noTemplate") {
                params["template"] = $scope.form.template;
                params["template"]["template_options"]["tokens"] = [];
                if ($scope.form.tokens.length > 0) {
                    angular.forEach($scope.form.tokens, function (token) {
                        if (token.state === "add") {
                            delete token.state;
                        }
                        if (token.state !== "remove") {
                            params["template"]["template_options"]["tokens"].push(token);
                        }
                    });
                }
            }

            if ($scope.newUser.user) {
                params["user"] = fixUser($scope.newUser.user);
                params["realm"] = $scope.newUser.realm;
            }
            if ($scope.newUser.realmOnly && $scope.newUser.realm) {
                params["realm"] = $scope.newUser.realm;
            }
            if ($scope.form.description) {
                params["description"] = $scope.form.description;
            }

            ContainerFactory.createContainer(params, function (data) {
                $scope.containerSerial = data.result.value.container_serial;
                let stay = false;
                if ($scope.initRegistration && AuthFactory.checkRight('container_register')) {
                    let registrationParams =
                        {
                            "container_serial": $scope.containerSerial,
                            "passphrase_user": $scope.passphrase.user,
                            "passphrase_prompt": $scope.passphrase.prompt,
                            "passphrase_response": $scope.passphrase.response
                        };
                    ContainerFactory.initializeRegistration(registrationParams, function (registrationData) {
                        $scope.containerRegister = true;
                        $scope.containerRegistrationURL = registrationData.result.value['container_url']['value'];
                        $scope.containerRegistrationQR = registrationData.result.value['container_url']['img'];
                        $scope.pollContainerDetails();
                    });
                    stay = true;
                }
                if (data.result.value.tokens) {
                    $scope.showTokenEnrolled = true;
                    $scope.tokenInitData = data.result.value.tokens;
                    stay = true;

                    angular.forEach($scope.tokenInitData, function (initData, serial) {
                        if (initData.otps) {
                            const otpsCount = Object.keys(initData.otps).length;
                            let otpRowCount = parseInt(otpsCount / 5 + 0.5);
                            let otp_rows = Object.keys(initData.otps).slice(0, otpRowCount);
                            initData["otp_rows"] = otp_rows;
                            initData["otp_row_count"] = otpRowCount;
                        }
                        if (initData.webAuthnRegisterRequest) {
                            $scope.click_wait = true;
                        }
                    });
                }
                if ($scope.container_wizard["enabled"]) {
                    $scope.containerCreated = true;
                    stay = true;
                }
                if (!stay) {
                    $state.go("token.containerdetails", {"containerSerial": $scope.containerSerial});
                }

            });
        };

        $scope.regenerateToken = function (serial) {
            let initParams = $scope.tokenInitData[serial].init_params;
            initParams["serial"] = serial;
            TokenFactory.enroll({}, initParams, function (data) {
                $scope.tokenInitData[serial] = data.detail;
                $scope.tokenInitData[serial].initParams = initParams;
                $scope.tokenInitData[serial].type = initParams.type;
            });
        };

        $scope.verifyTokenCallback = function (response) {
            $scope.tokenInitData[response.detail.serial]["rollout_state"] = response.detail.rollout_state;
        };

        $scope.pollContainerDetails = function () {
            ContainerFactory.getContainerForSerial($scope.containerSerial, function (data) {
                if (data.result.value.containers.length > 0) {
                    let container = data.result.value.containers[0];
                    let registrationState = container.info['registration_state'];
                    if (registrationState === "client_wait" && $location.path() === "/token/container") {
                        // stop polling if the page changed or the container was (un)registered
                        $timeout($scope.pollContainerDetails, 2500);
                    } else if (registrationState === "registered") {
                        // container successfully registered, move to details page
                        if (!$scope.container_wizard["enabled"]) {
                            $state.go("token.containerdetails", {"containerSerial": $scope.containerSerial});
                        } else {
                            $scope.containerRegister = false;
                            $scope.registeredSuccessfully = true;
                        }
                    }
                }
            });
        };

        // Read the token types and container types from the server
        $scope.getTokenAndContainerTypes = function () {
            TokenFactory.getEnrollTokens(function (data) {
                $scope.tokenSettings["tokenTypes"] = data.result.value;
                $scope.getContainerTypes();
            });
        };

        const templateListRight = AuthFactory.checkRight('container_template_list');
        if (templateListRight) {
            $scope.getTemplates();
        }
        $scope.getTokenAndContainerTypes();
    }]);

myApp.controller("containerListController", ['$scope', '$http', '$q', 'ContainerFactory', 'AuthFactory',
    'ConfigFactory', 'TokenFactory',
    function containerListController($scope, $http, $q, ContainerFactory, AuthFactory, ConfigFactory, TokenFactory) {
        $scope.containersPerPage = $scope.token_page_size;
        $scope.loggedInUser = AuthFactory.getUser();
        $scope.params = {sortdir: "asc"};
        $scope.containerdata = [];
        $scope.filter = {serial: "", type: "", realm: "", description: ""}

        // Change the pagination
        $scope.pageChanged = function () {
            $scope.get();
        };

        // Get all containers
        $scope.get = function () {
            $scope.expandedRows = [];

            $scope.params.container_serial = "*" + $scope.filter.serial + "*";
            $scope.params.container_realm = "*" + $scope.filter.realm + "*";
            $scope.params.type = "*" + $scope.filter.type + "*";
            $scope.params.description = "*" + $scope.filter.description + "*";

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
    'AuthFactory', 'ConfigFactory', 'TokenFactory', '$state', '$rootScope', '$timeout', '$location', 'ContainerUtils',
    'inform', 'gettextCatalog',
    function containerDetailsController($scope, $http, $stateParams, $q, ContainerFactory, AuthFactory, ConfigFactory,
                                        TokenFactory, $state, $rootScope, $timeout, $location, ContainerUtils, inform,
                                        gettextCatalog) {
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

        $scope.editContainerInfo = false;
        $scope.containerInfoOptions = {};
        $scope.selectedInfoOptions = {};

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
            let params = {
                container_serial: $scope.containerSerial,
                user: fixUser($scope.containerOwner.user_name),
                realm: $scope.containerOwner.user_realm,
                user_id: $scope.containerOwner.user_id,
                resolver: $scope.containerOwner.user_resolver
            }
            ContainerFactory.unassignUser(
                params
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
        $scope.passphrase = {"user": false, "prompt": "", "response": ""};
        $scope.offline_tokens = [];
        $scope.registerContainer = function (rollover) {
            let registrationParams =
                {
                    "container_serial": $scope.containerSerial,
                    "passphrase_user": $scope.passphrase.user,
                    "passphrase_prompt": $scope.passphrase.prompt,
                    "passphrase_response": $scope.passphrase.response,
                    "rollover": rollover
                };
            ContainerFactory.initializeRegistration(registrationParams, function (data) {
                if ($scope.container.type === "smartphone") {
                    $scope.showQR = true;
                    $scope.containerRegistrationURL = data.result.value['container_url']['value'];
                    $scope.containerRegistrationQR = data.result.value['container_url']['img'];
                    $scope.offline_tokens = data.result.value['offline_tokens'];
                }
                $scope.registrationOptions = {"open": false};
                // Set registration state to start the polling
                $scope.container.info["registration_state"] = "client_wait";
                $scope.pollContainerDetails();
            });
        };

        $scope.showDisableAllTokens = -1.0;
        $scope.startCountdown = 5;
        $scope.unregisterContainer = function () {
            ContainerFactory.terminateRegistration($scope.containerSerial, function () {
                $scope.showQR = false;
                $scope.getContainer();
                $scope.showDisableAllTokens = $scope.startCountdown;
                $scope.disableCountdown();
            });
        };
        $scope.disableCountdown = function () {
            // Recursively call this function every 250 ms until the countdown is over
            if ($scope.showDisableAllTokens >= -0.25) {
                $timeout(function () {
                    $scope.showDisableAllTokens -= 0.25;
                    $scope.disableCountdown();
                }, 250);
            }
        };

        $scope.pollContainerDetails = function () {
            $scope.getContainer();
            let details_path = "/token/container/details/" + $scope.containerSerial;
            let registration_state = $scope.container.info['registration_state'];
            if ((registration_state === "client_wait" || registration_state === "rollover")
                && $location.path() === details_path) {
                // stop polling if the page changed or the container was (un)registered
                $timeout($scope.pollContainerDetails, 2500);
            }
        };

        $scope.showDiff = false;
        $scope.compareWithTemplate = function (template) {

            ContainerFactory.compareTemplateWithContainers(
                $scope.container.template, {"container_serial": $scope.container.serial},
                function (data) {
                    $scope.templateContainerDiff = ContainerUtils.containerTemplateDiffCallback(data);
                    $scope.showDiff = true;
                }
            );
        };

        // Check if the user has any registration rights relevant for each state
        const register_allowed = $scope.checkRight('container_register');
        const unregister_allowed = $scope.checkRight('container_unregister');
        const rollover_allowed = $scope.checkRight('container_rollover');
        $scope.anyRegistrationRights = {
            "none": register_allowed,
            "client_wait": register_allowed || unregister_allowed,
            "registered": unregister_allowed || rollover_allowed,
            "rollover": unregister_allowed || rollover_allowed,
            "rollover_completed": unregister_allowed || rollover_allowed
        };
        // Check if the user has either registration or rollover rights depending on the state
        $scope.registrationOrRolloverRights = {
            "none": register_allowed,
            "client_wait": register_allowed,
            "registered": rollover_allowed,
            "rollover": rollover_allowed,
            "rollover_completed": rollover_allowed
        };

        if ($scope.loggedInUser.isAdmin) {
            // These are functions that can only be used by administrators.
            // If the user is admin, we can fetch all realms
            // If the loggedInUser is only a user, we do not need the realm list,
            // as we do not assign a user
            ConfigFactory.getRealms(function (data) {
                $scope.realms = data.result.value;
                angular.forEach($scope.realms, function (realm, realmname) {
                    // if there is a default realm, preset the default realm
                    if (realm.default && !$scope.newUser.realm && !$scope.newUser.user) {
                        $scope.newUser = {user: "", realm: realmname};
                    }
                });
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

        $scope.allTokensDisabled = function () {
            let allDisabled = true;
            angular.forEach($scope.container.tokens, function (token) {
                if (token.active) {
                    allDisabled = false;
                }
            });
            return allDisabled;
        };

        $scope.disableAllTokens = function () {
            let tokenSerialList = $scope.getAllTokenSerials();
            angular.forEach(tokenSerialList, function (serial) {
                $scope.disableToken(serial);
            });
            if ($scope.showDisableAllTokens > 0) {
                $scope.showDisableAllTokens = 0;
            }
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
            let tokenSerialStr = tokenSerialList.join(',');
            TokenFactory.deleteBatch({"serial": tokenSerialStr}, function (data) {
                // Delete container
                callback();
                // Error message if some tokens could not be deleted
                let failedTokens = []
                angular.forEach(data.result.value, function (success, serial) {
                    if (!success) {
                        failedTokens.push(serial);
                    }
                });
                if (failedTokens.length > 0) {
                    console.warn("Some tokens could not be deleted: " + failedTokens.join(", "));
                    inform.add(gettextCatalog.getString("Some tokens could not be deleted: " + failedTokens.join(", ")),
                        {type: "danger", ttl: 10000});
                }
            });
            $scope.showDialogAll = false;
        };

        $scope.assignUserToAllTokens = function () {
            if ($scope.containerOwner) {
                let tokensToAssign = [];
                angular.forEach($scope.container.tokens, function (token, index) {
                    if (token.username === "") {
                        tokensToAssign.push(token.serial);
                    }
                });

                angular.forEach(tokensToAssign, function (serial, index) {
                    let params = {
                        serial: serial,
                        user: $scope.containerOwner.user_name,
                        realm: $scope.containerOwner.user_realm
                    }
                    if (index == tokensToAssign.length - 1) {
                        TokenFactory.assign(params, $scope.getContainer);
                    } else {
                        TokenFactory.assign(params, function (data) {
                        });
                    }

                });
            }
        };

        $scope.unassignUsersFromAllTokens = function () {
            // Get tokens with the same user as the container owner
            let tokensToUnassign = [];
            angular.forEach($scope.container.tokens, function (token, index) {
                if (token.username === $scope.containerOwner.user_name && token.user_realm === $scope.containerOwner.user_realm) {
                    tokensToUnassign.push(token.serial);
                }
            });
            // Unassign the user from the tokens
            angular.forEach(tokensToUnassign, function (serial, index) {
                if (index == tokensToUnassign.length - 1) {
                    TokenFactory.unassign(serial, $scope.getContainer);
                } else {
                    TokenFactory.unassign(serial, function (data) {
                    });
                }
            });
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
