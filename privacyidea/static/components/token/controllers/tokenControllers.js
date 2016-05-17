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
    // go to the list view by default
    if ($location.path() == "/token") {
        $location.path("/token/list");
    }
    // go to token.wizard, if the wizard is defined
    if ($scope.token_wizard) {
        $location.path("/token/wizard");
    }

    // Change the pagination
    $scope.pageChanged = function () {
        console.log('Page changed to: ' + $scope.params.page);
        $scope.get();
    };

    // This function fills $scope.tokendata
    $scope.get = function () {
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
            $scope.tokendata = data.result.value;
            console.log($scope.tokendata);
        }, $scope.params);
    };

    $scope.get();

    /*
     * Functions to check and to create a default realm. At the moment this is
     * in the tokenview, as the token view is the first view. This could be
     * changed to be located anywhere else.
     */
    if ($scope.loggedInUser.role == "admin") {
        ConfigFactory.getRealms(function (data) {
            // Check if there is a realm defined, or if we should display the
            // Auto Create Dialog
            var number_of_realms = Object.keys(data.result.value).length;
            if (number_of_realms == 0) {
                $('#dialogAutoCreateRealm').modal();
            }
        });
    }

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
    if ($state.includes('token.wizard')) {
        $scope.qrCodeWidth = 500;
    }
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

    // These token need to PIN
    // TODO: This is also contained in the tokentype class!
    $scope.changeTokenType = function() {
        console.log("Token Type Changed.");
        if (["sshkey", "certificate"].indexOf($scope.form.type) >= 0) {
            $scope.hidePin = true;
        } else {
            $scope.hidePin = false;
        }
    };

    // A watch function to change the form data in case another user is selected
    $scope.$watch(function(scope) {return scope.newUser.email;},
        function(newValue, oldValue){
            $scope.form.email = newValue;
        });
    $scope.$watch(function(scope) {return scope.newUser.mobile;},
        function(newValue, oldValue){
            $scope.form.phone = newValue;
        });

    // Get the realms and fill the realm dropdown box
    if (AuthFactory.getRole() == 'admin') {
        ConfigFactory.getRealms(function (data) {
            $scope.realms = data.result.value;
            angular.forEach($scope.realms, function (realm, realmname) {
                if (realm.default && !$stateParams.realmname) {
                    // Set the default realm
                    $scope.newUser = {user: "", realm: realmname};
                    console.log("tokenEnrollController");
                    console.log($scope.newUser);
                }
            });
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
    } else if (AuthFactory.getRole() == 'user') {
        // init the user, if token.enroll was called as a normal user
        $scope.newUser.user = AuthFactory.getUser().username;
        $scope.newUser.realm = AuthFactory.getUser().realm;
    }

    // Read the the tokentypes from the server
    TokenFactory.getEnrollTokens(function(data){
        console.log(data);
        $scope.formInit["tokenTypes"] = data.result.value;
        // set the default tokentype
        if (!$scope.formInit.tokenTypes.hasOwnProperty("hotp")) {
            // if HOTP does not exist, we set another default type
            for (var tkey in $scope.formInit.tokenTypes) {
                // set the first key to be the default tokentype
                $scope.form.type = tkey;
                break;
            }
        }
    });

    $scope.CAConnectors = [];
    $scope.radioCSR = 'csrgenerate';


    // default enrollment callback
    $scope.callback = function (data) {
        $scope.U2FToken = {};
        $scope.enrolledToken = data.detail;
        $scope.click_wait=false;
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
    };

    $scope.enrollToken = function () {
        console.log($scope.newUser.user);
        console.log($scope.newUser.realm);
        console.log($scope.newUser.pin);
        $scope.newUser.user = fixUser($scope.newUser.user);
        TokenFactory.enroll($scope.newUser,
            $scope.form, $scope.callback);
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
                    console.log($scope.U2FToken);
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
            });
            console.log($scope.CAConnectors);
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
        console.log("system default config");
        console.log(systemDefault);
        // TODO: The entries should be handled automatically.
        var entries = ["radius.server", "radius.secret", "remote.server",
            "radius.identifier",
            "totp.hashlib", "hotp.hashlib", "email.mailserver",
            "email.mailfrom", "sms.Provider", "yubico.id", "tiqr.regServer"];
        entries.forEach(function(entry) {
            if (!$scope.form[entry]) {
                // preset the UI
                $scope.form[entry] = systemDefault[entry];
            }
        });
        // Now add the questions
        angular.forEach(systemDefault, function(value, key) {
            if (key.indexOf("question.question.") === 0) {
                $scope.questions.push(value);
            }
        });
        $scope.num_answers = systemDefault["question.num_answers"];
        console.log($scope.questions);
        console.log($scope.form);
    });

    // open the window to generate the key pair
    $scope.openCertificateWindow = function () {
        var params = {authtoken: AuthFactory.getAuthToken(),
                      ca: $scope.form.ca};
        var tabWindowId = window.open('about:blank', '_blank');
        $http.post(instanceUrl + '/certificate', params).then(
            function (response) {
                console.log(response);
                tabWindowId.document.write(response.data);
                //tabWindowId.location.href = response.headers('Location');
        });
    };

    // print the paper token
    $scope.printOtp = function () {
        var serial = $scope.enrolledToken.serial;
        var mywindow = window.open('', 'otpPrintingWindow', 'height=400,width=600');
        var link1 = '<link' +
            ' href="' + instanceUrl +
            '/static/contrib/css/bootstrap.css" rel="stylesheet">';
        var link2 = '<link' +
            ' href="' + instanceUrl +
            '/static/contrib/css/bootstrap-theme.css"' +
            ' rel="stylesheet">';

        console.log(link1);
        console.log(link2);
        mywindow.document.write('<html><head><title>'+serial+'</title>');
        /*
        TODO: In certain cases (https/instance) the links lead to blank pages!
        mywindow.document.write(link1);
        mywindow.document.write(link2);
        */
        mywindow.document.write('</head><body><h1>'+serial+'</h1>');
        mywindow.document.write($('#paperOtpTable').html());
        mywindow.document.write('</body></html>');
        mywindow.document.close(); // necessary for IE >= 10
        mywindow.focus(); // necessary for IE >= 10
        mywindow.print();
        mywindow.close();
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
