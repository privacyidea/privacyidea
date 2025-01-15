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
myApp.directive('tokenDataEdit', ["AuthFactory", "instanceUrl", "versioningSuffixProvider", function (AuthFactory, instanceUrl, versioningSuffixProvider) {
    return {
        scope: {
            text: '@',
            buttonText: '@',
            tokenData: '@',
            tokenLocked: '@',
            tokenKey: '@',
            hideButtons: '@',
            setRight: '@',
            inputPattern: '@',
            inputType: '@',
            editableAsUser: '@',
            callback: '&',
            callbackCancel: '&'
        },
        templateUrl: instanceUrl + "/static/components/directives/views/directive.tokendata.html" + versioningSuffixProvider.$get(),
        link: function (scope, element, attr, ctrl) {
            scope.loggedInUser = AuthFactory.getUser();
            //debug: console.log("tokenDataEdit");
            //debug: console.log(scope.loggedInUser);
        }
    };
}]);

myApp.directive("piFilter", ["instanceUrl", "versioningSuffixProvider", function (instanceUrl, versioningSuffixProvider) {
    return {
        require: 'ngModel',
        restrict: 'E',
        scope: {},
        templateUrl: instanceUrl + "/static/components/directives/views/directive.filter.table.html" + versioningSuffixProvider.$get(),
        link: function (scope, element, attr, ctrl) {
            scope.updateFilter = function () {
                ctrl.$setViewValue(scope.filterValue);
            };
            ctrl.$viewChangeListeners.push(function () {
                scope.$eval(attr.ngChange);
            });
        }
    };
}]);

myApp.directive('focusMe', ["$timeout", function ($timeout) {
    return {
        link: function (scope, element, attrs) {
            scope.$watch(attrs.focusMe, function (value) {
                if (value === true) {
                    $timeout(function () {
                        element[0].focus();
                        scope[attrs.focusMe] = false;
                    });
                }
            });
        }
    };
}]);

myApp.directive("piSortBy", function () {
    return {
        restrict: 'A', link: function (scope, element, attr) {
            element.on('click', function () {
                var column = attr.piSortBy;
                scope.sortby = column;
                scope.reverse = !scope.reverse;
                $(".sortUp").addClass("unsorted");
                $(".sortDown").addClass("unsorted");
                $(".sortUp").removeClass("sortUp");
                $(".sortDown").removeClass("sortDown");
                element.removeClass("unsorted");
                if (scope.reverse) {
                    element.addClass("sortDown");
                } else {
                    element.addClass("sortUp");
                }

                // scope.get() is what we call, when sorting is done on the server. For client-side sorting $apply() is
                // used to rerender the list with the new sorting.
                scope.get ? scope.get() : scope.$apply();
            });
        }
    };
});

myApp.directive('assignUser', ["$http", "$rootScope", "userUrl", "AuthFactory", "instanceUrl", "versioningSuffixProvider", function ($http, $rootScope, userUrl, AuthFactory, instanceUrl, versioningSuffixProvider) {
    /*
    This directive is used to select a user from a realm

    newUserObject consists of .user and .realm
     */
    return {
        scope: {
            newUserObject: '=',
            realms: '=',
            enableSetPin: '='
        },
        templateUrl: instanceUrl + "/static/components/directives/views/directive.assignuser.html" + versioningSuffixProvider.$get(),
        link: function (scope, element, attr) {
            //console.log("Entering assignUser directive");
            //console.log(scope.realms);
            // If the user is not set, set the default realm selection to the first realm in the list
            scope.$watch('realms', function (newVal, oldVal) {
                if (newVal && !scope.newUserObject.user) {
                    scope.newUserObject.realm = Object.keys(newVal)[0];
                }
            }, true);

            //console.log(scope.newUserObject);
            // toggle enable/disable loadUsers calls
            scope.toggleLoadUsers = function ($toggle) {
                // only trigger if the search_on_enter policy is active
                if ($rootScope.search_on_enter) {
                    const $viewValue = scope.newUserObject.user;
                    scope.newUserObject.toggle = $toggle;
                    // update field value with a placeholder to trigger typeahead
                    if (scope.newUserObject.toggle && $viewValue.charAt($viewValue.length - 1) != "*") {
                        const ctrl = element.find('input').controller('ngModel');
                        ctrl.$setViewValue($viewValue + "*");
                    }
                }
            };

            scope.loadUsers = function ($viewValue) {
                if ($rootScope.search_on_enter && (!$viewValue || $viewValue == "*" || !scope.newUserObject.toggle)) {
                    // only use existing result if any, and if search_on_enter policy is active
                    return scope.newUserObject.loadedUsers;
                }
                const auth_token = AuthFactory.getAuthToken();
                return $http({
                    method: 'GET',
                    url: userUrl + "/?username=*" + $viewValue + "*" + "&realm=" + scope.newUserObject.realm,
                    headers: {'PI-Authorization': auth_token}
                }).then(function ($response) {
                    scope.newUserObject.loadedUsers = $response.data.result.value.map(function (item) {
                        scope.newUserObject.email = item.email;
                        scope.newUserObject.mobile = item.mobile;
                        scope.newUserObject.phone = item.phone;
                        return "[" + item.userid + "] " + item.username + " (" + item.givenname + " " + item.surname + ")";
                    });
                    return scope.newUserObject.loadedUsers;
                });
            };
        }
    };
}]);

myApp.directive('assignToken', ["$http", "$rootScope", "tokenUrl", "AuthFactory", "instanceUrl", "versioningSuffixProvider", function ($http, $rootScope, tokenUrl, AuthFactory, instanceUrl, versioningSuffixProvider) {
    /*
    This directive is used to select a serial number and assign it
    to the user.

    newTokenObject consists of .serial and .pin
     */
    return {
        scope: {
            newTokenObject: '='
        },
        templateUrl: instanceUrl + "/static/components/directives/views/directive.assigntoken.html" + versioningSuffixProvider.$get(),
        link: function (scope, element, attr) {
            // Toggle enable/disable loadSerials call
            scope.toggleLoadSerials = function ($toggle) {
                // only trigger if the search_on_enter policy is active
                if ($rootScope.search_on_enter) {
                    const $viewValue = scope.newTokenObject.serial;
                    scope.newTokenObject.toggle = $toggle;
                    // update field value with a placeholder to trigger typeahead
                    if (scope.newTokenObject.toggle && $viewValue.charAt($viewValue.length - 1) != "*") {
                        const ctrl = element.find('input').controller('ngModel');
                        ctrl.$setViewValue($viewValue + "*");
                    }
                }
            };
            scope.loadSerials = function ($viewValue) {
                if ($rootScope.search_on_enter && (!$viewValue || $viewValue == "*" || !scope.newTokenObject.toggle)) {
                    // only use existing result if any, and if search_on_enter policy is active
                    return scope.newTokenObject.loadedSerials;
                }
                const auth_token = AuthFactory.getAuthToken();
                return $http({
                    method: 'GET', url: tokenUrl + "/", headers: {'PI-Authorization': auth_token}, params: {
                        assigned: "False", serial: "*" + $viewValue + "*"
                    }
                }).then(function ($response) {
                    scope.newTokenObject.loadedSerials = $response.data.result.value.tokens.map(function (item) {
                        let serialString = item.serial + " (" + item.tokentype + ") "
                        if (item.description) {
                            serialString += "[" + item.description + "] "
                        }
                        return serialString;
                    });
                    return scope.newTokenObject.loadedSerials;
                });
            };
        }
    };
}]);

myApp.directive('attachToken', ["$http", "tokenUrl", "AuthFactory", "instanceUrl", "versioningSuffixProvider", function ($http, tokenUrl, AuthFactory, instanceUrl, versioningSuffixProvider) {
    /*
    This directive is used to select a serial number and attach it to a machine

    newTokenObject consists of .serial
     */
    return {
        scope: {
            newTokenObject: '='
        },
        templateUrl: instanceUrl + "/static/components/directives/views/directive.attachtoken.html" + versioningSuffixProvider.$get(),
        link: function (scope, element, attr) {
            scope.loadSerials = function ($viewValue) {
                const auth_token = AuthFactory.getAuthToken();
                return $http({
                    method: 'GET',
                    url: tokenUrl + "/",
                    headers: {'PI-Authorization': auth_token},
                    params: {serial: "*" + $viewValue + "*"}
                }).then(function ($response) {
                    return $response.data.result.value.tokens.map(function (item) {
                        let serialString = item.serial + " (" + item.tokentype + ") "
                        if (item.username) {
                            serialString += "[" + item.username + "@" + item.realms + "] "
                        }
                        if (item.description) {
                            serialString += "[" + item.description + "] "
                        }
                        return serialString;
                    });
                });
            };
        }
    };
}]);

myApp.directive('attachMachine', ["$http", "machineUrl", "AuthFactory", "instanceUrl", "versioningSuffixProvider", function ($http, machineUrl, AuthFactory, instanceUrl, versioningSuffixProvider) {
    /*
    This directive is used to select a machine.
     */
    return {
        scope: {
            newMachine: '='
        },
        templateUrl: instanceUrl + "/static/components/directives/views/directive.attachmachine.html" + versioningSuffixProvider.$get(),
        link: function (scope, element, attr) {
            scope.loadMachines = function ($viewValue) {
                var auth_token = AuthFactory.getAuthToken();
                return $http({
                    method: 'GET',
                    url: machineUrl + "/",
                    headers: {'PI-Authorization': auth_token},
                    params: {any: $viewValue}
                }).then(function ($response) {
                    //debug: console.log($response.data.result.value);
                    return $response.data.result.value.map(function (item) {
                        return item.hostname + " [" + item.ip + "] (" + item.id + " in " + item.resolver_name + ")";
                    });
                });
            };
        }
    };
}]);

myApp.directive('equals', function () {
    return {
        restrict: 'A', // only activate on element attribute
        require: '?ngModel', // get a hold of NgModelController
        link: function (scope, elem, attrs, ngModel) {
            const validate = function () {
                // values
                const val1 = ngModel.$viewValue || "";
                const val2 = attrs.equals || "";

                // set validity
                ngModel.$setValidity('equals', val1 === val2);
            };
            if (!ngModel) { // do nothing if no ng-model
                return;
            }

            // watch own value and re-validate on change
            scope.$watch(attrs.ngModel, function () {
                validate();
            });

            // observe the other value and re-validate on change
            attrs.$observe('equals', function (val) {
                validate();
            });

        }
    };
});

myApp.directive('statusClass', function () {
    return {
        link: function (scope, element, attrs, ngModel) {
            if (["ACCEPT", "OK", "1", 1].indexOf(attrs.statusClass) > -1) {
                element.addClass("label label-success");
                element.removeClass("label-danger");
            } else {
                element.addClass("label label-danger");
                element.removeClass("label-success");
            }
        }
    };
});

// See http://blog.techdev.de/an-angularjs-directive-to-download-pdf-files/
myApp.directive('csvDownload', ["AuthFactory", "$http", "instanceUrl", "versioningSuffixProvider", function (AuthFactory, $http, instanceUrl, versioningSuffixProvider) {
    return {
        restrict: 'E',
        templateUrl: instanceUrl + "/static/components/directives/views/directive.csvdownload.html" + versioningSuffixProvider.$get(),
        scope: true,
        link: function (scope, element, attr) {
            const anchor = element.children()[0];

            // When the download starts, disable the link
            scope.$on('download-start', function () {
                $(anchor).attr('disabled', 'disabled')
                    .text('Please Wait! Crunching data...');
                scope.downloadProgress = true;
            });

            // When the download finishes, attach the data to the link. Enable the link and change its appearance.
            scope.$on('downloaded', function (event, data) {
                $(anchor).attr({
                    href: 'data:text/csv;utf-8,' + encodeURI(data), download: attr.filename
                })
                    .removeAttr('disabled')
                    .text('Save')
                    .removeClass('btn-primary')
                    .addClass('btn-success');
                scope.downloadProgress = false;
                // Also overwrite the download pdf function to do nothing.
                scope.downloadCSV = function () {
                };
            });
        },
        controller: ['$scope', '$attrs', '$http', function ($scope, $attrs, $http) {
            $scope.downloadCSV = function () {
                $scope.$emit('download-start');
                //debug: console.log("Download start.");
                $scope.getParams();
                $http.get($attrs.url, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}, params: $scope.params
                }).then(function (response) {
                    //debug: console.log("Downloaded.");
                    $scope.$emit('downloaded', response.data);
                });
            };
        }]
    }
}]);

myApp.directive('spinner', function () {
    return {
        scope: {
            name: '@?', register: '=?'
        },
        template: ['<div ng-show="showSpinner">', '<span class="glyphicon glyphicon-refresh spin" aria-hidden="true"></span>', '</div>'].join(''),
        controller: function ($scope, $rootScope) {
            $scope.loading_queue = 0;
            $scope.$watch('loading_queue', function (loading_queue) {
                if (loading_queue > 0) {
                    $scope.showSpinner = true;
                    $rootScope.showReload = false;
                } else if (loading_queue < 0) {
                    $scope.loading_queue = 0;
                } else {
                    $scope.showSpinner = false;
                    $rootScope.showReload = true;
                }
            });
            $scope.$on('spinnerEvent', function (event, data) {
                if (data.action === 'increment') {
                    $scope.loading_queue++;
                } else if (data.action === 'decrement') {
                    $scope.loading_queue--;
                }
            });
        }
    };
});

myApp.directive('autofocus', ['$timeout', function ($timeout) {
    return {
        restrict: 'A', link: function ($scope, $element) {
            $timeout(function () {
                $element[0].focus();
            });
        }
    };
}]);

myApp.directive("piPolicyConditions", ["instanceUrl", "versioningSuffixProvider", function (instanceUrl, versioningSuffixProvider) {
    /* This directive is used to set the conditions of a policy.
       It supports adding, removing and editing conditions. */
    return {
        restrict: 'E',
        scope: {
            // We need a bidirectional binding because we modify the conditions.
            // The conditions are a list of 5-element lists.
            policyConditions: "=conditions", // We only need a one-directional binding, because we will never change the definitions
            conditionDefs: "=defs"
        },
        templateUrl: instanceUrl + "/static/components/directives/views/directive.policyconditions.html" + versioningSuffixProvider.$get(),
        link: function (scope, element, attr, ctrl) {
            // The index of the condition that is currently being edited,
            // or -1 if no condition is currently being edited
            scope.editIndex = -1;

            // Called when the user clicks on the "edit" button of a condition
            scope.editCondition = function (idx) {
                if (scope.editIndex == idx) {
                    // we are editing this condition right now, toggle editing
                    scope.editIndex = -1;
                } else {
                    scope.editIndex = idx;
                }
            };

            // Called when the user clicks on the "delete" button of a condition
            scope.deleteCondition = function (idx) {
                scope.policyConditions.splice(idx, 1);
                scope.editIndex = -1;
            };

            // Called when the user clicks on the "add condition" button.
            // Adds a condition with default values
            scope.addCondition = function () {
                scope.policyConditions.push(["userinfo", "", "equals", "", false]);
                scope.editIndex = scope.policyConditions.length - 1;
            };
        },
    };
}]);

myApp.directive("selectOrCreateContainer", ["instanceUrl", "versioningSuffixProvider", "ContainerFactory", "$http",
    "containerUrl", "AuthFactory",
    function (instanceUrl, versioningSuffixProvider, ContainerFactory, $http, containerUrl, AuthFactory) {
        return {
            scope: {
                // The selected serial of the container
                containerSerial: "=",
                // Set to true to disable the container selection.
                disableSelection: "=",
                // Set to true to show a checkbox that allows to assign the container to a user directly. Is only
                // visible if userObject is also set.
                enableUserAssignment: "=",
                // If set to true, the user assignment will be checked by default
                checkUserAssignment: "=",
                userName: "=",
                userRealm: "=",
                // Array of tokentypes that will be going in the container to select. Settings this changes the selection based
                // on what tokentypes each containertype can support
                tokenTypes: "="
            },
            templateUrl: instanceUrl + "/static/components/directives/views/directive.selectorcreatecontainer.html" + versioningSuffixProvider.$get(),
            link: function (scope, element, attr) {
                // Showing the user assignment checkbox is not only dependent on the enableUserAssignment flag, but also
                // on the user assignment rights and the userName being set.
                scope.showUserAssignment = scope.enableUserAssignment && AuthFactory.checkRight("container_assign_user") && scope.userName;
                // If showUserAssignment is false, the user assignment will be disabled
                scope.assignUserToContainer = scope.checkUserAssignment;

                scope.$watch("userName", function (newVal, oldVal) {
                    if (newVal) {
                        scope.showUserAssignment = scope.enableUserAssignment && AuthFactory.checkRight("container_assign_user");
                    } else {
                        scope.showUserAssignment = false;
                    }
                });

                scope.newContainer = {
                    type: "generic", types: "", token_types: "", description: "",
                }

                let allContainerTypes = {};
                let containerList = {};
                // Get the supported token types for each container type once
                ContainerFactory.getTokenTypes(function (data) {
                    allContainerTypes = data.result.value;

                    angular.forEach(allContainerTypes, function (_, containerType) {
                        if (containerType === 'generic') {
                            allContainerTypes[containerType]["token_types_display"] = 'All';
                        } else {
                            allContainerTypes[containerType]["token_types_display"] = scope.tokenTypesToDisplayString(
                                allContainerTypes[containerType].token_types);
                        }
                    });
                    if (allContainerTypes[scope.newContainer.type]) {
                        scope.newContainer.token_types = allContainerTypes[scope.newContainer.type]["token_types_display"];
                    }

                    scope.getContainers();
                });

                // converts the supported token types to a display string
                scope.tokenTypesToDisplayString = function (containerTokenTypes) {
                    let displayString = "";
                    // create comma separated list out of token names
                    angular.forEach(containerTokenTypes, function (type) {
                        displayString += type.charAt(0).toUpperCase() + type.slice(1) + ", ";
                    });
                    displayString = displayString.slice(0, -2);

                    return displayString;
                };

                scope.getContainers = function () {
                    if (AuthFactory.checkRight("container_list")) {
                        $http.get(containerUrl + "/?no_token=1", {
                            headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                        }).then(function (response) {
                            containerList = response.data.result.value.containers;
                            scope.setContainerSelection(containerList);
                            scope.setDefaultSerialSelection();
                            scope.newContainer.types = scope.getContainerTypesForTokenType();
                        }, function (error) {
                            AuthFactory.authError(error.data);
                        });
                    }
                };

                scope.getContainerTypesForTokenType = function () {
                    let usableContainerTypes = {};
                    let includesAll = (arr, target) => target.every(element => arr.includes(element));
                    if (allContainerTypes !== undefined) {
                        if (scope.tokenTypes && Array.isArray(scope.tokenTypes) && scope.tokenTypes.length > 0) {
                            Object.keys(allContainerTypes).forEach(function (ctype) {
                                if (includesAll(allContainerTypes[ctype]["token_types"], scope.tokenTypes)) {
                                    usableContainerTypes[ctype] = allContainerTypes[ctype];
                                }
                            });
                        } else {
                            // No tokenType selected, show all container types
                            usableContainerTypes = allContainerTypes;
                        }
                    }
                    return usableContainerTypes;
                };

                // containerList is data.result.value of GET /container
                scope.setContainerSelection = function () {
                    const usableContainerTypes = scope.getContainerTypesForTokenType();
                    scope.containers = [];
                    // Filter the containers
                    if (scope.tokenTypes && usableContainerTypes) {
                        for (let i = 0; i < containerList.length; i++) {
                            if (containerList[i].type in usableContainerTypes) {
                                scope.containers.push(containerList[i]);
                            }
                        }
                    } else {
                        scope.containers = containerList;
                    }

                    // Add a display string to the containers
                    if (scope.containers && scope.containers.length > 0) {
                        scope.containers.forEach(function (container) {
                            container.displayString = "[" + container.type + "] " + container.serial;
                            if (container.users.length > 0) {
                                container.displayString += " of " + container.users[0].user_name + "@" + container.users[0].user_realm;
                            }
                            if (container.description) {
                                container.displayString += " (" + container.description + ")";
                            }
                        });
                    }
                    if (AuthFactory.checkRight("container_create")) {
                        // Always add an extra container at the beginning to represent the creation of a new container
                        scope.containers.unshift({displayString: "Create new container", serial: "createnew"});
                    }
                    // Placeholder for no container selected
                    scope.containers.unshift({displayString: "No Container", serial: "none"});
                }

                scope.setDefaultSerialSelection = function () {
                    if (!scope.containerSerial) {
                        scope.containerSerial = "none";
                    }
                }

                // Set the default to creating a new container/the first container if there is containerSerial set from outer scope
                scope.setDefaultSerialSelection();

                scope.$watch('tokenTypes', function (newVal, oldVal) {
                    if (newVal) {
                        scope.setContainerSelection();
                        scope.newContainer.types = scope.getContainerTypesForTokenType();
                    }
                });

                // Watch for changes in these variables so that can not be null/undefined. They might be set to null if
                // the tokentypes change and therefore the selection changes. In that case, reset to createnew.
                scope.$watch('newContainer.type', function (newVal, oldVal) {
                    //console.log("newContainer.type changed from " + oldVal + " to " + newVal);
                    if (newVal === undefined || newVal === null) {
                        scope.newContainer.type = "generic"
                    }
                    if (allContainerTypes[scope.newContainer.type] !== undefined) {
                        scope.newContainer.token_types = allContainerTypes[scope.newContainer.type]["token_types_display"];
                    }
                });
                scope.$watch('containerSerial', function (newVal, oldVal) {
                    //console.log("selectOrCreateDirective: containerSerial changed from " + oldVal + " to " + newVal);
                    // setDefaultSerialSelection check for rights to create_container, so in case newVal is "createnew",
                    // double check that because it can be set from outside
                    if (newVal === undefined || newVal === null) {
                        scope.setDefaultSerialSelection();
                    }
                });

                scope.createContainer = function () {
                    let params = {
                        type: scope.newContainer.type, description: scope.newContainer.description,
                    }
                    if (scope.assignUserToContainer && scope.userName && scope.userRealm) {
                        params["user"] = fixUser(scope.userName);
                        params["realm"] = scope.userRealm;
                    }
                    $http.post(containerUrl + "/init", params, {
                        headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    }).then(function (response) {
                        const newSerial = response.data.result.value.container_serial;
                        scope.getContainers();
                        scope.containerSerial = newSerial;
                        scope.newContainer.description = "";
                        if (scope.assignUserToContainer && scope.userName && scope.userRealm) {
                            params["user"] = fixUser(scope.userName);
                            params["realm"] = scope.userRealm;
                        }
                    }, function (error) {
                        AuthFactory.authError(error.data);
                    });
                }
            }
        };
    }]);


myApp.directive("selectResolver", ["instanceUrl", "versioningSuffixProvider", "$http",
    function (instanceUrl, versioningSuffixProvider, $http) {
        return {
            scope: {
                selectedResolvers: "=",
                resolvers: "="
            },
            templateUrl: instanceUrl + "/static/components/directives/views/directive.selectresolver.html" + versioningSuffixProvider.$get(),
            link: function (scope, element, attr) {

                scope.selectionChanged = function (newSelection) {
                    scope.selectedResolvers = newSelection;
                };

            }
        };
    }]);
