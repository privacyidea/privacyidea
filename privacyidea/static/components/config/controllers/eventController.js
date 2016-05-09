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
myApp.controller("eventController", function($scope, $stateParams,
                                             $location, ConfigFactory) {
    if ($location.path() === "/config/events") {
        $location.path("/config/events/list");
    }

    // Get all events
    $scope.getEvents = function () {
        ConfigFactory.getEvents(function(data) {
            $scope.events = data.result.value;
            console.log("Fetched all events");
            console.log($scope.events);
        });
    };

    $scope.delEvent = function (eventid) {
        console.log("Deleting event " + eventid);
        ConfigFactory.delEvent(eventid, function(data) {
            console.log(data);
            $scope.getEvents();
        });
    };
    $scope.getEvents();
});

myApp.controller("eventDetailController", function($scope, $stateParams,
                                                    ConfigFactory, $state) {
    // init
    $scope.form = {};
    $scope.eventid = $stateParams.eventid;
    $scope.availableEvents = Array();
    $scope.opts = {};

    $scope.getEvent = function () {
        ConfigFactory.getEvent($scope.eventid, function(event) {
            console.log("Fetching single event " + $scope.eventid);
            // first we need to fetch the action-list:
            ConfigFactory.getHandlerActions(event.result.value[0].handlermodule,
                function(actions){
                    $scope.handlerOptions = actions.result.value;
                    $scope.handlerActions = Object.keys($scope.handlerOptions);
                    $scope.form = event.result.value[0];
                    for (var i=0; i<$scope.availableEvents.length; i++) {
                       var name = $scope.availableEvents[i].name;
                        if ($scope.form.event.indexOf(name) >= 0) {
                            $scope.availableEvents[i].ticked = true;
                        }
                    }
                    // set the options
                    $scope.actionChanged();
                    $scope.opts = event.result.value[0].options;
                });
        });
    };

    $scope.getAvailableEvents = function () {
        ConfigFactory.getEvent("available", function(data) {
            console.log("getting available events");
            var events = data.result.value;
            $scope.availableEvents = Array();
            angular.forEach(events, function(event) {
                $scope.availableEvents.push({"name": event})
            });
            console.log($scope.availableEvents);
        });
    };

    $scope.getHandlerModules = function () {
        ConfigFactory.getEvent("handlermodules", function(data) {
            console.log("getting handlermodules");
            $scope.handlermodules = data.result.value;
            console.log($scope.handlermodules );
        });
    };

    $scope.createEvent = function () {
        // This is called to save the event handler
        $scope.form.id = $scope.eventid;
        var events = Array();
        // transform the event options to form parameters
        for (var option in $scope.opts) {
            if ($scope.opts.hasOwnProperty(option)) {
                $scope.form["option." + option] = $scope.opts[option];
            }
        }
        // push all ticked events
        angular.forEach($scope.selectedEvents, function(event){
            if (event.ticked === true) {
                events.push(event.name);
            }
        });
        $scope.form.event = events.join(",");
        console.log("saving events " + $scope.form.event);
        ConfigFactory.setEvent($scope.form, function() {
            $state.go("config.events.list");
        });
        $('html,body').scrollTop(0);
    };

    $scope.getHandlerActions = function () {
        console.log("getting handler actions for " + $scope.form.handlermodule);
        ConfigFactory.getHandlerActions($scope.form.handlermodule,
            function(actions){
                $scope.handlerOptions = actions.result.value;
                $scope.handlerActions = Object.keys($scope.handlerOptions);
                console.log($scope.handlerActions);
                console.log($scope.form);
            });
    };

    $scope.actionChanged = function () {
        $scope.options = $scope.handlerOptions[$scope.form.action];
    };

    $scope.getAvailableEvents();
    $scope.getHandlerModules();
    if ($scope.eventid) {
        $scope.getEvent();
    }

});
