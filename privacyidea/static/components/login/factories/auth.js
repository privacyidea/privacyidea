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
angular.module("privacyideaAuth", [])
    .factory("AuthFactory", function () {
        /*
        Each service - just like this service factory - is a singleton.
        Here we just store the username of the authenticated user and his
        auth_token.
         */
        var user = {};

        return {
            setUser: function (username, realm, auth_token, role, rights) {
                user.username = username;
                user.realm = realm;
                user.auth_token = auth_token;
                user.role = role;
                user.rights = rights;
            },
            dropUser: function () {
                    user = {};
            },
            getUser: function () {
                return user;
            },
            getRealm: function () {
                return user.realm;
            },
            getAuthToken: function () {
                return user.auth_token;
            },
            getRole: function () {
                return user.role;
            },
            checkRight: function (action) {
                // check if the action is contained in user.rights
                var res = (user.rights.indexOf(action) >= 0);
                //console.log("checking right: " + action + ": " + res);
                return res;
            },
            checkEnroll: function() {
                // Check if any enroll* action is contained in user.rights
                var res = false;
                user.rights.forEach(function(entry){
                    // check if the action starts with "enroll"
                    if (entry.indexOf("enroll") === 0) {
                        res = true;
                    }
                });
                return res;
            }
        };
    });

//
// Taken from
// https://timesheets.altamiracorp.com/blog/employee-posts/simple-polling-service-in-angularjs
angular.module('privacyideaAuth')
    .factory('PollingAuthFactory', ['$http', 'authUrl', function($http,
                                                                 authUrl){
        var pollingTime = 1000;
        var polls = {};
        // We only need one poller
        var name = "authPoller";

        return {
            start: function(polling_func) {
                // Check to make sure poller doesn't already exist
                if (!polls[name]) {
                    polls[name] = setInterval(polling_func, pollingTime);
                }
            },

            stop: function() {
                clearInterval(polls[name]);
                delete polls[name];
            }
        };
    }]);
