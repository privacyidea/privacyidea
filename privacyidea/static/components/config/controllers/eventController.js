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

    $scope.getEvent = function () {
        ConfigFactory.getEvent($scope.eventid, function(data) {
            console.log("Fetching single event " + $scope.eventid);
            $scope.form = data.result.value[0];
        });
    };

    $scope.createEvent = function () {
        // This is called to save the event handler
        $scope.form.id = $scope.eventid;
        if( typeof $scope.form.event  === 'string' ) {
        } else {
            $scope.form.event = $scope.form.event.join();
        }
        ConfigFactory.setEvent($scope.form, function(data) {
            $state.go("config.events.list");
        });
        $('html,body').scrollTop(0);
    };

    if ($scope.eventid) {
        $scope.getEvent();
    }

});
