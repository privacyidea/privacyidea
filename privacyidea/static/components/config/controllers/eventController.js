/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2016-05-08 Cornelius Kölbel, <cornelius@privacyidea.org>
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
myApp.controller("eventController", ["$scope", "$stateParams", "$state",
    "$location", "ConfigFactory",
    function ($scope, $stateParams, $state,
              $location, ConfigFactory) {
        if ($location.path() === "/config/events") {
            $location.path("/config/events/list");
        }
        $('html,body').scrollTop(0);

        // define functions
        $scope.getEvents = function () {
            ConfigFactory.getEvents(function (data) {
                $scope.events = data.result.value;
                //debug: console.log("Fetched all events");
                //debug: console.log($scope.events);
            });
        };

        $scope.delEvent = function (eventid) {
            //debug: console.log("Deleting event " + eventid);
            ConfigFactory.delEvent(eventid, function (data) {
                //debug: console.log(data);
                $scope.getEvents();
                $state.go("config.events.list");
            });
        };

        $scope.enableEvent = function (eventid) {
            ConfigFactory.enableEvent(eventid, function () {
                $scope.getEvents();
            });
        };

        $scope.disableEvent = function (eventid) {
            ConfigFactory.disableEvent(eventid, function () {
                $scope.getEvents();
            });
        };

        $scope.orderChanged = function (event) {
            //debug: console.log(event);
            ConfigFactory.setEvent(event, function () {
                    $scope.getEvents();
                }
            );
        };

        // Get all events
        $scope.getEvents();

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getEvents);
    }]);

myApp.controller("eventDetailController", ["$scope", "$stateParams",
    "ConfigFactory", "$state", "ContainerFactory",
    function ($scope, $stateParams,
              ConfigFactory, $state, ContainerFactory) {
        // init
        $scope.form = {};
        $scope.eventid = $stateParams.eventid;
        $scope.availableEvents = Array();
        $scope.opts = {};
        $scope.conds = {};
        $scope.actionCheckBox = {};
        $scope.conditionCheckBox = {};
        $scope.condition_filter = "";
        $('html,body').scrollTop(0);

        $scope.getEvent = function () {
            ConfigFactory.getEvent($scope.eventid, function (event) {
                // get available positions for this module first, so we can set the select box
                $scope.form.handlermodule = event.result.value[0].handlermodule;
                $scope.getHandlerPositions();
                // Now fetch the action list
                ConfigFactory.getHandlerActions(event.result.value[0].handlermodule,
                    function (actions) {
                        $scope.handlerOptions = actions.result.value;
                        $scope.handlerActions = Object.keys($scope.handlerOptions);
                        $scope.form = event.result.value[0];
                        // tick the checked events
                        for (let i = 0; i < $scope.availableEvents.length; i++) {
                            const name = $scope.availableEvents[i].name;
                            if ($scope.form.event.indexOf(name) >= 0) {
                                $scope.availableEvents[i].ticked = true;
                            }
                        }
                        // set the options
                        $scope.actionChanged();
                        $scope.opts = event.result.value[0].options;
                        // set bool options, which are marked as "1" to true
                        angular.forEach($scope.opts, function (value, opt) {
                            // We need to check if $scope.form.action[opt]
                            // exist. Since if the handler was changed, there
                            // could be an option of another handler type, which
                            // is not available anymore.
                            if ($scope.handlerOptions[$scope.form.action][opt] &&
                                $scope.handlerOptions[$scope.form.action][opt].type === "bool" && isTrue(value)) {
                                $scope.opts[opt] = true;
                            }
                        });
                        // get the configured conditions
                        $scope.conds = event.result.value[0].conditions;
                        angular.forEach($scope.conds, function (value, cond) {
                            //debug: console.log("[Condition] " + cond + ": " + value);
                            $scope.conditionCheckBox[cond] = true;
                        });
                        // get the available conditions
                        $scope.getHandlerConditions();
                    });
            });
        };

        $scope.enableEvent = function (eventid) {
            ConfigFactory.enableEvent(eventid, function () {
                $scope.getEvent();
            });
        };

        $scope.disableEvent = function (eventid) {
            ConfigFactory.disableEvent(eventid, function () {
                $scope.getEvent();
            });
        };

        $scope.getAvailableEvents = function () {
            ConfigFactory.getEvent("available", function (data) {
                //debug: console.log("getting available events");
                const events = data.result.value;
                $scope.availableEvents = Array();
                angular.forEach(events, function (event) {
                    $scope.availableEvents.push({"name": event});
                });
                //debug: console.log($scope.availableEvents);
            });
        };

        $scope.getHandlerModules = function () {
            ConfigFactory.getEvent("handlermodules", function (data) {
                //debug: console.log("getting handlermodules");
                $scope.handlermodules = data.result.value;
                //debug: console.log($scope.handlermodules );
                if ($scope.eventid) {
                    $scope.getEvent();
                }
            });
        };

        $scope.createEvent = function () {
            // This is called to save the event handler
            $scope.form.id = $scope.eventid;
            let events = Array();
            // transform the event options to form parameters
            let handlerOptions = $scope.handlerOptions[$scope.form.action]
            for (let option in $scope.opts) {
                if (Object.hasOwn($scope.opts, option) && Object.hasOwn(handlerOptions, option)) {
                    $scope.form["option." + option] = $scope.opts[option];
                }
            }
            // Remove the preset "options" object from the form
            delete $scope.form.options
            // push all ticked events
            angular.forEach($scope.selectedEvents, function (event) {
                if (event.ticked === true) {
                    events.push(event.name);
                }
            });
            $scope.form.event = events.join(",");
            //debug: console.log("saving events " + $scope.form.event);
            // Add the activated conditions
            $scope.form.conditions = {};
            angular.forEach($scope.conditionCheckBox, function (activated, value) {
                if (activated === true) {
                    if (typeof $scope.conds[value] === "object") {
                        // push all ticked values
                        let multivalue = Array();
                        angular.forEach($scope.conds[value], function (mval) {
                            if (mval.ticked === true) {
                                multivalue.push(mval.name);
                            }
                        });
                        $scope.form.conditions[value] = multivalue.join(",");
                    } else {
                        $scope.form.conditions[value] = $scope.conds[value];
                    }
                }
            });
            ConfigFactory.setEvent($scope.form, function () {
                $state.go("config.events.list");
                $scope.reload();
            });
            $('html,body').scrollTop(0);
        };

        $scope.getHandlerActions = function () {
            //debug: console.log("getting handler actions for " + $scope.form.handlermodule);
            ConfigFactory.getHandlerActions($scope.form.handlermodule,
                function (actions) {
                    $scope.handlerOptions = actions.result.value;
                    $scope.handlerActions = Object.keys($scope.handlerOptions);
                    //debug: console.log($scope.handlerActions);
                    //debug: console.log($scope.form);
                });
        };

        $scope.getHandlerPositions = function () {
            ConfigFactory.getHandlerPositions($scope.form.handlermodule,
                function (positions) {
                    $scope.handlerPositions = positions.result.value;
                });
        };

        $scope.getHandlerConditions = function () {
            //debug: console.log("getting handler conditions for " + $scope.form.handlermodule);
            ConfigFactory.getHandlerConditions($scope.form.handlermodule,
                function (conditions) {
                    $scope.handlerConditions = conditions.result.value;
                    $scope.conditionGroups = [];
                    // Reset for open/close all groups if new handler is loaded
                    $scope.groupsOpen = 0;
                    $scope.groupIsOpen = {};

                    // tick selected handlerConditions, if type===multi
                    angular.forEach($scope.handlerConditions, function (condition, name) {
                        if (condition.type === "multi"
                            && Object.keys($scope.conds).indexOf(name) >= 0
                            && $scope.conds[name].length > 0) {
                            // multi value conditions are comma separated in one string
                            let tickedConditions = $scope.conds[name].split(',').map(cond => {
                                return cond.trim();
                            });
                            // Now we iterate over the given values and set them as `ticked`
                            angular.forEach(tickedConditions, function (cond) {
                                condition.value.find(x => x.name === cond).ticked = true;
                            });
                        }
                        if ($scope.conditionGroups.indexOf(condition.group) < 0) {
                            $scope.conditionGroups.push(condition.group)
                            $scope.groupIsOpen[condition.group] = false;
                        }
                    });
                });
        };

        $scope.openCloseAllGroups = function (open) {
            angular.forEach($scope.conditionGroups, function (group) {
                $scope.groupIsOpen[group] = open;
            });
        };

        $scope.groupsOpen = 0;
        $scope.$watch('groupIsOpen', function (newVal, oldVal) {
            if (newVal !== undefined && oldVal !== undefined) {
                angular.forEach(newVal, function (isOpen, group) {
                    if (newVal[group] != oldVal[group]) {
                        if (isOpen) {
                            $scope.groupsOpen++;
                        } else if ($scope.groupsOpen > 0) {
                            $scope.groupsOpen--;
                        }
                    }
                })
            }
        }, true);

        // test if the accordion group should be open or closed
        $scope.checkOpenConditionGroup = function (condition, conditionname, pattern) {
            let pat = escapeRegexp(pattern);
            let re = RegExp(pat, 'i');
            return ($scope.conditionCheckBox[conditionname] ||
                    !$scope.onlySelectedVisible) &&
                (re.test(conditionname) || re.test(condition.desc));
        };

        $scope.handlerModuleChanged = function () {
            $scope.getHandlerActions();
            $scope.getHandlerConditions();
            $scope.getHandlerPositions();
        };

        $scope.actionChanged = function () {
            $scope.options = $scope.handlerOptions[$scope.form.action];
            if ($scope.form.action == "set states") {
                $scope.container_set_states();
            }
        };

        $scope.getAvailableEvents();
        $scope.getHandlerModules();

        // Container - set_states: Handle excluded states
        $scope.container_set_states = function () {
            $scope.containerStates = {}
            ContainerFactory.getStateTypes(function (data) {
                $scope.containerStates = data.result.value;
            })
        }

        $scope.$watch('opts', function (newVal, oldVal) {
            if ($scope.form.action == "set states") {
                for (let [key, value] of Object.entries(newVal)) {
                    if (value && !oldVal[key]) {
                        $scope.excludeStates(key);
                    }
                }
            }
        }, true); // true = deep watch

        $scope.excludeStates = function (state) {
            // Deselect excluded states based on the selected state
            angular.forEach($scope.containerStates[state], function (disableType) {
                $scope.opts[disableType] = false
            })
        }
    }]);
