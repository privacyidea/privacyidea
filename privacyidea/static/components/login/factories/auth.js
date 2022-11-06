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
angular.module("privacyideaAuth", ['privacyideaApp.errorMessage'])
    .factory("AuthFactory", ["inform", "gettextCatalog", "$state",
                             function (inform, gettextCatalog, $state) {
        /*
        Each service - just like this service factory - is a singleton.
        Here we just store the username of the authenticated user and his
        auth_token.
         */
        var user = {};

        return {
            setUser: function (username, realm, auth_token, role, rights, menus) {
                user.username = username;
                user.realm = realm;
                user.auth_token = auth_token;
                user.role = role;
                user.rights = rights;
                user.menus = menus;
            },
            authError: function(error) {
                var authErrorCodes = Array(403, 4031, 4032, 4033, 4034, 4035, 4036);
                if (error === null) {
                    console.warn('No error object available, maybe the request was aborted?')
                    return
                }
                if (typeof (error) === "string") {
                    inform.add(gettextCatalog.getString("Failed to get a valid JSON response from the privacyIDEA server."),
                        {type: "danger", ttl: 10000});
                } else {
                    inform.add(error.result.error.message, {type: "danger", ttl: 10000});
                    if (authErrorCodes.indexOf(error.result.error.code) >= 0) {
                        if ($state.current.controller === "registerController" ) {
                            $state.go('register');
                        } else if ($state.current.controller === "recoveryController") {
                            $state.go('recovery');
                        } else {
                            $state.go('login');
                        }
                    }
                }
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
                if (user.rights) {
                    // check if the action is contained in user.rights
                    var res = (user.rights.indexOf(action) >= 0);
                    ////debug: console.log("checking right: " + action + ": " + res);
                    return res;
                }
            },
            getRightsValue: function (action, defaultValue=false) {
                // return the value of an action like otp_pin_minlength
                var res = defaultValue;
                if (user.rights) {
                    user.rights.forEach(function (entry) {
                        if (entry.indexOf("=") >= 0) {
                            // this is a value action
                            var components = entry.split("=");
                            if (components[0] === action) {
                                res = components[1];
                            }
                        }
                    });
                }
                return res;
            },
            checkMainMenu: function (menu) {
                var res = (user.menus.indexOf(menu) >= 0);
                return res;
            },
            checkEnroll: function() {
                // Check if any enroll* action is contained in user.rights
                var res = false;
                if (user.rights) {
                    user.rights.forEach(function(entry){
                        // check if the action starts with "enroll"
                        if (entry.indexOf("enroll") === 0) {
                            res = true;
                        }
                    });
                }
                return res;
            }
        };
    }]);

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
