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
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program. If not, see <http://www.gnu.org/licenses/>.
 *
 */
angular.module("privacyideaApp")
    .controller("mainController",
                            function (Idle,
                                      $scope, $http, $location,
                                      authUrl, AuthFactory, $rootScope,
                                      $state, ConfigFactory, inform,
                                      PolicyTemplateFactory, gettext, hotkeys,
                                      PollingAuthFactory) {

    hotkeys.add({
        combo: 'alt+e',
        description: gettext('Enroll a new token'),
        callback: function(event, hotkey) {
            event.preventDefault();
            $state.go('token.enroll');
        }
    });
    hotkeys.add({
        combo: 'alt+l',
        description: gettext("List tokens"),
        callback: function() {
            $state.go('token.list');
        }
    });
    hotkeys.add({
        combo: 'alt+q',
        description: gettext('Log out'),
        callback: function() {
            $scope.logout();
        }
    });
    $scope.myCountdown = "";
    // We save the previous State in the $rootScope, so that we
    // can return there
    $rootScope.$on('$stateChangeSuccess',
        function (ev, to, toParams, from, fromParams) {
            console.log("we changed the state from " + from + " to " + to);
            console.log(from);
            console.log(fromParams);
            $rootScope.previousState = {
                state: from.name,
                params: fromParams
            };
        });
    $scope.$on('IdleStart', function () {
        console.log("start idle");
    });

    $scope.$on('IdleWarn', function(e, countdown) {
        // follows after the IdleStart event, but includes a countdown
        // until the user is considered timed out
        // the countdown arg is the number of seconds remaining until then.
        // you can change the title or display a warning dialog from here.
        // you can let them resume their session by calling Idle.watch()
        $scope.myCountdown = countdown;
        console.log($scope.myCountdown);
        $scope.logoutWarning = true;
        $scope.$apply();
    });

    $scope.$on('IdleEnd', function () {
        console.log("The user has ended idling");
        $scope.logoutWarning = false;
    });

    $scope.$on('IdleTimeout', function () {
        console.log("Logout!");
        $scope.logout();
    });
    /*
     $rootScope.$on('Keepalive', function() {
        $scope.logoutWarning = false;
    });
    */

    // This holds the user object, the username, the password and the token.
    $scope.login = {username: "", password: ""};
    $scope.transactionid = "";
    AuthFactory.setUser();

    $scope.authenticate_first = function() {
        $scope.transactionid = "";
        $scope.authenticate();
    };

    $scope.authenticate = function () {
        $scope.polling = false;
        $scope.image = false;
        $http.post(authUrl, {
            username: $scope.login.username,
            password: $scope.login.password,
            transaction_id: $scope.transactionid
        }, {
            withCredentials: true
        }).success(function (data) {
            $scope.do_login_stuff(data);
        }).error(function (error) {
            console.log("challenge response");
            console.log(error);
            $scope.transactionid = "";
            $scope.login.password = "";
            // In case of error.detail.transaction_id is present, we
            // have a challenge response and we need to go to the state response
            if (error.detail['transaction_id']) {
                $state.go("response");
                inform.add(gettext("Challange Response Authentication. You" +
                    " are not completely authenticated, yet."),
                    {type: "warning", ttl:10000});
                $scope.challenge_message = error.detail.message;
                $scope.transactionid = error.detail["transaction_id"];
                $scope.image = error.detail.attributes.img;
                $scope.polling = error.detail.attributes.poll;
                console.log($scope.polling);
                $scope.login.password = "";
                // Now we need to start the poller
                PollingAuthFactory.start($scope.check_authentication);
            } else {
                inform.add(gettext("Authentication failed. ") + error.result.error.message,
                {type: "danger", ttl: 10000});
            }
        }).then(function () {
            // We delete the login object, so that the password is not
            // contained in the scope
            $scope.login = {username: "", password: ""};
            }
        );
    };
    $scope.check_authentication = function() {
        // This function is used to poll, if a challenge response
        // authentication was performed successfully in the background
        // This is used for the TiQR token.
        console.log("calling check_authentication.");
        $http.post(authUrl, {
            username: $scope.login.username,
            password: "",
            transaction_id: $scope.transactionid
        }, {
            withCredentials: true
        }).success(function (data) {
            $scope.do_login_stuff(data);
            PollingAuthFactory.stop();
        })
    };

    $scope.do_login_stuff = function(data) {
        AuthFactory.setUser(data.result.value.username,
                data.result.value.realm,
                data.result.value.token,
                data.result.value.role);
            $scope.privacyideaVersionNumber = data.versionnumber;
            $scope.loggedInUser = AuthFactory.getUser();
            timeout = data.result.value.logout_time;
            PolicyTemplateFactory.setUrl(data.result.value.policy_template_url);
            console.log(timeout);
            Idle.setIdle(timeout-10);
            Idle.watch();
            console.log("successfully authenticated");
            console.log($scope.loggedInUser);
            $location.path("/token");
            inform.add(gettext("privacyIDEA UI supports hotkeys. Use '?' to" +
                    " get help."), {type: "info", ttl: 10000});
            $scope.transactionid = "";
    };

    $scope.logout = function () {
        // logout: Clear the user and the auth_token.
        AuthFactory.dropUser();
        $scope.loggedInUser = {};
        $scope.privacyideaVersionNumber = null;
        $scope.logoutWarning = false;
        $scope.myCountdown = "";
        $state.go("login");
        Idle.unwatch();
    };

    $scope.about = function() {
        $('#dialogAbout').modal();
    };

    $rootScope.showError = false;
    $scope.errorOK = function () {
        // This will hide the error again
        $rootScope.showError = false;
    };

    $rootScope.showInfo = false;
    $scope.infoOK = function () {
        // This will hide the error again
        $rootScope.showInfo = false;
    };


    $scope.createDefaultRealm = function () {
        var resolver_params = {type: "passwdresolver", filename: "/etc/passwd"};
        var realm_params = {resolvers: "deflocal"};
        ConfigFactory.setResolver("deflocal",
            resolver_params,
            function(data) {
                if (data.result.value) {
                    // The resolver is created, we can create the realm
                    ConfigFactory.setRealm("defrealm",
                        realm_params, function (data) {
                            if (data.result.value) {
                                inform.add(gettext("Realm defrealm created."),
                                {type: "info"});

                            }
                        });
                }
        });

    }


});
