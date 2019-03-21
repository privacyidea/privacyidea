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
myApp.controller("tokenController", function (TokenFactory, ConfigFactory,
                                              $scope, $location, AuthFactory,
                                              instanceUrl,
                                              $rootScope, gettextCatalog,
                                              hotkeys) {
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
            $scope.params.type = "*" + ($scope.typeFilter || "") + "*";
            $scope.params.description = "*" + ($scope.descriptionFilter || "") + "*";
            $scope.params.userid = "*" + ($scope.userIdFilter || "") + "*";
            $scope.params.resolver = "*" + ($scope.resolverFilter || "") + "*";
            $scope.params.pagesize = $scope.token_page_size;
            if ($scope.reverse) {
                $scope.params.sortdir = "desc";
            } else {
                $scope.params.sortdir = "asc";
            }
            TokenFactory.getTokens(function (data) {
                if (data) {
                    $scope.tokendata = data.result.value;
                    //debug: console.log($scope.tokendata);
                }
            }, $scope.params);
        }
    };

    if ($scope.loggedInUser.role === "admin") {
        /*
        * Functions to check and to create a default realm. At the moment this is
        * in the tokenview, as the token view is the first view. This could be
        * changed to be located anywhere else.
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
        if ($scope.welcomeStep < 4) {
            // We did not walk throught the welcome dialog, yet.
            if (($scope.subscription_state === 0 && !$scope.hide_welcome) ||
                ($scope.subscription_state === 1) ||
                ($scope.subscription_state === 2)) {
                $('#dialogWelcome').modal("show");
                $("body").addClass("modal-open");
            }
        }
    }

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

    if ($location.path() === "/token/list") {
        $scope.get();
    }

    // go to the list view by default
    if ($location.path() === "/token") {
        $location.path("/token/list");
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
    $scope.$on("piReload", function() {
        /* Due to the parameter "live_search" in the get function
        we can not bind the get-function to piReload below. This
        will break in Chrome, would work in Firefox.
        So we need this wrapper function
        */
        $scope.get();
    });

});


myApp.controller("tokenAssignController", function ($scope, TokenFactory,
                                                    $stateParams, AuthFactory,
                                                    UserFactory, $state) {
    $scope.assignToken = function () {
        TokenFactory.assign({
            serial: fixSerial($scope.newToken.serial),
            pin: $scope.newToken.pin
        }, function () {
            $state.go('token.list');
        });
    };
});

myApp.controller("tokenEnrollController", function ($scope, TokenFactory,
                                                    $timeout,
                                                    $stateParams, AuthFactory,
                                                    UserFactory, $state,
                                                    ConfigFactory, instanceUrl,
                                                    $http, hotkeys,
                                                    gettextCatalog,
                                                    inform, U2fFactory) {

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

    if ($state.includes('token.wizard') && !$scope.show_seed) {
        $scope.qrCodeWidth = 500;
    }

    $scope.checkRight = AuthFactory.checkRight;
    $scope.loggedInUser = AuthFactory.getUser();
    $scope.newUser = {};
    $scope.tempData = {};
    $scope.instanceUrl = instanceUrl;
    $scope.click_wait = true;
    $scope.U2FToken = {};
    // System default values for enrollment
    $scope.systemDefault = {};
    // questions for questionnaire token
    $scope.questions = [];
    $scope.num_questions = 5;
    // These are values that are also sent to the backend!
    $scope.form = {
        timeStep: 30,
        otplen: 6,
        genkey: true,
        type: $scope.default_tokentype,
        hashlib: "sha1",
        'radius.system_settings': true
    };
    $scope.vasco = {
        // Note: A primitive does not work in the ng-model of the checkbox!
        useIt: false
    };

    $scope.formInit = {
        tokenTypes: {"hotp": gettextCatalog.getString("HOTP: event based One Time Passwords"),
            "totp": gettextCatalog.getString("TOTP: time based One Time Passwords"),
            "spass": gettextCatalog.getString("SPass: Simple Pass token. Static passwords"),
            "motp": gettextCatalog.getString("mOTP: classical mobile One Time Passwords"),
            "sshkey": gettextCatalog.getString("SSH Public Key: The public SSH key"),
            "yubikey": gettextCatalog.getString("Yubikey AES mode: One Time Passwords with" +
                " Yubikey"),
            "remote": gettextCatalog.getString("Remote Token: Forward authentication request" +
                " to another server"),
            "yubico": gettextCatalog.getString("Yubikey Cloud mode: Forward authentication" +
                " request to YubiCloud"),
            "radius": gettextCatalog.getString("RADIUS: Forward authentication request to a" +
                " RADIUS server"),
            "email": gettextCatalog.getString("EMail: Send a One Time Password to the users email" +
                " address."),
            "sms": gettextCatalog.getString("SMS: Send a One Time Password to the users" +
                " mobile phone."),
            "certificate": gettextCatalog.getString("Certificate: Enroll an x509 Certificate" +
                " Token."),
            "4eyes": gettextCatalog.getString("Four Eyes: Two or more users are required to" +
                " log in."),
            "tiqr": gettextCatalog.getString("TiQR: Authenticate with Smartphone by scanning" +
                " a QR code."),
            "u2f": gettextCatalog.getString("U2F: Universal 2nd Factor hardware token."),
            "paper": gettextCatalog.getString("PAPER: OTP values on a sheet of paper.")},
        timesteps: [30, 60],
        otplens: [6, 8],
        hashlibs: ["sha1", "sha256", "sha512"]
    };

    $scope.setVascoSerial = function() {
        if ($scope.form.otpkey.length === 496) {
                 //console.log('DEBUG: got 496 hexlify otpkey, check vasco serialnumber!');

                 // convert hexlified input blob to ascii and use the serialnumber (first 10 chars)
                 var vasco_hex = $scope.form.otpkey.toString();//force conversion
                 var vasco_otpstr = '';
                 for (var i = 0; i < vasco_hex.length; i += 2)
                     vasco_otpstr += String.fromCharCode(parseInt(vasco_hex.substr(i, 2), 16));
                 var vasco_serial = vasco_otpstr.slice(0, 10);
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
    $scope.changeTokenType = function() {
        //debug: console.log("Token Type Changed.");
        if (["sshkey", "certificate"].indexOf($scope.form.type) >= 0) {
            $scope.hidePin = true;
        } else {
            $scope.hidePin = false;
        }
        if ($scope.form.type === "hotp") {
            // preset HOTP hashlib
            $scope.form.hashlib = $scope.form['hotp.hashlib'];
        } else if ($scope.form.type === "totp") {
            // preset TOTP hashlib
            $scope.form.hashlib = $scope.form['totp.hashlib'];
        }
        if ($scope.form.type === "vasco") {
            $scope.form.genkey = false;
        } else {
            $scope.form.genkey = true;
        }
        // preset twostep enrollment
        $scope.setTwostepEnrollmentDefault();
    };

    // Set the default value of the "2stepinit" field if twostep enrollment should be forced
    $scope.setTwostepEnrollmentDefault = function () {
        $scope.form["2stepinit"] = $scope.checkRight($scope.form.type + "_2step=force");
    };

    // Initially set the default value
    $scope.setTwostepEnrollmentDefault();

    // A watch function to change the form data in case another user is selected
    $scope.$watch(function(scope) {return scope.newUser.email;},
        function(newValue, oldValue){
            if (newValue != '') {
                $scope.form.email = newValue;
            }
        });
    $scope.$watch(function(scope) {return scope.newUser.mobile;},
        function(newValue, oldValue){
            if (newValue != '') {
                $scope.form.phone = newValue;
            }
        });

    // Get the realms and fill the realm dropdown box
    if (AuthFactory.getRole() === 'admin') {
        ConfigFactory.getRealms(function (data) {
            $scope.realms = data.result.value;
            // Set the default realm
            var size = Object.keys($scope.realms).length;
            angular.forEach($scope.realms, function (realm, realmname) {
                if (size === 1) {
                    // if there is only one realm, preset it
                    $scope.newUser = {user: "", realm: realmname};
                }
                // if there is a default realm, preset the default realm
                if (realm.default && !$stateParams.realmname) {
                    $scope.newUser = {user: "", realm: realmname};
                    //debug: console.log("tokenEnrollController");
                    //debug: console.log($scope.newUser);
                }
            });
            // init the user, if token.enroll was called from the user.details
            if ($stateParams.realmname) {
                $scope.newUser.realm = $stateParams.realmname;
            }
            if ($stateParams.username) {
                $scope.newUser.user = $stateParams.username;
                // preset the mobile and email for SMS or EMAIL token
                UserFactory.getUsers({realm: $scope.newUser.realm,
                    username: $scope.newUser.user},
                    function(data) {
                        var userObject = data.result.value[0];
                        $scope.form.email = userObject.email;
                        if (typeof userObject.mobile === "string") {
                            $scope.form.phone = userObject.mobile;
                        } else {
                            $scope.phone_list = userObject.mobile;
                            if ($scope.phone_list.length === 1) {
                                $scope.form.phone = $scope.phone_list[0];
                            }
                        }
                });
            }
        });
    } else if (AuthFactory.getRole() === 'user') {
        // init the user, if token.enroll was called as a normal user
        $scope.newUser.user = AuthFactory.getUser().username;
        $scope.newUser.realm = AuthFactory.getUser().realm;
    }

    // Read the the tokentypes from the server
    TokenFactory.getEnrollTokens(function(data){
        //debug: console.log("getEnrollTokens");
        //debug: console.log(data);
        $scope.formInit["tokenTypes"] = data.result.value;
        // set the default tokentype
        if (!$scope.formInit.tokenTypes.hasOwnProperty(
                $scope.default_tokentype)) {
            // if HOTP does not exist, we set another default type
            for (var tkey in $scope.formInit.tokenTypes) {
                // set the first key to be the default tokentype
                $scope.form.type = tkey;
                // Set the 2step enrollment value
                $scope.setTwostepEnrollmentDefault();
                break;
            }
        }
    });

    $scope.CAConnectors = [];
    $scope.CATemplates = {};
    $scope.radioCSR = 'csrgenerate';


    // default enrollment callback
    $scope.callback = function (data) {
        $scope.U2FToken = {};
        $scope.enrolledToken = data.detail;
        $scope.click_wait=false;
        if ($scope.enrolledToken.otps) {
            var otps_count = Object.keys($scope.enrolledToken.otps).length;
            $scope.otp_row_count = parseInt(otps_count/5 + 0.5);
            $scope.otp_rows = Object.keys($scope.enrolledToken.otps).slice(0, $scope.otp_row_count);
        }
        if ($scope.enrolledToken.certificate) {
            var blob = new Blob([ $scope.enrolledToken.certificate ],
                { type : 'text/plain' });
            $scope.certificateBlob = (window.URL || window.webkitURL).createObjectURL( blob );
        }
        if ($scope.enrolledToken.pkcs12) {
            var bytechars = atob($scope.enrolledToken.pkcs12);
            var byteNumbers = new Array(bytechars.length);
            for (var i = 0; i < bytechars.length; i++) {
                byteNumbers[i] = bytechars.charCodeAt(i);
            }
            var byteArray = new Uint8Array(byteNumbers);
            var blob = new Blob([byteArray], {type: 'application/x-pkcs12'});
            $scope.pkcs12Blob = (window.URL || window.webkitURL).createObjectURL( blob );
        }
        if ($scope.enrolledToken.u2fRegisterRequest) {
            // This is the first step of U2F registering
            // save serial
            $scope.serial = data.detail.serial;
            // We need to send the 2nd stage of the U2F enroll
            $scope.register_u2f($scope.enrolledToken.u2fRegisterRequest);
            $scope.click_wait=true;
        }
        if ($scope.enrolledToken.rollout_state === "clientwait") {
            $scope.pollTokenInfo();
        }
        $('html,body').scrollTop(0);
    };

    $scope.enrollToken = function () {
        //debug: console.log($scope.newUser.user);
        //debug: console.log($scope.newUser.realm);
        //debug: console.log($scope.newUser.pin);
        $scope.newUser.user = fixUser($scope.newUser.user);
        // convert the date object to a string
        $scope.form.validity_period_start = date_object_to_string($scope.form.validity_period_start);
        $scope.form.validity_period_end = date_object_to_string($scope.form.validity_period_end);
        TokenFactory.enroll($scope.newUser,
            $scope.form, $scope.callback);
    };

    $scope.pollTokenInfo = function () {
        TokenFactory.getTokenForSerial($scope.enrolledToken.serial, function(data) {
            $scope.enrolledToken.rollout_state = data.result.value.tokens[0].rollout_state;
            // Poll the data after 2.5 seconds again
            if ($scope.enrolledToken.rollout_state === "clientwait") {
                $timeout($scope.pollTokenInfo, 2500);
            }
        })
    };

    $scope.regenerateToken = function () {
        var params = $scope.form;
        params.serial = $scope.enrolledToken.serial;
        TokenFactory.enroll($scope.newUser, params, $scope.callback);
    };

    $scope.sendClientPart = function () {
        var params = {
            "otpkey": $scope.clientpart.replace(/ /g, ""),
            "otpkeyformat": "base32check",
            "serial": $scope.enrolledToken.serial,
            "type": $scope.form.type
        };
        TokenFactory.enroll($scope.newUser, params, function (data) {
            $scope.clientpart = "";
            $scope.callback(data);
        });
    };

    // Special Token functions
    $scope.sshkeyChanged = function () {
        var keyArr = $scope.form.sshkey.split(" ");
        $scope.form.description = keyArr.slice(2).join(" ");
    };

    $scope.yubikeyGetLen = function () {
        if ($scope.tempData.yubikeyTest.length >= 32) {
            $scope.form.otplen = $scope.tempData.yubikeyTest.length;
            if ($scope.tempData.yubikeyTest.length > 32) {
                $scope.tempData.yubikeyUid = true;
                $scope.tempData.yubikeyUidLen = $scope.tempData.yubikeyTest.length - 32;
            }
        }
    };

    // U2F
    $scope.register_u2f = function (registerRequest) {
        U2fFactory.register_request(registerRequest, function (params) {
            params.serial = $scope.serial;
            TokenFactory.enroll($scope.newUser,
                params, function (response) {
                    $scope.click_wait = false;
                    $scope.U2FToken.subject = response.detail.u2fRegisterResponse.subject;
                    $scope.U2FToken.vendor = $scope.U2FToken.subject.split(" ")[0];
                    //debug: console.log($scope.U2FToken);
                });
        });
    };

    // get the list of configured RADIUS server identifiers
    $scope.getRADIUSIdentifiers = function() {
        ConfigFactory.getRadius(function(data){
            $scope.radiusIdentifiers = data.result.value;
        });
    };
    $scope.getRADIUSIdentifiers();

    // get the list of configured CA connectors
    $scope.getCAConnectors = function () {
        ConfigFactory.getCAConnectors(function (data){
            var CAConnectors = data.result.value;
            angular.forEach(CAConnectors, function(value, key){
                $scope.CAConnectors.push(value.connectorname);
                $scope.form.ca = value.connectorname;
                $scope.CATemplates[value.connectorname] = value;
            });
            //debug: console.log($scope.CAConnectors);
        });
    };
    $scope.getCAConnectors();

    // If the user is admin, he can read the config.
    ConfigFactory.loadSystemConfig(function (data) {
        /* Default config values like
            radius.server, radius.secret...
           are stored in systemDefault and $scope.form
         */
        var systemDefault = data.result.value;
        //debug: console.log("system default config");
        //debug: console.log(systemDefault);
        // TODO: The entries should be handled automatically.
        var entries = ["radius.server", "radius.secret", "remote.server",
            "radius.identifier",
            "totp.hashlib", "hotp.hashlib", "email.mailserver",
            "email.mailfrom", "yubico.id", "tiqr.regServer"];
        entries.forEach(function(entry) {
            if (!$scope.form[entry]) {
                // preset the UI
                $scope.form[entry] = systemDefault[entry];
            }
        });
        // Default HOTP hashlib
        $scope.form.hashlib = $scope.form["hotp.hashlib"];
        // Now add the questions
        angular.forEach(systemDefault, function(value, key) {
            if (key.indexOf("question.question.") === 0) {
                $scope.questions.push(value);
            }
        });
        $scope.num_answers = systemDefault["question.num_answers"];
        //debug: console.log($scope.questions);
        //debug: console.log($scope.form);
    });

    // open the window to generate the key pair
    $scope.openCertificateWindow = function () {
        var params = {authtoken: AuthFactory.getAuthToken(),
                      ca: $scope.form.ca};
        var tabWindowId = window.open('about:blank', '_blank');
        $http.post(instanceUrl + '/certificate', params).then(
            function (response) {
                //debug: console.log(response);
                tabWindowId.document.write(response.data);
                //tabWindowId.location.href = response.headers('Location');
        });
    };

    // print the paper token
    $scope.printOtp = function () {
        var serial = $scope.enrolledToken.serial;
        var mywindow = window.open('', 'otpPrintingWindow', 'height=400,width=600');
        var css = '<link' +
            ' href="' + instanceUrl +
            '/static/css/papertoken.css"' +
            ' rel="stylesheet">';
        mywindow.document.write('<html><head><title>'+serial+'</title>');
        mywindow.document.write(css);
        mywindow.document.write('</head>' +
            '<body onload="window.print(); window.close()">');
        mywindow.document.write($('#paperOtpTable').html());
        mywindow.document.write('</body></html>');
        mywindow.document.close(); // necessary for IE >= 10
        mywindow.focus(); // necessary for IE >= 10
        return true;
    };

    // ===========================================================
    // ===============  Date stuff ===============================
    // ===========================================================

    $scope.openDate = function($event) {
        $event.stopPropagation();
        return true;
    };

    $scope.today = new Date();
    $scope.dateOptions = {
        formatYear: 'yy',
        startingDay: 1
    };

});


myApp.controller("tokenImportController", function ($scope, $upload,
                                                    AuthFactory, tokenUrl,
                                                    ConfigFactory, inform) {
    $scope.formInit = {
        fileTypes: ["aladdin-xml", "OATH CSV", "Yubikey CSV", "pskc"]
    };
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

    $scope.upload = function (files) {
        if (files && files.length) {
            for (var i = 0; i < files.length; i++) {
                var file = files[i];
                $upload.upload({
                    url: tokenUrl + '/load/filename',
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    fields: {type: $scope.form.type,
                             psk: $scope.form.psk,
                             password: $scope.form.password,
                             tokenrealms: $scope.form.realm},
                    file: file
                }).progress(function (evt) {
                    $scope.progressPercentage = parseInt(100.0 * evt.loaded / evt.total);
                }).success(function (data, status, headers, config) {
                    $scope.uploadedFile = config.file.name;
                    $scope.uploadedTokens = data.result.value;
                }).error(function (error) {
                    if (error.result.error.code === -401) {
                        $state.go('login');
                    } else {
                        inform.add(error.result.error.message,
                                {type: "danger", ttl: 10000});
                    }
                });
            }
        }
    };
});
