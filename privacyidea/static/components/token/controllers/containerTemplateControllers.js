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
 * SPDX-FileCopyrightText: 2024 Jelina Unger <jelina.unger@netknights.it>
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

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
        $scope.containerClassOptions = {};

        $scope.containerTypes = {};
        $scope.selection = {
            templateName: "",
            containerType: "generic",
            options: {},
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
                // Set the supported token types for the new container type
                $scope.allowedTokenTypes = ContainerUtils.setAllowedTokenTypes($scope.selection.containerType,
                    $scope.containerTypes, $scope.tokenSettings.tokenTypes);
                $scope.tokenSettings.selectedTokenType = $scope.allowedTokenTypes.default;

                // TODO: Check if the selected token types are still allowed for the new container type
            }
        }, true);

        // Get the supported token types for each container type once
        $scope.getContainerTypes = function () {
            ContainerFactory.getTemplateTokenTypes(function (data) {
                // Get all container types and corresponding token types
                $scope.containerTypes = data.result.value;

                // Create display string for supported token types of each container type
                angular.forEach($scope.containerTypes, function (val, containerType) {
                    $scope.containerTypes[containerType].token_types_display = ContainerUtils.createDisplayList(
                        $scope.containerTypes[containerType].token_types, true);
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
            angular.forEach($scope.selection.options, function (value, key) {
                if (value === "-") {
                    delete $scope.selection.options[key];
                }
            });
            $scope.params.template_options = {"tokens": $scope.selection.tokens, "options": $scope.selection.options};
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
        $scope.containerClassOptions = {};

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

        $scope.selection = {containerType: "", options: {}, tokens: []};
        $scope.initialOptions = {};
        $scope.functionObject = {};

        $scope.containerData = [];
        $scope.showContainers = false;
        $scope.templateContainerDiff = {};
        $scope.showDiff = false;

        $scope.get = function () {
            ContainerFactory.getTemplates({"name": $stateParams.templateName},
                function (data) {
                    $scope.templateData = data.result.value["templates"][0];
                    $scope.selection.containerType = $scope.templateData.container_type;
                    $scope.selection.tokens = $scope.templateData.template_options.tokens || [];
                    $scope.selection.default = $scope.templateData.default || false;
                    $scope.initialOptions[$scope.selection.containerType] = $scope.templateData.template_options.options || {};
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
                        ContainerUtils.createDisplayList(containerTypes[$scope.templateData.container_type].token_types,
                            true);
                }

                // Sets the supported token types for the template in different formats (list, display list,
                // display selection of each type, default type for the selection)
                $scope.allowedTokenTypes = ContainerUtils.setAllowedTokenTypes($scope.templateData.container_type,
                    containerTypes, $scope.tokenSettings.tokenTypes);
                $scope.tokenSettings.selectedTokenType = $scope.allowedTokenTypes.default;
            });
        };

        // Read the token types and container types from the server
        $scope.getTokenAndContainerTypes = function () {
            TokenFactory.getEnrollTokens(function (data) {
                $scope.tokenSettings["tokenTypes"] = data.result.value;
                $scope.getContainerTypes();
            });
        };

        // Get containers created with the template
        $scope.getContainers = function () {
            let params = {"template": $stateParams.templateName}
            ContainerFactory.getContainers(params, function (data) {
                $scope.containerData = data.result.value;
            });
        };

        $scope.compareContainersWithTemplate = function () {
            $scope.showDiff = true;
            ContainerFactory.compareTemplateWithContainers($stateParams.templateName, {}, function (data) {
                $scope.templateContainerDiff = ContainerUtils.containerTemplateDiffCallback(data);
            })
        };

        $scope.saveTemplate = function () {
            $scope.functionObject.saveOpenProperties();
            $scope.params.name = $scope.templateData.name;
            $scope.params.type = $scope.templateData.container_type;
            angular.forEach($scope.selection.options, function (value, key) {
                if (value === "-") {
                    delete $scope.selection.options[key];
                }
            });

            let tokenList = [];
            angular.forEach($scope.selection.tokens, function (token) {
                if (token.state !== "remove") {
                    if (token.state) {
                        delete token.state;
                    }
                    tokenList.push(token);
                }
            });
            $scope.params.template_options = {"tokens": tokenList, "options": $scope.selection.options};
            $scope.params.default = $scope.selection.default;

            ContainerFactory.createTemplate($scope.params, function (data) {
                $state.go("token.containertemplates.list");
            });
        };

        // Initial call
        $scope.get();
        $scope.getContainers();

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.get);
    }]);

