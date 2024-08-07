myApp.controller("realmController", ["$scope", "$location", "$rootScope", "$state", "ConfigFactory",
    function ($scope, $location, $rootScope, $state, ConfigFactory) {
        // redirect to the list view
        if ($location.path() === "/config/realms") {
            $location.path("/config/realms/list");
        }

        $scope.nodes = {"All": "All"};
        $scope.nodesById = {};
        $scope.nodesDisplayString = {"All": "All Nodes"};

        $scope.getNodes = function () {
            $scope.nodeNames = [];
            $scope.numNodes = 0;
            ConfigFactory.getNodes(function (data) {
                const nodeList = data.result.value;
                angular.forEach(nodeList, function (node) {
                    $scope.nodes[node.name] = node.uuid;
                    $scope.nodesById[node.uuid] = node.name;
                    $scope.numNodes++;
                    $scope.nodeNames.push({"name": node.name, "ticked": false});
                    $scope.nodesDisplayString[node.name] = node.name;
                });
            });
        };
        $scope.getNodes();

        $scope.setRealmNode = function (realmName, selectedResolvers) {
            const nodeName = Object.keys(selectedResolvers)[0];
            const res = selectedResolvers[nodeName];
            let resolvers = [];

            if (!nodeName || nodeName === "All" || nodeName === $scope.nodesDisplayString["All"]) {
                // realm without node specification
                // Format resolvers
                let pObject = {};
                angular.forEach(res, function (value, resolverName) {
                    if (value.selected === true) {
                        resolvers.push(resolverName);
                        pObject["priority." + resolverName] = value.priority;
                    }
                });
                pObject.resolvers = resolvers.join(',');

                ConfigFactory.setRealm(realmName, pObject, function (data) {
                    delete (selectedResolvers[nodeName]);
                    if (Object.keys(selectedResolvers).length > 0) {
                        $scope.setRealmNode(realmName, selectedResolvers);
                    } else {
                        $location.path("/config/realms/list");
                        $scope.reload();
                        return;
                    }
                });
            } else {
                // Node-specific realms
                // Format resolvers
                angular.forEach(res, function (value, resolverName) {
                    if (value.selected === true) {
                        const resolver = {"name": resolverName, "priority": value.priority};
                        resolvers.push(resolver);
                    }
                });
                const resolversDict = {"resolver": resolvers};
                ConfigFactory.setRealmNode(realmName, $scope.nodes[nodeName], resolversDict, function (data) {
                    delete (selectedResolvers[nodeName]);
                    if (Object.keys(selectedResolvers).length > 0) {
                        $scope.setRealmNode(realmName, selectedResolvers);
                    } else {
                        $location.path("/config/realms/list");
                        $scope.reload();
                        return;
                    }
                });
            }
        };
    }]);

myApp.controller("realmListController", ["$scope", "$location", "$rootScope", "$state", "$stateParams", "ConfigFactory",
    function ($scope, $location, $rootScope, $state, $stateParams, ConfigFactory) {

        $scope.selectedNode = {"name": "All"};
        $scope.newRealmParams = {"realmName": "", "node": "All"};
        $scope.selectedResolvers = {};

        $scope.getRealms = function () {
            ConfigFactory.getRealms(function (data) {
                $scope.realms = data.result.value;
                $scope.sortByNodes();
            });
        };

        $scope.sortByNodes = function () {
            $scope.realmByNodes = {};
            $scope.realmByNodes["All"] = {};
            angular.forEach($scope.realms, function (realm, realmName) {
                realm["nodes"] = {};
                for (let i = 0; i < realm.resolver.length; i++) {
                    // sort resolvers by nodes for the realm
                    let resObj = realm.resolver[i];
                    if (!realm.nodes[resObj.node]) {
                        realm.nodes[resObj.node] = [];
                    }
                    realm.nodes[resObj.node].push(resObj);

                    // sort realm by nodes
                    if (!$scope.realmByNodes[resObj.node]) {
                        // Initialize the node's dict
                        $scope.realmByNodes[resObj.node] = {};
                    }
                    $scope.realmByNodes[resObj.node][realmName] = realm;
                    $scope.realmByNodes["All"][realmName] = realm;
                }
            })
        };

        $scope.delRealm = function (name) {
            ConfigFactory.delRealm(name, function (data) {
                $scope.set_result = data.result.value;
                $scope.getRealms();
            });
        };

        $scope.setDefaultRealm = function (name) {
            ConfigFactory.setDefaultRealm(name, function (data) {
                $scope.set_result = data.result.value;
                $scope.getRealms();
            });
        };

        $scope.clearDefaultRealm = function () {
            ConfigFactory.clearDefaultRealm(function (data) {
                $scope.set_result = data.result.value;
                $scope.getRealms();
            });
        };

        $scope.createRealmInPlace = function (realmName, nodeName, selectedResolvers) {
            let nodesSpecificResolvers = {};
            nodesSpecificResolvers[nodeName] = selectedResolvers;
            $scope.setRealmNode(realmName, nodesSpecificResolvers);
            $scope.newRealmParams.realmName = "";
            $scope.newRealmParams.node = "All";
            $scope.selectedResolvers = {};
        }

        $scope.startEdit = function (realmName, realm) {
            if ($scope.numNodes <= 1) {
                // Only one node: edit in list
                $scope.editRealm = realmName;
                // fill the selectedResolvers with the resolver of the realm
                $scope.selectedResolvers = {};
                angular.forEach(realm.resolver, function (resolver, _keyreso) {
                    $scope.selectedResolvers[resolver.name] = {
                        selected: true,
                        priority: resolver.priority
                    };
                });
            } else {
                // redirect to create/edit page
                $state.go("config.realms.edit", {
                    "realmName": realmName,
                    "realm": $scope.realms[realmName]
                });
            }

        };

        $scope.cancelEdit = function () {
            $scope.editRealm = null;
            $scope.selectedResolvers = {};
        };

        $scope.getRealms();

        // listen to the reload broadcast
        $scope.$on("piReload", function () {
            $scope.getRealms();
        });
    }]);

myApp.controller("realmCreateController", ["$scope", "$location", "$rootScope", "$state", "$stateParams",
    function ($scope, $location, $rootScope, $state, $stateParams) {

        $scope.selectedResolvers = {};
        $scope.realmName = "";
        $scope.selectedNodes = [];
        $scope.editRealm = false;

        $scope.applyDefaultResolversToNodes = function () {
            angular.forEach($scope.selectedNodes, function (node) {
                $scope.selectedResolvers[node.name] = angular.copy($scope.selectedResolvers["All"]);
            });
        };

    }]);

myApp.controller("realmEditController", ["$scope", "$location", "$rootScope", "$state", "$stateParams",
    function ($scope, $location, $rootScope, $state, $stateParams) {

        $scope.selectedResolvers = {};
        $scope.realmName = "";
        $scope.selectedNodes = [];
        $scope.editRealm = true;

        $scope.getStateParams = function () {
            if ($stateParams.realmName) {
                $scope.realmName = $stateParams.realmName;
                // Get realm
                if ($stateParams.realm) {
                    const realm = $stateParams.realm;
                    let resolverNodeNames = {};
                    angular.forEach(realm.resolver, function (resolver) {
                        // Extract node names
                        let nodeName = $scope.nodesById[resolver.node];
                        if (!nodeName || nodeName === "") {
                            nodeName = "All";
                        } else {
                            resolverNodeNames[nodeName] = true;
                        }

                        // Get resolvers
                        if (!$scope.selectedResolvers[nodeName]) {
                            // Init dict
                            $scope.selectedResolvers[nodeName] = {};
                        }
                        $scope.selectedResolvers[nodeName][resolver.name] = {
                            selected: true,
                            priority: resolver.priority
                        };
                    });

                    // Select nodes
                    angular.forEach(resolverNodeNames, function (node, nodeName) {
                        for (let i = 0; i < $scope.nodeNames.length; i++) {
                            if ($scope.nodeNames[i].name === nodeName) {
                                $scope.nodeNames[i].ticked = true;
                                break;
                            }
                        }
                    });
                }
            }
        };

        $scope.getStateParams();

        $scope.applyDefaultResolversToNodes = function () {
            angular.forEach($scope.selectedNodes, function (node) {
                $scope.selectedResolvers[node.name] = angular.copy($scope.selectedResolvers["All"]);
            });
        };

    }]);