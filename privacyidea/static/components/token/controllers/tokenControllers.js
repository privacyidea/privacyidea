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

myApp.controller("tokenMenuController", ['$scope', '$location', '$rootScope', 'AuthFactory', 'ConfigFactory',
    function ($scope, $location, $rootScope, AuthFactory, ConfigFactory) {
        $scope.loggedInUser = AuthFactory.getUser();

        // set default path
        if ($location.path() === "/token") {
            $location.path("/token/list");
            $scope.tokenMenu = true;
        }

        // watch the location to change the side menu from token to container
        $rootScope.$on('$locationChangeSuccess', function () {
            if ($location.path().includes("container")) {
                $scope.tokenMenu = false;
            } else {
                $scope.tokenMenu = true;
            }
        })
    }]);

myApp.controller("tokenController", ['TokenFactory', 'ConfigFactory', '$scope',
    '$location', 'AuthFactory', 'instanceUrl', '$rootScope',
    function (TokenFactory, ConfigFactory, $scope, $location, AuthFactory, instanceUrl, $rootScope) {
        $scope.tokensPerPage = $scope.token_page_size;
        $scope.params = {page: 1, sortdir: "asc"};
        $scope.reverse = false;
        $scope.loggedInUser = AuthFactory.getUser();
        $scope.selectedToken = {serial: null};
        $scope.clientpart = "";

        // Change the pagination
        $scope.pageChanged = function () {
            //debug: console.log('Page changed to: ' + $scope.params.page);
            $scope.get();
        };

        // This function fills $scope.tokendata
        $scope.get = function (live_search) {
            if ((!$rootScope.search_on_enter) || ($rootScope.search_on_enter && !live_search)) {
                $scope.params.serial = "*" + ($scope.serialFilter || "") + "*";
                $scope.params.tokenrealm = "*" + ($scope.tokenrealmFilter || "") + "*";
                $scope.params.type = "*" + ($scope.typeFilter || "") + "*";
                $scope.params.description = "*" + ($scope.descriptionFilter || "") + "*";
                $scope.params.rollout_state = "*" + ($scope.rolloutStateFilter || "") + "*";
                $scope.params.userid = "*" + ($scope.userIdFilter || "") + "*";
                $scope.params.resolver = "*" + ($scope.resolverFilter || "") + "*";
                $scope.params.pagesize = $scope.token_page_size;
                $scope.params.sortby = $scope.sortby;
                if ($scope.reverse) {
                    $scope.params.sortdir = "desc";
                } else {
                    $scope.params.sortdir = "asc";
                }
                TokenFactory.getTokens(function (data) {
                    if (data) {
                        $scope.tokendata = data.result.value;
                    }
                }, $scope.params);
            }
        };

        // single token function
        $scope.reset = function (serial) {
            TokenFactory.reset(serial, $scope.get);
        };
        $scope.disable = function (serial) {
            TokenFactory.disable(serial, $scope.get);
        };
        $scope.enable = function (serial) {
            TokenFactory.enable(serial, $scope.get);
        };

        // go to the list view by default
        if ($location.path() === "/token") {
            $location.path("/token/list");
        }
        if ($location.path() === "/token/list") {
            $scope.get();
        }
        // go to token.wizard, if the wizard is defined
        if ($scope.token_wizard) {
            $location.path("/token/wizard");
        }

        // go to change PIN, if we should change the PIN
        if ($scope.pin_change) {
            $location.path("/pinchange");
        }

        // listen to the reload broadcast
        $scope.$on("piReload", function () {
            /* Due to the parameter "live_search" in the get function
            we can not bind the get-function to piReload below. This
            will break in Chrome, would work in Firefox.
            So we need this wrapper function
            */
            $scope.get();
        });

    }]);


myApp.controller("tokenAssignController", ['$scope', 'TokenFactory',
    '$stateParams', 'AuthFactory', 'UserFactory', '$state',
    function tokenAssignController($scope, TokenFactory, $stateParams, AuthFactory, UserFactory, $state) {
        $scope.assignToken = function () {
            TokenFactory.assign({
                serial: fixSerial($scope.newToken.serial),
                pin: $scope.newToken.pin
            }, function () {
                $state.go('token.list');
            });
        };
    }]);

myApp.controller("tokenEnrollController", ["$scope", "TokenFactory", "$timeout", "$stateParams", "AuthFactory",
    "UserFactory", "$state", "ConfigFactory", "instanceUrl", "$http", "hotkeys", "gettextCatalog", "inform",
    "U2fFactory", "webAuthnToken", "versioningSuffixProvider", "$location",
    function tokenEnrollController($scope, TokenFactory, $timeout, $stateParams, AuthFactory, UserFactory, $state,
                                   ConfigFactory, instanceUrl, $http, hotkeys, gettextCatalog, inform, U2fFactory,
                                   webAuthnToken, versioningSuffixProvider, $location) {

        hotkeys.bindTo($scope).add({
            combo: 'alt+e',
            description: gettextCatalog.getString('Enroll a new token'),
            callback: function (event, hotkey) {
                event.preventDefault();
                $state.go('token.enroll');
                $scope.enrolledToken = null;
            }
        });
        hotkeys.bindTo($scope).add({
            combo: 'alt+r',
            description: gettextCatalog.getString('Roll the token'),
            callback: function () {
                $scope.enrollToken();
            }
        });

        $scope.qrCodeWidth = 250;

        // Available SMS gateways. We do this here to avoid javascript loops
        $scope.smsGateways = $scope.getRightsValue('sms_gateways', '').split(' ');

        if ($state.includes('token.wizard') && !$scope.show_seed) {
            $scope.qrCodeWidth = 300;
        }
        $scope.checkRight = AuthFactory.checkRight;
        $scope.loggedInUser = AuthFactory.getUser();
        $scope.newUser = {};
        $scope.tempData = {};
        $scope.instanceUrl = instanceUrl;
        $scope.click_wait = true;
        $scope.U2FToken = {};
        $scope.webAuthnToken = {};
        // System default values for enrollment
        $scope.systemDefault = {};
        // questions for questionnaire token
        $scope.questions = [];
        $scope.num_questions = 5;
        $scope.fileVersionSuffix = versioningSuffixProvider.$get();
        // These are values that are also sent to the backend!
        $scope.form = {
            timeStep: 30,
            otplen: 6,
            genkey: true,
            type: $scope.default_tokentype,
            hashlib: "sha1",
            'radius.system_settings': true,
            container_serial: null,
        };
        if ($state.includes('token.rollover')) {
            $scope.form.serial = $stateParams.tokenSerial;
            $scope.form.type = $stateParams.tokenType;
            $scope.form.container_serial = $stateParams.containerSerial;
        }
        $scope.vasco = {
            // Note: A primitive does not work in the ng-model of the checkbox!
            useIt: false
        };
        $scope.enrolling = false;
        $scope.containerSerial = $stateParams.containerSerial;

        $scope.formInit = {
            tokenTypes: {},  // will be set later with response from server
            timesteps: [30, 60],
            otplens: [6, 8],
            hashlibs: ["sha1", "sha256", "sha512"],
            service_ids: {}
        };

        $scope.loadAvailableServiceIDs = function () {
            ConfigFactory.getServiceid("", function (data) {
                let serviceids = data.result.value;
                angular.forEach(serviceids, function (serviceid_data, name) {
                    $scope.formInit.service_ids[name] = name + ": " + serviceid_data.description;
                });
            })
        }

        $scope.setVascoSerial = function () {
            if ($scope.form.otpkey.length === 496) {
                //console.log('DEBUG: got 496 hexlify otpkey, check vasco serialnumber!');

                // convert hexlified input blob to ascii and use the serialnumber (first 10 chars)
                const vasco_hex = $scope.form.otpkey.toString();//force conversion
                let vasco_otpstr = '';
                for (let i = 0; i < vasco_hex.length; i += 2)
                    vasco_otpstr += String.fromCharCode(parseInt(vasco_hex.substr(i, 2), 16));
                const vasco_serial = vasco_otpstr.slice(0, 10);
                //console.log(vasco_serial);
                $scope.vascoSerial = vasco_serial;
                if ($scope.vasco.useIt) {
                    $scope.form.serial = vasco_serial;
                } else {
                    delete $scope.form.serial;
                }
            } else {
                // If we do not have 496 characters this might be no correct vasco blob.
                // So we reset the serial
                $scope.vascoSerial = "";
                delete $scope.form.serial;
            }
        };

        // These token need to PIN
        // TODO: This is also contained in the tokentype class!
        $scope.changeTokenType = function () {
            //debug: console.log("Token Type Changed.");
            $scope.hidePin = ["sshkey", "certificate"].indexOf($scope.form.type) >= 0;
            if ($scope.form.type === "hotp") {
                // preset HOTP hashlib
                $scope.form.hashlib = $scope.systemDefault['hotp.hashlib'] || 'sha1';
            } else if ($scope.form.type === "totp") {
                // preset TOTP hashlib
                $scope.form.hashlib = $scope.systemDefault['totp.hashlib'] || 'sha1';
                $scope.form.timeStep = parseInt($scope.systemDefault['totp.timeStep'] || '30');
            } else if ($scope.form.type === "daypassword") {
                // preset DayPassword hashlib
                $scope.form.hashlib = $scope.systemDefault['daypassword.hashlib'] || 'sha1';
                $scope.form.timeStep = parseInt($scope.systemDefault['daypassword.timeStep'] || '60');
            }
            $scope.form.genkey = $scope.form.type !== "vasco";
            if ($scope.form.type === "applspec") {
                $scope.loadAvailableServiceIDs();
            }
            if ($scope.form.type === "yubikey") {
                // save the original otp length
                $scope.old_otplen = $scope.form.otplen;
                // set the default otp length for yubikeys in AES mode to 44
                // (12 characters (6 bytes) UID and 32 characters (16 bytes) OTP)
                $scope.form.otplen = 44;
            } else {
                // restore old otp length if available
                if (typeof $scope.old_otplen != "undefined") {
                    $scope.form.otplen = $scope.old_otplen;
                    delete $scope.old_otplen;
                }
            }

            $scope.preset_indexedsecret();

            if ($scope.form.type === "radius") {
                // only load RADIUS servers when the user actually tries to enroll a RADIUS token,
                // because the user might not be allowed to list RADIUS servers
                $scope.getRADIUSIdentifiers();
            }
            if ($scope.form.type === "remote") {
                // fetch the privacyIDEA servers
                $scope.getPrivacyIDEAServers();
            }
            if ($scope.form.type === "certificate") {
                $scope.getCAConnectors();
            }
            // preset twostep enrollment
            $scope.setTwostepEnrollmentDefault();
        };

        // helper function for setting indexed secret attribute
        $scope.preset_indexedsecret = function () {
            if ($scope.form.type === "indexedsecret") {
                // in case of indexedsecret we do never generate a key from the UI
                $scope.form.genkey = false;
                // Only fetch, if a preset_attribute is defined
                if ($scope.tokensettings.indexedsecret.preset_attribute) {
                    // In case of a normal logged in user, an empty params is fine
                    let params = {};
                    if (AuthFactory.getRole() === 'admin') {
                        params = {
                            realm: $scope.newUser.realm,
                            username: fixUser($scope.newUser.user)
                        };
                    }
                    UserFactory.getUsers(params,
                        function (data) {
                            const userObject = data.result.value[0];
                            // preset for indexedsecret token
                            $scope.form.otpkey = userObject[$scope.tokensettings.indexedsecret.preset_attribute];
                        });
                }
            }
        };

        // Set the default value of the "2stepinit" field if twostep enrollment should be forced
        $scope.setTwostepEnrollmentDefault = function () {
            $scope.form["2stepinit"] = $scope.checkRight($scope.form.type + "_2step=force");
        };

        // Initially set the default value
        $scope.setTwostepEnrollmentDefault();

        // A watch function to change the form data in case another user is selected
        $scope.$watch(function (scope) {
                return scope.newUser.email;
            },
            function (newValue, oldValue) {
                if (newValue !== '') {
                    $scope.form.email = newValue;
                }
            });
        $scope.$watch(function (scope) {
                return scope.newUser.mobile;
            },
            function (newValue, oldValue) {
                if (newValue !== '') {
                    $scope.form.phone = newValue;
                }
            });
        $scope.$watch(function (scope) {
                return fixUser(scope.newUser.user);
            },
            function (newValue, oldValue) {
                // The newUser was changed
                $scope.preset_indexedsecret();
            });

        // Helper function to populate user information
        $scope.get_user_infos = function (data) {
            const userObject = data.result.value[0];
            $scope.form.email = userObject.email;
            if (typeof userObject.mobile === "string") {
                $scope.form.phone = userObject.mobile;
            } else {
                $scope.phone_list = userObject.mobile;
                if ($scope.phone_list && $scope.phone_list.length === 1) {
                    $scope.form.phone = $scope.phone_list[0];
                }
            }
            return userObject;
        }

        // Get the realms and fill the realm dropdown box
        if (AuthFactory.getRole() === 'admin') {
            ConfigFactory.getRealms(function (data) {
                $scope.realms = data.result.value;
                // Set the default realm
                angular.forEach($scope.realms, function (realm, realmname) {
                    // if there is a default realm, preset the default realm
                    if (realm.default && !$stateParams.realmname) {
                        $scope.newUser = {user: "", realm: realmname};
                    }
                });

                // init the user, if token.enroll was called from the user.details
                if ($stateParams.realmname) {
                    $scope.newUser.realm = $stateParams.realmname;
                }
                if ($stateParams.username) {
                    $scope.newUser.user = $stateParams.username;
                    // preset the mobile and email for SMS or EMAIL token
                    UserFactory.getUsers({
                            realm: $scope.newUser.realm,
                            username: $scope.newUser.user
                        },
                        function (data) {
                            $scope.get_user_infos(data)
                        });
                }
            });
        } else if (AuthFactory.getRole() === 'user') {
            // init the user, if token.enroll was called as a normal user
            $scope.newUser.user = AuthFactory.getUser().username;
            $scope.newUser.realm = AuthFactory.getUser().realm;
            if ($scope.checkRight('userlist')) {
                UserFactory.getUserDetails({}, function (data) {
                    $scope.User = $scope.get_user_infos(data);
                });
            }
        }

        // Read the tokentypes from the server
        TokenFactory.getEnrollTokens(function (data) {
            //console.log("getEnrollTokens");
            //console.log(data);
            $scope.formInit["tokenTypes"] = data.result.value;
            // set the default tokentype
            if (!$scope.formInit.tokenTypes.hasOwnProperty(
                $scope.default_tokentype)) {
                // if HOTP does not exist, we set another default type
                for (const tkey in $scope.formInit.tokenTypes) {
                    // set the first key to be the default tokentype
                    $scope.form.type = tkey;
                    // Set the 2step enrollment value
                    $scope.setTwostepEnrollmentDefault();
                    // Initialize token specific settings
                    $scope.changeTokenType();
                    break;
                }
            }
        });

        $scope.CAConnectors = [];
        $scope.CATemplates = {};
        $scope.radioCSR = 'csrgenerate';

        // default enrollment callback
        $scope.callback = function (data) {
            let blob;
            $scope.U2FToken = {};
            $scope.webAuthnToken = {};
            $scope.enrolledToken = data.detail;
            $scope.click_wait = false;
            if ($scope.enrolledToken.otps) {
                const otps_count = Object.keys($scope.enrolledToken.otps).length;
                $scope.otp_row_count = parseInt(otps_count / 5 + 0.5);
                $scope.otp_rows = Object.keys($scope.enrolledToken.otps).slice(0, $scope.otp_row_count);
            } else {
                $scope.otp_rows = null;
            }
            if ($scope.enrolledToken.certificate) {
                blob = new Blob([$scope.enrolledToken.certificate],
                    {type: 'text/plain'});
                $scope.certificateBlob = (window.URL || window.webkitURL).createObjectURL(blob);
            }
            if ($scope.enrolledToken.pkcs12) {
                const bytechars = atob($scope.enrolledToken.pkcs12);
                const byteNumbers = new Array(bytechars.length);
                for (let i = 0; i < bytechars.length; i++) {
                    byteNumbers[i] = bytechars.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                blob = new Blob([byteArray], {type: 'application/x-pkcs12'});
                $scope.pkcs12Blob = (window.URL || window.webkitURL).createObjectURL(blob);
            }
            if ($scope.enrolledToken.u2fRegisterRequest) {
                // This is the first step of U2F registering, save serial.
                $scope.serial = data.detail.serial;

                $scope.register_fido($scope.enrolledToken.u2fRegisterRequest, U2fFactory, $scope.U2FToken);
            }
            if ($scope.enrolledToken.webAuthnRegisterRequest) {
                // This is the first step of U2F registering, save serial.
                $scope.serial = data.detail.serial;

                $scope.register_fido($scope.enrolledToken.webAuthnRegisterRequest, webAuthnToken, $scope.webAuthnToken);
            }
            if ($scope.enrolledToken.rollout_state === "clientwait" && !$scope.form["2stepinit"]) {
                $scope.pollTokenInfo();
            }
            // Passkey
            $scope.bytesToBase64 = function (bytes) {
                const binString = Array.from(bytes, (byte) =>
                    String.fromCodePoint(byte),).join("");
                return btoa(binString);
            };
            $scope.base64URLToBytes = function (base64URLString) {
                const base64 = base64URLString.replace(/-/g, '+').replace(/_/g, '/');
                const padLength = (4 - (base64.length % 4)) % 4;
                const padded = base64.padEnd(base64.length + padLength, '=');
                const binary = atob(padded);
                const buffer = new ArrayBuffer(binary.length);
                const bytes = new Uint8Array(buffer);
                for (let i = 0; i < binary.length; i++) {
                    bytes[i] = binary.charCodeAt(i);
                }
                return buffer;
            }

            if ($scope.enrolledToken.passkey_registration) {
                $scope.click_wait = true;
                //console.log($scope.enrolledToken.passkey_registration);
                let options = $scope.enrolledToken.passkey_registration;
                let excludedCredentials = [];
                for (const cred of options.excludeCredentials) {
                    excludedCredentials.push({
                        id: $scope.base64URLToBytes(cred.id),
                        type: cred.type,
                    });
                }
                navigator.credentials.create({
                    publicKey: {
                        rp: options.rp,
                        user: {
                            id: $scope.base64URLToBytes(options.user.id),
                            name: options.user.name,
                            displayName: options.user.displayName
                        },
                        challenge: Uint8Array.from(options.challenge, c => c.charCodeAt(0)),
                        pubKeyCredParams: options.pubKeyCredParams,
                        excludeCredentials: excludedCredentials,
                        authenticatorSelection: options.authenticatorSelection,
                        timeout: options.timeout,
                        extensions: {
                            credProps: true,
                        },
                        attestation: options.attestation
                    }
                }).then(function (publicKeyCred) {
                    //console.log("Successfully registered passkey");
                    //console.log(publicKeyCred);
                    let params = {
                        user: $scope.newUser.user,
                        realm: $scope.newUser.realm,
                        transaction_id: data.detail.transaction_id,
                        serial: data.detail.serial,
                        type: "passkey",
                        credential_id: publicKeyCred.id,
                        rawId: $scope.bytesToBase64(new Uint8Array(publicKeyCred.rawId)),
                        authenticatorAttachment: publicKeyCred.authenticatorAttachment,
                        attestationObject: $scope.bytesToBase64(
                            new Uint8Array(publicKeyCred.response.attestationObject)),
                        clientDataJSON: $scope.bytesToBase64(new Uint8Array(publicKeyCred.response.clientDataJSON)),
                    }
                    if (publicKeyCred.response.attestationObject) {
                        params.attestationObject = $scope.bytesToBase64(
                            new Uint8Array(publicKeyCred.response.attestationObject));
                    }
                    const extResults = publicKeyCred.getClientExtensionResults();
                    if (extResults.credProps) {
                        params.credProps = extResults.credProps;
                    }
                    TokenFactory.initToken(params, function (response) {
                        $scope.click_wait = false;
                    });
                }, function (error) {
                    console.log("Error while registering passkey");
                    console.log(error);
                    inform.add("Error while registering passkey, the token will not be created!",
                        {type: "danger", ttl: 10000});
                    if (AuthFactory.checkRight("delete")) {
                        TokenFactory.delete(data.detail.serial, function (response) {
                            $state.go('token.list');
                        });
                    }
                });
            }
            // End Passkey
            $('html,body').scrollTop(0);
        }

        $scope.enrollToken = function () {
            $scope.enrolling = true;
            //debug: console.log($scope.newUser.user);
            //debug: console.log($scope.newUser.realm);
            //debug: console.log($scope.newUser.pin);
            $scope.newUser.user = fixUser($scope.newUser.user);
            // convert the date object to a string
            $scope.form.validity_period_start = date_object_to_string($scope.form.validity_period_start);
            $scope.form.validity_period_end = date_object_to_string($scope.form.validity_period_end);

            if ($scope.containerSerial !== "createnew" && $scope.containerSerial !== "none") {
                $scope.form.container_serial = $scope.containerSerial;
            } else {
                // Do not send the container_serial if it has no value
                delete $scope.form.container_serial;
            }

            TokenFactory.enroll($scope.newUser,
                $scope.form, $scope.callback,
                function (data) {
                    $scope.enrolling = false;
                }
            );
        };

        $scope.pollTokenInfo = function () {
            TokenFactory.getTokenForSerial($scope.enrolledToken.serial, function (data) {
                if (data.result.value && data.result.value.tokens && data.result.value.tokens.length > 0) {
                    $scope.enrolledToken.rollout_state = data.result.value.tokens[0].rollout_state;
                }
                // Poll the data after 2.5 seconds again
                if ($scope.enrolledToken.rollout_state === "clientwait" && $location.path().indexOf("/token/enroll") > -1) {
                    $timeout($scope.pollTokenInfo, 2500);
                }
            })
        };

        $scope.regenerateToken = function (serial) {
            const params = $scope.form;
            if (serial) {
                params.serial = serial;
            } else {
                params.serial = $scope.enrolledToken.serial;
            }
            TokenFactory.enroll(null, params, $scope.callback);
        };

        $scope.sendClientPart = function () {
            const params = {
                "otpkey": $scope.clientpart.replace(/ /g, ""),
                "otpkeyformat": "base32check",
                "serial": $scope.enrolledToken.serial,
                "type": $scope.form.type,
                // Send the rollover parameter as well to avoid a possible PIN check
                "rollover": $scope.form.rollover
            };
            TokenFactory.enroll($scope.newUser, params, function (data) {
                $scope.clientpart = "";
                $scope.callback(data);
            });
        };

        $scope.sendVerifyResponse = function () {
            const params = {
                "serial": $scope.enrolledToken.serial,
                "verify": $scope.verifyResponse,
                "type": $scope.form.type
            };
            TokenFactory.enroll($scope.newUser, params, function (data) {
                if (data.result.value === true) {
                    inform.add(gettextCatalog.getString("Token successfully verified"),
                        {type: "success", ttl: 10000});
                }
                $scope.verifyResponse = "";
                $scope.callback(data);
            });
        };

        // Special Token functions
        $scope.sshkeyChanged = function () {
            const keyArr = $scope.form.sshkey.split(" ");
            $scope.form.description = keyArr.slice(2).join(" ");
        };

        $scope.yubikeyGetLen = function () {
            let yktestdatalen = $scope.tempData.yubikeyTest.trim().length;
            if (yktestdatalen >= 32) {
                $scope.form.otplen = yktestdatalen;
            }
        };

        // U2F and WebAuthn
        $scope.register_fido = function (registerRequest, Factory, token) {
            // We need to send the 2nd stage of the U2F enroll
            Factory.register_request(registerRequest, function (params) {
                params.serial = $scope.serial;
                TokenFactory.enroll($scope.newUser,
                    params, function (response) {
                        $scope.click_wait = false;
                        token.subject
                            = (response.detail.u2fRegisterResponse || response.detail.webAuthnRegisterResponse).subject;
                        token.vendor = token.subject.split(" ")[0];
                        //console.log(token);
                    });
            }, function (error) {
                if (AuthFactory.checkRight("delete")) {
                    TokenFactory.delete($scope.serial, function (response) {
                        $state.go('token.list');
                    });
                }
            });
            $scope.click_wait = true;
        };

        // get the list of configured RADIUS server identifiers
        $scope.getRADIUSIdentifiers = function () {
            ConfigFactory.getRadiusNames(function (data) {
                $scope.radiusIdentifiers = data.result.value;
            });
        };

        // get the list of configured privacyIDEA server identifiers
        $scope.getPrivacyIDEAServers = function () {
            ConfigFactory.getPrivacyidea(function (data) {
                $scope.privacyIDEAServers = data.result.value;
            });
        };

        // get the list of configured CA connectors
        $scope.getCAConnectors = function () {
            ConfigFactory.getCAConnectorNames(function (data) {
                const CAConnectors = data.result.value;
                angular.forEach(CAConnectors, function (value, key) {
                    $scope.CAConnectors.push(value.connectorname);
                    $scope.form.ca = value.connectorname;
                    $scope.CATemplates[value.connectorname] = value;
                });
                //debug: console.log($scope.CAConnectors);
            });
        };

        // If the user is admin, he can read the config.
        ConfigFactory.loadSystemConfig(function (data) {
            /* Default config values like
                radius.server, radius.secret...
               are stored in systemDefault and $scope.form
             */
            $scope.systemDefault = data.result.value;
            //debug: console.log("system default config");
            //debug: console.log(systemDefault);
            // TODO: The entries should be handled automatically.
            const entries = ["radius.server", "radius.secret", "remote.server",
                "radius.identifier", "email.mailserver",
                "email.mailfrom", "yubico.id", "tiqr.regServer"];
            entries.forEach(function (entry) {
                if (!$scope.form[entry]) {
                    // preset the UI
                    $scope.form[entry] = $scope.systemDefault[entry];
                }
            });
            // Default HOTP hashlib
            $scope.form.hashlib = $scope.systemDefault["hotp.hashlib"] || 'sha1';
            // Now add the questions
            angular.forEach($scope.systemDefault, function (value, key) {
                if (key.indexOf("question.question.") === 0) {
                    $scope.questions.push(value);
                }
            });
            $scope.num_answers = $scope.systemDefault["question.num_answers"];
            //debug: console.log($scope.questions);
            //debug: console.log($scope.form);
        });

        // open the window to generate the key pair
        $scope.openCertificateWindow = function () {
            const params = {
                authtoken: AuthFactory.getAuthToken(),
                ca: $scope.form.ca
            };
            const tabWindowId = window.open('about:blank', '_blank');
            $http.post(instanceUrl + '/certificate', params).then(
                function (response) {
                    //debug: console.log(response);
                    tabWindowId.document.write(response.data);
                    //tabWindowId.location.href = response.headers('Location');
                });
        };

        // print the paper token
        $scope.printOtp = function () {
            const serial = $scope.enrolledToken.serial;
            const myWindow = window.open('', 'otpPrintingWindow', 'height=400,width=600');
            const css = '<link' +
                ' href="' + instanceUrl +
                '/static/css/papertoken.css"' +
                ' rel="stylesheet">';
            myWindow.document.write('<html><head><title>' + serial + '</title>');
            myWindow.document.write(css);
            myWindow.document.write('</head>' +
                '<body onload="window.print(); window.close()">');
            myWindow.document.write($('#paperOtpTable').html());
            myWindow.document.write('</body></html>');
            myWindow.document.close(); // necessary for IE >= 10
            myWindow.focus(); // necessary for IE >= 10
            return true;
        };

        $scope.copyPKCS12PasswordToClipboard = function (text) {
            navigator.clipboard.writeText(text).then(function () {
                inform.add(gettextCatalog.getString("PKCS12 Password copied to clipboard"),
                    {type: "info", ttl: 3000})
            });
        }

        // ===========================================================
        // ===============  Date stuff ===============================
        // ===========================================================

        $scope.openDate = function ($event) {
            $event.stopPropagation();
            return true;
        };

        $scope.today = new Date();
        $scope.dateOptions = {
            formatYear: 'yy',
            startingDay: 1
        };
    }
]);

myApp.controller("tokenImportController", ['$scope', 'Upload', 'AuthFactory', 'tokenUrl', 'ConfigFactory', 'inform',
    'gettextCatalog',
    function ($scope, Upload, AuthFactory, tokenUrl, ConfigFactory, inform, gettextCatalog) {
        $scope.formInit = {
            fileTypes: ["aladdin-xml", "OATH CSV", "Yubikey CSV", "pskc"]
        };

        $scope.verify_pskc_opts = {
            no_check: gettextCatalog.getString('Do not verify the authenticity'),
            check_fail_soft: gettextCatalog.getString('Skip tokens that can not be verified'),
            check_fail_hard: gettextCatalog.getString('Abort operation on unverifiable token'),
        }

        // These are values that are also sent to the backend!
        $scope.form = {
            type: "OATH CSV",
            realm: ""
        };

        // get Realms
        ConfigFactory.getRealms(function (data) {
            $scope.realms = data.result.value;
            // Preset the default realm
            angular.forEach($scope.realms, function (realm, realmname) {
                if (realm.default) {
                    $scope.form.realm = realmname;
                }
            });
        });

        // get PGP keys
        ConfigFactory.getPGPKeys(function (data) {
            $scope.pgpkeys = data.result.value;
        });

        $scope.upload = function (file) {
            if (file) {
                Upload.upload({
                    url: tokenUrl + '/load/filename',
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    data: {
                        file: file,
                        type: $scope.form.type,
                        psk: $scope.form.psk,
                        pskcValidateMAC: $scope.form.validateMAC,
                        password: $scope.form.password,
                        tokenrealms: $scope.form.realm
                    },
                }).then(function (resp) {
                    $scope.uploadedFile = resp.config.data.file.name;
                    $scope.uploadedTokens = resp.data.result.value.n_imported;
                    $scope.notImportedTokens = resp.data.result.value.n_not_imported;
                }, function (error) {
                    if (error.data.result.error.code === -401) {
                        $state.go('login');
                    } else {
                        inform.add(error.data.result.error.message,
                            {type: "danger", ttl: 10000});
                    }
                }, function (evt) {
                    $scope.uploadProgress = parseInt(100.0 * evt.loaded / evt.total)
                });
            }
        };
    }]);
