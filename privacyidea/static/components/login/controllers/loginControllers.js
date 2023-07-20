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
//Otherwise, return the result of the ordinary split.
String.prototype.mysplit = function(separator) {
    return this == "" ? [] : this.split(separator);
};


angular.module("privacyideaApp")
    .controller("mainController", ["Idle", "$scope", "$sce", "$http", "$location",
                                   "authUrl", "validateUrl", "AuthFactory", "$rootScope",
                                   "$state", "ConfigFactory", "inform",
                                   "PolicyTemplateFactory", "gettextCatalog",
                                   "hotkeys", "RegisterFactory",
                                   "U2fFactory", "webAuthnToken", "instanceUrl",
                                   "PollingAuthFactory", "$transitions",
                                   "resourceNamePatterns", "$window",
                                   function (Idle, $scope, $sce, $http, $location,
                                             authUrl, validateUrl, AuthFactory, $rootScope,
                                             $state, ConfigFactory, inform,
                                             PolicyTemplateFactory, gettextCatalog,
                                             hotkeys, RegisterFactory,
                                             U2fFactory, webAuthnToken, instanceUrl,
                                             PollingAuthFactory, $transitions,
                                             resourceNamePatterns, $window) {

    $scope.instanceUrl = instanceUrl;
    $scope.checkRight = AuthFactory.checkRight;
    $scope.getRightsValue = AuthFactory.getRightsValue;
    $scope.checkMainMenu = AuthFactory.checkMainMenu;
    $scope.checkEnroll = AuthFactory.checkEnroll;
    $scope.inputNamePatterns = resourceNamePatterns;
    $scope.startRoute = "/token";
    var obj = angular.element(document.querySelector("#REMOTE_USER"));
    $scope.remoteUser = obj.val();
    if (!$scope.remoteUser) {
        $scope.loginWithCredentials = true;
    }
    obj = angular.element(document.querySelector('#FORCE_REMOTE_USER'));
    $scope.forceRemoteUser = obj.val();
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
    $scope.hasJobQueue = obj.val() === "True";
    obj = angular.element(document.querySelector('#LOGIN_TEXT'));
    $scope.piLoginText = obj.val();
    obj = angular.element(document.querySelector('#SHOW_NODE'));
    $scope.show_node = obj.val();
    obj = angular.element(document.querySelector('#GDPR_LINK'));
    // we need to trust the GDPR URI explicitly since an admin can change this via policy.
    $scope.piGDPRLink = $sce.trustAsUrl(obj.val());
    obj = angular.element(document.querySelector('#PI_TRANSLATION_WARNING'));
    $scope.piTranslationWarning = obj.val() !== "False";
    $scope.piTranslationPrefix = obj.val();
    gettextCatalog.debug = $scope.piTranslationWarning;
    gettextCatalog.debugPrefix = $scope.piTranslationPrefix;

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

    $scope.confirmDelete = function(delete_function, identifier) {
        $scope.confirmDeleteObj = {
            question: document.activeElement.getAttribute('aria-label'),
            identifier: identifier,
            delete_function: delete_function
        };
        if (!$scope.confirmDeleteObj.question) {
            $scope.confirmDeleteObj.question = gettextCatalog.getString('Do you really want to delete this object?');
        }
        if ($scope.deletion_confirmation) {
            $('#dialogConfirmDelete').modal();
        } else {
            $scope.confirmDeleteObj.delete_function($scope.confirmDeleteObj.identifier);
        }
    };

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
    $transitions.onBefore({},
        function () {
            // The stateParams or $state.params are always changed as a reference.
            // So we need to do a deep copy, to preserve it between state transitions
            var oldParams = {};
            angular.copy($state.params, oldParams);
            $rootScope.previousState = {
                state: $state.current.name,
                params: oldParams
            };
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
        if ($scope.timeout_action === "logout") {
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
        }).then(function (response) {
            // failed auth request (may be challenge-response)
            //debug: console.log("challenge response");
            //debug: console.log(error);
            let data = response.data;
            if (data.result.value && data.result.value.token) {
                // successful authentication
                $scope.do_login_stuff(response.data);
                // login data is not needed anymore, remove from scope
                $scope.login = {username: "", password: ""};
            } else if (data.detail && data.detail.transaction_id) {
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
                    {type: "warning", ttl: 5000});
                $scope.hideResponseInput = true;
                $scope.u2fSignRequests = Array();
                $scope.webAuthnSignRequests = [];
                $scope.transactionid = data.detail["transaction_id"];
                // Challenge Response always contains multi_challenge!
                var multi_challenge = data.detail.multi_challenge;
                if (multi_challenge.length > 1) {
                    $scope.challenge_message = gettextCatalog.getString('Please confirm with one of these tokens:');
                    $scope.challenge_multiple_tokens = true;
                } else {
                    $scope.challenge_message = data.detail.message;
                    $scope.challenge_multiple_tokens = false;
                }
                for (var i = 0; i < multi_challenge.length; i++) {
                    if (multi_challenge.length > 1) {
                        $scope.challenge_message = $scope.challenge_message + ' ' + multi_challenge[i].serial;
                    }
                    let challenge = multi_challenge[i];
                    if (challenge !== null) {
                        if (challenge.client_mode === 'interactive') {
                            // if we have at least one interactive token, we need to show the input field
                            $scope.hideResponseInput = false;
                        }
                        let attributes = challenge.attributes ? challenge.attributes : null;
                        if (attributes && attributes.u2fSignRequest) {
                            $scope.u2fSignRequests.push(attributes.u2fSignRequest);
                        }
                        if (attributes && attributes.webAuthnSignRequest) {
                            $scope.webAuthnSignRequests.push(attributes.webAuthnSignRequest);
                        }
                        if (challenge.image) {
                            // This should always be a base64 encoded image
                            $scope.image = challenge.image;
                        }
                        if (challenge.client_mode && challenge.client_mode === 'poll') {
                            $scope.polling = true;
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
                    $scope.u2f_first_error = data;
                    U2fFactory.sign_request(data, $scope.u2fSignRequests,
                        $scope.login.username,
                        $scope.transactionid, $scope.do_login_stuff);
                }
                // In case of webAuthn we do:
                if ($scope.webAuthnSignRequests.length > 0) {
                    $scope.webauthn_first_error = data;
                    webAuthnToken.sign_request(
                        $scope.webauthn_first_error,
                        $scope.webAuthnSignRequests,
                        $scope.login.username,
                        $scope.transactionid,
                        $scope.do_login_stuff
                    );
                }
            } else {
                inform.add(gettextCatalog.getString("Something went wrong!"),
                    {type: "error", ttl: 5000});
                $state.go("login");
            }
        }, function (error) {
            // TODO: Do we want to display the error message?
            // This can show an attacker, if a username exists.
            // But this can also be due to a problem like
            // "HSM not ready".
            if ($state.current.name === "response") {
                // We are already in the response state, but the first
                // response was not valid.
                inform.add(gettextCatalog.getString("Challenge Response " +
                        "Authentication. Your response was not valid!"),
                    {type: "warning", ttl: 5000});
                // in case of U2F we try for a 2nd signature
                // In case of u2f we do:
                if ($scope.u2f_first_error) {
                    U2fFactory.sign_request($scope.u2f_first_error,
                        $scope.u2fSignRequests,
                        $scope.login.username,
                        $scope.transactionid, $scope.do_login_stuff);
                }
                // In case of WebAuthn we try for a 2nd signature:
                if ($scope.webauthn_first_error) {
                    webAuthnToken.sign_request(
                        $scope.webauthn_first_error,
                        $scope.webAuthnSignRequests,
                        $scope.login.username,
                        $scope.transactionid,
                        $scope.do_login_stuff
                    )
                }
            } else {
                var errmsg = gettextCatalog.getString("Authentication failed.");
                inform.add(errmsg + " " + error.data.result.error.message,
                    {type: "danger", ttl: 10000});
            }
        });
    };

    $scope.check_authentication = function() {
        // This function is used to poll, if a challenge response
        // authentication was performed successfully in the background
        // This is used for the TiQR token.
        //debug: console.log("calling check_authentication.");
        $http.get(validateUrl + "/polltransaction", {
            params: {
                'transaction_id': $scope.transactionid
            }
        }).then(function (response) {
            if (response.data.result.value === true) {
                $http.post(authUrl, {
                    username: $scope.login.username,
                    password: "",
                    transaction_id: $scope.transactionid
                }).then(function (response) {
                    $scope.do_login_stuff(response.data);
                }, function (response) {
                    console.log('Authentication failed after polling!');
                    console.log(response.data);
                });
                PollingAuthFactory.stop();
            }
            // if result.value is false, the challenge hasn't been answered yet.
            // Continue polling
        }, function(response) {
            // the /validate/polltransaction endpoint returned an error
            console.warn("Polling for transactions returned an error: " + response.data);
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
            $scope.dialogNoToken = data.result.value.dialog_no_token;
            if ($scope.dialogNoToken) {
                $('#dialogNoToken').modal("show");
            }
            $scope.qr_images = [];
            if ( data.result.value.qr_image_android ) {
                $scope.qr_images.push({
                    'src': data.result.value.qr_image_android,
                    'alt': 'QR-Code with link to android app in play store',
                    'help': gettextCatalog.getString('Get the Authenticator App for Android.')})
            }
            if ( data.result.value.qr_image_ios ) {
                $scope.qr_images.push({
                    'src': data.result.value.qr_image_ios,
                    'alt': 'QR-Code with link to iOS app in app store',
                    'help': gettextCatalog.getString('Get the Authenticator App for iOS.')})
            }
            if ( data.result.value.qr_image_custom ) {
                $scope.qr_images.push({
                    'src': data.result.value.qr_image_custom,
                    'alt': 'QR-Code with link to a custom app',
                    'help': gettextCatalog.getString('Get the Authenticator App.')})
            }
            if ($scope.qr_images.length > 0) {
                $scope.qr_col_md = "col-md-" + parseInt(12 / $scope.qr_images.length);
            }
            $scope.audit_page_size = data.result.value.audit_page_size;
            $scope.require_description = data.result.value.require_description;
            $scope.token_page_size = data.result.value.token_page_size;
            $scope.user_page_size = data.result.value.user_page_size;
            $scope.user_details_in_tokenlist = data.result.value.user_details;
            $scope.default_tokentype = data.result.value.default_tokentype;
            $scope.timeout_action = data.result.value.timeout_action;
            $scope.admin_dashboard = data.result.value.admin_dashboard;
            if ($scope.admin_dashboard) {
                $scope.startRoute = "/dashboard";
            } else {
                $scope.startRoute = "/token";
            }
            $scope.logout_redirect_url = data.result.value.logout_redirect_url;
            $scope.hide_welcome = data.result.value.hide_welcome;
            $scope.hide_buttons = data.result.value.hide_buttons;
            $scope.deletion_confirmation = data.result.value.deletion_confirmation;
            $scope.show_seed = data.result.value.show_seed;
            $scope.show_node = data.result.value.show_node;
            $scope.token_rollover = data.result.value.token_rollover;
            $scope.subscription_state = data.result.value.subscription_status;
            $scope.subscription_state_push = data.result.value.subscription_status_push;
            $rootScope.search_on_enter = data.result.value.search_on_enter;
            // Token specific settings
            $scope.tokensettings = {indexedsecret:
                    {preset_attribute: data.result.value.indexedsecret_preset_attribute,
                     force_attibute: data.result.value.indexedsecret_force_attribute}
            };
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
            if ($scope.loggedInUser.role === "admin") {
            /*
            * Functions to check and to create a default realm.
            */
                ConfigFactory.getRealms(function (data) {
                    // Check if there is a realm defined, or if we should display the
                    // Auto Create Dialog
                    var number_of_realms = Object.keys(data.result.value).length;
                    if (number_of_realms === 0) {
                        $('#dialogAutoCreateRealm').modal();
                    }
                });
                /*
                 Welcome dialog, which displays a lot of information to the
                 administrator.

                 We display it if
                 subscription_state = 0 and hide_welcome = false
                 subscription_state = 1
                 subscription_state = 2
                 */
                $scope.resetWelcome();
                if (($scope.welcomeStep < 4 && !$scope.hide_welcome) || $scope.welcomeStep < 5) {
                    // We did not walk through the welcome dialog, yet.
                    if (($scope.subscription_state === 0 && !$scope.hide_welcome) ||
                        ($scope.subscription_state === 1)) {
                        $('#dialogWelcome').modal("show");
                    }
                }
                var $random_number = Math.floor(Math.random() * (9999 + 1000 + 1)) + 1000;
                $scope.class_subscription_expired = "subscriptionExpired" + $random_number;
                // Show info about privacyIDEA Authenticator App and push
                if ($scope.subscription_state_push === 1 && !$scope.hide_welcome) {
                    // no subscription at all
                     inform.add(gettextCatalog.getString("You are using a certain amount of Push tokens. " +
                         "Note, that you need a valid subscription, to use Push tokens in push mode. Otherwise" +
                         " Push tokens will only work in poll only mode. "),
                            {type: "danger", ttl: 30000});
                }
                if ($scope.subscription_state_push === 2) {
                    // Subscription expired
                    inform.add(gettextCatalog.getString("Your subscription for the privacyIDEA Authenticator" +
                        " has expired."),
                        {type: "danger", ttl: 20000});
                }
            }
            if ( $scope.unlocking ) {
                $('#dialogLock').modal('hide');
            } else {
                // if we login anew, we either go to the token or to the dashboard
                $location.path($scope.startRoute);
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
        $scope.resetWelcome();
        $scope.dialogNoToken = false;
        $scope.privacyideaSupportLink = $rootScope.publicLink;
        $state.go("login");
        Idle.unwatch();
        // Jump to top when the policy is saved
        $('html,body').scrollTop(0);
        // Optional redirect on logout
        if ($scope.logout_redirect_url !== "") {
            console.log("Redirecting to "+$scope.logout_redirect_url)
            $window.location.href = $scope.logout_redirect_url;
        }
    };

    $scope.nextWelcome = function() {
        $scope.welcomeStep += 1;
        if (($scope.subscription_state === 0 && $scope.welcomeStep === 4) ||
            ($scope.subscription_state === 1 && $scope.welcomeStep === 5)) {
            $('#dialogWelcome').modal("hide");
        }
    };
    $scope.resetWelcome = function() {
        if ($scope.hide_welcome) {
            $scope.welcomeStep = 4;
        } else {
            $scope.welcomeStep = 0;
        }

    };

    $scope.closeNoToken = function() {
        $scope.dialogNoToken = false;
        $('#dialogNoToken').modal('hide');
    };

    $scope.lock_screen = function () {
        // We need to destroy the auth_token
        $scope.loggedInUser.auth_token = null;
        $scope.resetWelcome();
        Idle.unwatch();
        $('#dialogLock').modal({
            keyboard: false,
            backdrop: 'static',
        }).show();
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

}]);

angular.module("privacyideaApp")
    .controller("pinChangeController", ["Idle", "$scope", "$http", "$location",
                                        "authUrl", "AuthFactory", "$rootScope",
                                        "$state", "ConfigFactory", "inform",
                                        "PolicyTemplateFactory", "gettextCatalog",
                                        "hotkeys", "RegisterFactory",
                                        "U2fFactory", "instanceUrl",
                                        "PollingAuthFactory", "TokenFactory",
                                        function (Idle, $scope, $http, $location,
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

}]);
