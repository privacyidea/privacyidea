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

//Return an empty array if string is empty.
//Otherwise return the result of the ordinary split.
String.prototype.mysplit = function(separator) {
    return this == "" ? [] : this.split(separator);
};


angular.module("privacyideaApp")
    .controller("mainController",
                            function (Idle,
                                      $scope, $http, $location,
                                      authUrl, AuthFactory, $rootScope,
                                      $state, ConfigFactory, inform,
                                      PolicyTemplateFactory, gettextCatalog,
                                      hotkeys, RegisterFactory,
                                      U2fFactory, instanceUrl,
                                      PollingAuthFactory) {

    $scope.instanceUrl = instanceUrl;
    $scope.checkRight = AuthFactory.checkRight;
    $scope.getRightsValue = AuthFactory.getRightsValue;
    $scope.checkMainMenu = AuthFactory.checkMainMenu;
    $scope.checkEnroll = AuthFactory.checkEnroll;
    var obj = angular.element(document.querySelector("#REMOTE_USER"));
    $scope.remoteUser = obj.val();
    if (!$scope.remoteUser) {
        $scope.loginWithCredentials = true;
    }
    obj = angular.element(document.querySelector("#PASSWORD_RESET"));
    $scope.passwordReset = obj.val();
    obj = angular.element(document.querySelector("#HSM_READY"));
    $scope.hsmReady = obj.val();
    obj = angular.element(document.querySelector("#CUSTOMIZATION"));
    $scope.piCustomization = obj.val();
    obj = angular.element(document.querySelector("#EXTERNAL_LINKS"));
    $scope.piExternalLinks = obj.val();
    obj = angular.element(document.querySelector('#REALMS'));
    $scope.piRealms = obj.val().mysplit(",").sort();
    //debug: console.log($scope.piRealms);
    obj = angular.element(document.querySelector('#LOGO'));
    $scope.piLogo = obj.val();
    obj = angular.element(document.querySelector('#HAS_JOB_QUEUE'));
    $scope.hasJobQueue = obj.val() == "True";
    obj = angular.element(document.querySelector('#LOGIN_TEXT'));
    $scope.piLoginText= obj.val();
    // Check if registration is allowed
    $scope.registrationAllowed = false;
    RegisterFactory.status(function (data) {
        $scope.registrationAllowed = data.result.value;
    });
    $scope.welcomeStep = 0;

    // customization
    $scope.piCustomMenuFile = angular.element(document.querySelector('#CUSTOM_MENU')).val();
    $scope.piCustomBaselineFile = angular.element(document.querySelector('#CUSTOM_BASELINE')).val();
    // TODO: We can change this after login, if there is a user dependent customization!

    hotkeys.add({
        combo: 'alt+e',
        description: gettextCatalog.getString('Enroll a new token'),
        callback: function(event, hotkey) {
            event.preventDefault();
            $state.go('token.enroll');
        }
    });
    hotkeys.add({
        combo: 'alt+l',
        description: gettextCatalog.getString("List tokens"),
        callback: function() {
            $state.go('token.list');
        }
    });
    hotkeys.add({
        combo: 'alt+q',
        description: gettextCatalog.getString('Log out'),
        callback: function() {
            $scope.logout();
        }
    });
    $scope.myCountdown = "";
    // We save the previous State in the $rootScope, so that we
    // can return there
    $rootScope.$on('$stateChangeSuccess',
        function (ev, to, toParams, from, fromParams) {
            //debug: console.log("we changed the state from " + from + " to " + to);
            //debug: console.log(from);
            //debug: console.log(fromParams);
            //debug: console.log(to);
            $rootScope.previousState = {
                state: from.name,
                params: fromParams
            };

            $scope.checkReloadListeners();
        });
    $scope.$on('IdleStart', function () {
        //debug: console.log("start idle");
    });

    $scope.$on('IdleWarn', function(e, countdown) {
        // follows after the IdleStart event, but includes a countdown
        // until the user is considered timed out
        // the countdown arg is the number of seconds remaining until then.
        // you can change the title or display a warning dialog from here.
        // you can let them resume their session by calling Idle.watch()
        $scope.myCountdown = countdown;
        //debug: console.log($scope.myCountdown);
        $scope.logoutWarning = true;
        $scope.$apply();
    });

    $scope.$on('IdleEnd', function () {
        //debug: console.log("The user has ended idling");
        $scope.logoutWarning = false;
    });

    $scope.$on('IdleTimeout', function () {
        if ($scope.timeout_action == "logout") {
            //debug: console.log("Logout!");
            $scope.logout();
        } else {
            //debug: console.log("Lock!");
            $scope.logoutWarning = false;
            $scope.$apply();
            $scope.lock_screen();
        }
    });
    /*
     $rootScope.$on('Keepalive', function() {
        $scope.logoutWarning = false;
    });
    */

    // helper function
    $scope.isChecked = function (val) {
        // check if val is set
        return [true, 1, '1', 'True', 'true', 'TRUE'].indexOf(val) > -1;
    };

    // This holds the user object, the username, the password and the token.
    // If we have a REMOTE_USER, we preset it.
    $scope.login = {username: $scope.remoteUser,
        password: "",
        realm: ""};
    $scope.transactionid = "";
    AuthFactory.setUser();

    $scope.unlock_first = function () {
        $scope.transactionid = "";
        $scope.unlocking = true;
        $scope.login.username = $scope.loggedInUser.username;
        $scope.login.realm = $scope.loggedInUser.realm;
        $scope.authenticate();
    };

    $scope.authenticate_first = function() {
        $scope.transactionid = "";
        $scope.unlocking = false;
        $scope.authenticate();
    };

    $scope.authenticate_remote_user = function () {
        $scope.login = {username: $scope.remoteUser, password: ""};
        $scope.unlocking = false;
        $scope.authenticate();
    };

    $scope.authenticate = function () {
        $scope.polling = false;
        $scope.image = false;
        //debug: console.log($scope.login);
        $http.post(authUrl, {
            username: $scope.login.username,
            password: $scope.login.password,
            realm: $scope.login.realm,
            transaction_id: $scope.transactionid
        }, {
            withCredentials: true
        }).success(function (data) {
            $scope.do_login_stuff(data);
        }).error(function (error) {
            //debug: console.log("challenge response");
            //debug: console.log(error);
            $scope.login.password = "";
            if (error.detail && error.detail.transaction_id) {
                // In case of error.detail.transaction_id is present, we
                // have a challenge response and we need to go to the state response
                if ($scope.unlocking === false) {
                    // If we are not unlocking, then we do a "login".
                    // For this we go to the response-state.
                    $state.go("response");
                }
                inform.add(gettextCatalog.getString("Challenge Response " +
                    "Authentication. You" +
                    " are not completely authenticated, yet."),
                    {type: "warning", ttl:5000});
                $scope.hideResponseInput = true;
                $scope.u2fSignRequests = Array();
                $scope.transactionid = error.detail["transaction_id"];

                // Challenge Response always containes mult_challenge!
                var multi_challenge = error.detail.multi_challenge;
                if (multi_challenge.length > 1) {
                    $scope.challenge_message = gettextCatalog.getString('Please confirm with one of these tokens:');
                    $scope.challenge_multiple_tokens = true;
                } else {
                    $scope.challenge_message = error.detail.message;
                    $scope.challenge_multiple_tokens = false;
                }
                for (var i = 0; i < multi_challenge.length; i++) {
                    if (multi_challenge.length > 1) {
                        $scope.challenge_message = $scope.challenge_message + ' ' + multi_challenge[i].serial;
                    }
                    var attributes = multi_challenge[i].attributes;
                    if (attributes === null || attributes.hideResponseInput !== true) {
                        $scope.hideResponseInput = false;
                    }
                    if (attributes !== null) {
                        if (attributes.u2fSignRequest) {
                           $scope.u2fSignRequests.push(attributes.u2fSignRequest);
                        }
                        if (attributes.img) {
                            $scope.image = attributes.img;
                            if ($scope.image.indexOf("data:image") === -1) {
                                // In case of an Image link, we prepend the instanceUrl
                                $scope.image = $scope.instanceUrl + "/" + $scope.image;
                            }
                        }
                        if (attributes.poll) {
                            $scope.polling = attributes.poll;
                        }
                    }
                }

                //debug: console.log($scope.polling);
                $scope.login.password = "";
                // In case of TiQR we need to start the poller
                if ($scope.polling) {
                    PollingAuthFactory.start($scope.check_authentication);
                }
                // In case of u2f we do:
                if ($scope.u2fSignRequests.length > 0) {
                    $scope.u2f_first_error = error;
                    U2fFactory.sign_request(error, $scope.u2fSignRequests,
                        $scope.login.username,
                        $scope.transactionid, $scope.do_login_stuff);
                }
            } else {
                if ($state.current.name === "response") {
                    // We are already in the response state, but the first
                    // response was not valid.
                    inform.add(gettextCatalog.getString("Challenge Response " +
                            "Authentication. Your response was not valid!"),
                        {type: "warning", ttl: 5000});
                    $scope.login.password = "";
                    // in case of U2F we try for a 2nd signature
                    // In case of u2f we do:
                    if ($scope.u2f_first_error) {
                        U2fFactory.sign_request($scope.u2f_first_error,
                            $scope.u2fSignRequests,
                            $scope.login.username,
                            $scope.transactionid, $scope.do_login_stuff);
                    }
                } else {
                        // TODO: Do we want to display the error message?
                        // This can show an attacker, if a username exists.
                        // But this can also be due to a problem like
                        // "HSM not ready".
                        $scope.transactionid = "";
                        var errmsg = gettextCatalog.getString("Authentication failed.");
                        inform.add(errmsg + " " + error.result.error.message,
                            {type: "danger", ttl: 10000});
                }
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
        //debug: console.log("calling check_authentication.");
        $http.post(authUrl, {
            username: $scope.login.username,
            password: "",
            transaction_id: $scope.transactionid
        }, {
            withCredentials: true
        }).success(function (data) {
            $scope.do_login_stuff(data);
            PollingAuthFactory.stop();
        });
    };

    $scope.do_login_stuff = function(data) {
        AuthFactory.setUser(data.result.value.username,
                data.result.value.realm,
                data.result.value.token,
                data.result.value.role,
                data.result.value.rights,
                data.result.value.menus);
            // clear old error messages
            inform.clear();
            if (data.detail) {
                $scope.pin_change_serial = data.detail.serial;
                $scope.pin_change = data.detail.pin_change;
                $scope.next_pin_change = data.detail.next_pin_change;
                if ($scope.next_pin_change && !$scope.pin_change_serial) {
                    inform.add(gettextCatalog.getString("Your OTP pin expires on ")
                        + $scope.next_pin_change,
                        {type: "warning", ttl: 5000, html: true});
                }
            }
            $scope.backend_log_level = data.result.value.log_level;
            $scope.backend_debug_passwords = data.result.value.debug_passwords;
            $scope.privacyideaVersionNumber = data.versionnumber;
            var lang = gettextCatalog.getCurrentLanguage();
            $scope.privacyideaSupportLink = "https://netknights.it/" + lang + "/support-link-" + data.result.value.role;
            $scope.loggedInUser = AuthFactory.getUser();
            $scope.token_wizard = data.result.value.token_wizard;
            $scope.token_wizard_2nd = data.result.value.token_wizard_2nd;
            $scope.token_page_size = data.result.value.token_page_size;
            $scope.user_page_size = data.result.value.user_page_size;
            $scope.user_details_in_tokenlist = data.result.value.user_details;
            $scope.default_tokentype = data.result.value.default_tokentype;
            $scope.timeout_action = data.result.value.timeout_action;
            $scope.hide_welcome = data.result.value.hide_welcome;
            $scope.hide_buttons = data.result.value.hide_buttons;
            $scope.show_seed = data.result.value.show_seed;
            $scope.subscription_state = data.result.value.subscription_status;
            $rootScope.search_on_enter = data.result.value.search_on_enter;
            var timeout = data.result.value.logout_time;
            PolicyTemplateFactory.setUrl(data.result.value.policy_template_url);
            //debug: console.log(timeout);
            var idlestart = timeout - 10;
            if (idlestart<=0) {
                idlestart = 1;
            }
            Idle.setIdle(idlestart);
            Idle.watch();
            //debug: console.log("successfully authenticated");
            //debug: console.log($scope.loggedInUser);
            if ( $scope.unlocking ) {
                $('#dialogLock').modal().hide();
                // Hack, since we can not close the modal and thus the body
                // keeps the modal-open and thus has no scroll-bars
                $("body").removeClass("modal-open");
            } else {
                // if we are unlocking we do NOT go to the tokens
                $location.path("/token");
            }

            //inform.add(gettextCatalog.getString("privacyIDEA UI supports " +
            //    "hotkeys. Use '?' to get help."), {type: "info", ttl: 10000});
            $scope.transactionid = "";
    };

    $scope.logout = function () {
        // logout: Clear the user and the auth_token.
        AuthFactory.dropUser();
        $scope.loggedInUser = {};
        $scope.privacyideaVersionNumber = null;
        $scope.logoutWarning = false;
        $scope.myCountdown = "";
        $scope.welcomeStep = 0;
        $scope.privacyideaSupportLink = $rootScope.publicLink;
        $state.go("login");
        Idle.unwatch();
        // Jump to top when the policy is saved
        $('html,body').scrollTop(0);
    };

    $scope.nextWelcome = function() {
        $scope.welcomeStep += 1;
        if ($scope.welcomeStep === 4) {
            $('#dialogWelcome').modal("hide");
            // Hack, since we can not close the modal and thus the body
            // keeps the modal-open and thus has no scroll-bars
            $("body").removeClass("modal-open");
        }
    };
    $scope.resetWelcome = function() {
        $scope.welcomeStep = 0;
    };

    $scope.lock_screen = function () {
        // We need to destroy the auth_token
        $scope.loggedInUser.auth_token = null;
        $scope.welcomeStep = 0;
        Idle.unwatch();
        $('#dialogLock').modal().show();
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
                                inform.add(gettextCatalog.getString("Realm " +
                                    "defrealm created."),
                                {type: "info"});

                            }
                        });
                }
        });

    };

    $scope.reload = function() {
        // emit a signal to the scope, that just listens
        $scope.$broadcast("piReload");
    };

    $scope.checkReloadListeners = function () {
        /*
         TODO: The a logic, that can hide the reload button.
         This is not straighforward, since the current number of connected
         listeners might be confusing:

         connected numbers:
         var currentListeners = $scope.$$listenerCount["piReload"];

         When the state changes, the scope and thus the current listener is
         destroyed. But the statechange-success is called, before the scope
         is destroyed, so there can be two connected listeners, when
         changing from a state to another state and both have a listener
         defined.
        */
        $scope.reloadListeners = 1;
    };

});

angular.module("privacyideaApp")
    .controller("pinChangeController",
                            function (Idle,
                                      $scope, $http, $location,
                                      authUrl, AuthFactory, $rootScope,
                                      $state, ConfigFactory, inform,
                                      PolicyTemplateFactory, gettextCatalog,
                                      hotkeys, RegisterFactory,
                                      U2fFactory, instanceUrl,
                                      PollingAuthFactory, TokenFactory)
{

    $scope.newpin = "";
    $scope.changePin = function () {
        TokenFactory.setpin($scope.pin_change_serial,
            "otppin", $scope.newpin, function () {
            inform.add(gettextCatalog.getString("PIN changed successfully."),
                {type: "info"});
            $scope.pin_change = null;
            $scope.next_pin_change = null;
            $scope.pin_change_serial = null;
        });

        $scope.pin_change = null;
        $scope.next_pin_change = null;
        $scope.pin_change_serial = null;
        $scope.logout();
    }

});
