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

myApp.controller("containerTemplateController", ['$scope', '$http', '$q', 'ContainerFactory', 'AuthFactory',
    'ConfigFactory', 'TokenFactory', '$location', '$state', 'ContainerUtils',
    function containerTemplateController($scope, $http, $q, ContainerFactory, AuthFactory, ConfigFactory, TokenFactory,
                                         $location, $state, ContainerUtils) {
        $scope.templatesPerPage = $scope.token_page_size;
        $scope.loggedInUser = AuthFactory.getUser();
        $scope.params = {sortby: "name", sortdir: "asc", pagesize: $scope.templatesPerPage};
        $scope.templatedata = [];
        $scope.templatesReady = false;

        // Get all templates
        $scope.getAllTemplates = function () {
            $scope.templatesReady = false;
            ContainerFactory.getTemplates($scope.params,
                function (data) {
                    $scope.templatedata = data.result.value;
                    $scope.templatesReady = true;
                });
        };

        // Read the token types from the server
        $scope.tokenSettings = {
            tokenTypes: {},
            timesteps: [30, 60],
            otplens: [6, 8],
            hashlibs: ["sha1", "sha256", "sha512"],
            service_ids: {},
            selectedTokenType: ""
        };
        $scope.getAllContainerAndTokenTypes = function () {
            $scope.typesReady = false;
            TokenFactory.getEnrollTokens(function (data) {
                $scope.tokenSettings["tokenTypes"] = data.result.value;
                $scope.getContainerTypes();
            });
        };

        // Get the supported token types for each container type once
        $scope.containerTypes = {};

        $scope.getContainerTypes = function () {
            ContainerFactory.getTemplateTokenTypes(function (data) {
                // Get all container types and corresponding token types
                $scope.containerTypes = data.result.value;

                // Create display string for supported token types of each container type
                angular.forEach($scope.containerTypes, function (val, containerType) {
                    $scope.containerTypes[containerType].token_types_display = ContainerUtils.createDisplayList(
                        $scope.containerTypes[containerType].token_types, true);
                });
                $scope.typesReady = true;
            });
        };

        $scope.getAllTemplates();
        $scope.getAllContainerAndTokenTypes();

        if ($location.path() === "token.containertemplates") {
            $location.path("token.containertemplates.list");
        }
    }]);


myApp.controller("containerTemplateListController", ['$scope', '$http', '$q', 'ContainerFactory', 'AuthFactory',
    'ConfigFactory', 'TokenFactory', '$location', '$state',
    function containerTemplateListController($scope, $http, $q, ContainerFactory, AuthFactory, ConfigFactory,
                                             TokenFactory, $location, $state) {

        // Change the pagination
        $scope.pageChanged = function () {
            $scope.getAllTemplates();
        };

        // get templates sorted: called from pi-sort-by directive
        // directive can only interact with the list controller and not with the parent controller
        $scope.get = function () {
            $scope.params.sortby = $scope.sortby;
            if ($scope.reverse) {
                $scope.params.sortdir = "desc";
            } else {
                $scope.params.sortdir = "asc";
            }
            $scope.getAllTemplates();
        };

        $scope.editTemplate = function (templateName) {
            $state.go("token.containertemplates.edit", {"templateName": templateName});
        };

        $scope.deleteTemplate = function (templateName) {
            ContainerFactory.deleteTemplate(templateName, $scope.get);
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.get);
    }]);

myApp.controller("containerTemplateCreateController", ['$scope', '$http', '$q', 'ContainerFactory', 'AuthFactory',
    'ConfigFactory', 'TokenFactory', '$location', '$state', 'ContainerUtils',
    function containerTemplateCreateController($scope, $http, $q, ContainerFactory, AuthFactory, ConfigFactory,
                                               TokenFactory, $location, $state, ContainerUtils) {
        $scope.params = {};
        $scope.containerClassOptions = {};

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

        $scope.tokenSettings.selectedTokenType = $scope.allowedTokenTypes.default;

        $scope.$watch('selection.containerType', function (newType, oldType) {
            if (newType && $scope.containerTypes[newType]) {
                // Set the supported token types for the new container type
                $scope.allowedTokenTypes = ContainerUtils.setAllowedTokenTypes($scope.selection.containerType,
                    $scope.containerTypes, $scope.tokenSettings.tokenTypes);
                $scope.tokenSettings.selectedTokenType = $scope.allowedTokenTypes.default;

                // Check if the selected token types are still allowed for the new container type
                let selectedTokens = $scope.selection.tokens;
                $scope.selection.tokens = [];
                angular.forEach(selectedTokens, function (token) {
                    if ($scope.allowedTokenTypes.list.includes(token.type)) {
                        $scope.selection.tokens.push(token);
                    }
                });
            }
        }, true);

        let existingTemplateNames = [];
        angular.forEach($scope.templatedata.templates, function (template) {
            existingTemplateNames.push(template.name);
        });

        $scope.$watch('selection.templateName', function (newName, oldName) {
            if (newName && existingTemplateNames.includes(newName)) {
                $scope.invalidName = true;
            } else {
                $scope.invalidName = false;
            }
        }, true);

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
                $scope.getAllTemplates();
                $state.go("token.containertemplates.list");
            });
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getAllContainerAndTokenTypes);
    }]);

myApp.controller("containerTemplateEditController", ['$scope', '$http', '$q', 'ContainerFactory', 'AuthFactory',
    'ConfigFactory', 'TokenFactory', '$location', '$state', '$stateParams', 'ContainerUtils',
    function containerTemplateEditController($scope, $http, $q, ContainerFactory, AuthFactory, ConfigFactory,
                                             TokenFactory, $location, $state, $stateParams, ContainerUtils) {
        $scope.containerClassOptions = {};
        $scope.template = {};

        $scope.selection = {containerType: "", tokens: []};
        $scope.functionObject = {};

        $scope.containersPerPage = $scope.token_page_size;
        $scope.params = {"template": $stateParams.templateName, sortdir: "asc"};
        $scope.containerData = [];
        $scope.showContainers = false;
        $scope.templateContainerDiff = {};
        $scope.showDiff = false;

        $scope.allowedTokenTypes = {
            list: [],
            displayPhrase: "All",
            displaySelection: {},
        };

        $scope.getOneTemplate = function () {
            angular.forEach($scope.templatedata.templates, function (template) {
                if (template.name === $stateParams.templateName) {
                    $scope.template = template;
                    $scope.selection.containerType = $scope.template.container_type;
                    $scope.selection.tokens = $scope.template.template_options.tokens || [];
                    $scope.selection.default = $scope.template.default || false;

                    // Sets the supported token types for the selected container type in different formats
                    // (list, display list, display selection of each type, default type for the selection)
                    $scope.allowedTokenTypes = ContainerUtils.setAllowedTokenTypes($scope.selection.containerType,
                        $scope.containerTypes, $scope.tokenSettings.tokenTypes);
                    $scope.tokenSettings.selectedTokenType = $scope.allowedTokenTypes.default;
                }
            });
        }

        // Wait for the templateController to finish loading the templates and token types
        $scope.$watch('templatesReady', function (newTemplatesReady, oldVal) {
            if (newTemplatesReady && $scope.typesReady && !oldVal) {
                $scope.getOneTemplate();
            }
        }, true);
        $scope.$watch('typesReady', function (newTypesReady, oldVal) {
            if (newTypesReady && $scope.templatesReady && !oldVal) {
                $scope.getOneTemplate();
            }
        }, true);

        // Initially get the template if data is already loaded
        if ($scope.templatesReady && $scope.typesReady) {
            $scope.getOneTemplate();
        }

        // Get containers created with the template
        $scope.getContainers = function () {
            $scope.params.sortby = $scope.sortby;
            if ($scope.reverse) {
                $scope.params.sortdir = "desc";
            } else {
                $scope.params.sortdir = "asc";
            }
            $scope.params.pagesize = $scope.token_page_size;
            ContainerFactory.getContainers($scope.params, function (data) {
                $scope.containerData = data.result.value;
            });
        };

        // Change the pagination
        $scope.pageChanged = function () {
            $scope.getContainers();
        };

        $scope.compareContainersWithTemplate = function () {
            $scope.showDiff = true;
            ContainerFactory.compareTemplateWithContainers($stateParams.templateName, {}, function (data) {
                $scope.templateContainerDiff = ContainerUtils.containerTemplateDiffCallback(data);
            })
        };

        $scope.saveTemplate = function () {
            $scope.functionObject.saveOpenProperties();
            $scope.params.name = $scope.template.name;
            $scope.params.type = $scope.template.container_type;

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
                $scope.getAllTemplates();
                $state.go("token.containertemplates.list");
            });
        };

        // Initial calls
        $scope.getContainers();

        $scope.editGet = function () {
            $scope.getAllTemplates();
            $scope.getContainers();
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.editGet);
    }]);

