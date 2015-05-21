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
                                              $rootScope) {
    $scope.params = {page: 1, sortdir: "asc"};
    $scope.reverse = false;
    $scope.loggedInUser = AuthFactory.getUser();
    $scope.selectedToken = {serial: null};
    // go to the list view by default
    if ($location.path() == "/token") {
        $location.path("/token/list");
    }

    // Change the pagination
    $scope.pageChanged = function () {
        console.log('Page changed to: ' + $scope.params.page);
        $scope.getTokens();
    };

    // This function fills $scope.tokendata
    $scope.getTokens = function () {
        $scope.params.serial = "*" + ($scope.serialFilter || "") + "*";
        $scope.params.type = "*" + ($scope.typeFilter || "") + "*";
        $scope.params.description = "*" + ($scope.descriptionFilter || "") + "*";
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

    $scope.getTokens();

    /*
     * Functions to check and to create a default realm. At the moment this is
     * in the tokenview, as the token view is the first view. This could be
     * changed to be located anywhere else.
     */
    if ($scope.loggedInUser.role == "admin") {
        ConfigFactory.getRealms(function (data) {
            // Check if there is a realm defined, or if we should display the
            // Auto Create Dialog
            number_of_realms = Object.keys(data.result.value).length;
            if (number_of_realms == 0) {
                $('#dialogAutoCreateRealm').modal();
            }
        });
    }

});



myApp.controller("tokenEnrollController", function ($scope, TokenFactory,
                                                    $stateParams, AuthFactory,
                                                    ConfigFactory, instanceUrl,
                                                    $http) {
    $scope.loggedInUser = AuthFactory.getUser();
    $scope.newUser = {};
    $scope.tempData = {};
    $scope.instanceUrl = instanceUrl;
    // System default values for enrollment
    $scope.systemDefault = {};

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
    } else if (AuthFactory.getRole() == 'user') {
        // init the user, if token.enroll was called as a normal user
        $scope.newUser.user = AuthFactory.getUser().username;
        $scope.newUser.realm = AuthFactory.getUser().realm;
    }

    // init the user, if token.enroll was called from the user.details
    if ($stateParams.username) {
        $scope.newUser.user = $stateParams.username;
    }
    if ($stateParams.realmname) {
        $scope.newUser.realm = $stateParams.realmname;
    }
    // TODO: Read this from an object "serverConfig", that is returned
    // after authentication
    $scope.formInit = {
        tokenTypes: {"hotp": "HOTP: event based One Time Passwords",
            "totp": "TOTP: time based One Time Passwords",
            "spass": "SPass: Simple Pass token. Static passwords",
            "motp": "mOTP: classical mobile One Time Passwords",
            "sshkey": "SSH Public Key: The public SSH key",
            "yubikey": "Yubikey AES mode: One Time Passwords with Yubikey",
            "remote": "Remote Token: Forward authentication request to another server",
            "yubico": "Yubikey Cloud mode: Forward authentication request to YubiCloud",
            "radius": "RADIUS: Forward authentication request to a RADIUS server",
            "email": "EMail: Send a One Time Passwort to the users email address",
            "sms": "SMS: Send a One Time Password to the users mobile phone",
            "certificate": "Certificate: Enroll an x509 Certificate Token."},
        timesteps: [30, 60],
        otplens: [6, 8],
        hashlibs: ["sha1", "sha256", "sha512"]
    };

    // These are values that are also sent to the backend!
    $scope.form = {
        timeStep: 30,
        otplen: 6,
        genkey: true,
        type: "hotp",
        hashlib: "sha1"
    };
    $scope.CAConnectors = [];
    $scope.radioCSR = 'csrgenerate';

    $scope.callback = function (data) {
        $scope.enrolledToken = data.detail;
        if ($scope.enrolledToken.certificate) {
            var blob = new Blob([ $scope.enrolledToken.certificate ],
                { type : 'text/plain' });
            $scope.certificateBlob = (window.URL || window.webkitURL).createObjectURL( blob );
        }
    };

    $scope.enrollToken = function () {
        console.log($scope.newUser.user);
        console.log($scope.newUser.realm);
        console.log($scope.newUser.pin);
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
    if ($scope.loggedInUser.role == "admin") {
        ConfigFactory.loadSystemConfig(function (data) {
            /* Default config values like
                radius.server, radius.secret...
             are stored in $scope.systemDefault
             */
            var systemDefault = data.result.value;
            // TODO: The entries should be handled automatically.
            var entries = ["radius.server", "radius.secret", "remote.server",
                "totp.hashlib", "hotp.hashlib"];
            entries.forEach(function(entry) {
                if (!$scope.form[entry]) {
                    $scope.form[entry] = systemDefault[entry];
                }
            });
        });
    }

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
});


myApp.controller("tokenImportController", function ($scope, $upload,
                                                    AuthFactory) {
    $scope.formInit = {
        fileTypes: ["OATH CSV", "Yubikey CSV"]
    };
    // These are values that are also sent to the backend!
    $scope.form = {
        type: "OATH CSV"
    };

    $scope.upload = function (files) {
        if (files && files.length) {
            for (var i = 0; i < files.length; i++) {
                var file = files[i];
                $upload.upload({
                    url: 'token/load/filename',
                    headers: {'Authorization': AuthFactory.getAuthToken()},
                    fields: {type: $scope.form.type},
                    file: file
                }).progress(function (evt) {
                    $scope.progressPercentage = parseInt(100.0 * evt.loaded / evt.total);
                }).success(function (data, status, headers, config) {
                    $scope.uploadedFile = config.file.name;
                    $scope.uploadedTokens = data.result.value;
                }).error(function (error) {
                    if (error.result.error.code == -401) {
                        $state.go('login');
                    } else {
                        addError(error.result.error.message);
                    }
                });
            }
        }
    };
});
