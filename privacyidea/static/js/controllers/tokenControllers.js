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
myApp.controller("tokenController", function (TokenFactory, ConfigFactory, $scope, $location, AuthFactory) {
    $scope.params = {page: 1, sortdir: "asc"};
    $scope.reverse = false;
    $scope.loggedInUser = AuthFactory.getUser();
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

    // Get the realms and fill the realm dropdown box
    if (AuthFactory.getRole() == 'admin') {
        ConfigFactory.getRealms(function (data) {
            $scope.realms = data.result.value;
            angular.forEach($scope.realms, function (realm, realmname) {
                if (realm.default) {
                    // Set the default realm
                    $scope.defaultRealm = realmname;
                }
            });
        });
    }
});


    myApp.controller("tokenDetailController", function ($scope,
                                                    TokenFactory, UserFactory,
                                                    $stateParams,
                                                    $state, $rootScope,
                                                    ValidateFactory,
                                                    AuthFactory) {
    $scope.tokenSerial = $stateParams.tokenSerial;
    $scope.editCountWindow = false;
    $scope.selectedRealms = {};
    $scope.newUser = {user: "", realm: $scope.defaultRealm};
    $scope.loggedInUser = AuthFactory.getUser();
    // scroll to the top of the page
    document.body.scrollTop = document.documentElement.scrollTop = 0;

    $scope.get = function () {
        TokenFactory.getTokenForSerial($scope.tokenSerial, function (data) {
            $scope.token = data.result.value.tokens[0];
        });
    };

    $scope.return_to = function () {
        // After deleting the token, we return here.
        // history.back();
        $state.go($rootScope.previousState.state,
            $rootScope.previousState.params);
    };

    $scope.unassign = function () {
        if ($scope.loggedInUser.role == 'user') {
            TokenFactory.unassign($scope.tokenSerial, $state.go('token.list'));
        } else {
            TokenFactory.unassign($scope.tokenSerial, $scope.get);
        }
    };

    $scope.enable = function () {
        TokenFactory.enable($scope.tokenSerial, $scope.get);
    };

    $scope.disable = function () {
        TokenFactory.disable($scope.tokenSerial, $scope.get);
    };

    $scope.set = function (key, value) {
        TokenFactory.set($scope.tokenSerial, key, value, $scope.get);
    };
    $scope.reset = function () {
        TokenFactory.reset($scope.tokenSerial, $scope.get);
    };

    $scope.get();

    $scope.startEditRealm = function () {
        // fill the selectedRealms with the realms of the token
        $scope.selectedRealms = {};
        $scope.editTokenRealm = true;
        angular.forEach($scope.token.realms, function (realmname, _index) {
            $scope.selectedRealms[realmname] = true;
        })
    };

    $scope.cancelEditRealm = function () {
        $scope.editTokenRealm = false;
        $scope.selectedRealms = {};
    };

    $scope.saveRealm = function () {
        console.log(Object.keys($scope.selectedRealms));
        TokenFactory.setrealm($scope.tokenSerial, Object.keys($scope.selectedRealms), $scope.get);
        $scope.cancelEditRealm();
    };

    $scope.assignUser = function () {
        TokenFactory.assign({
            serial: $scope.tokenSerial,
            user: fixUser($scope.newUser.user),
            realm: $scope.newUser.realm,
            pin: $scope.newUser.pin
        }, $scope.get);
    };

    $scope.delete = function () {
        TokenFactory.delete($scope.tokenSerial, $scope.return_to);
    };

    $scope.setPin = function () {
        TokenFactory.setpin($scope.tokenSerial, "otppin",
            $scope.pin1, function () {
                $scope.pin1 = "";
                $scope.pin2 = "";
            });
    };

    $scope.resyncToken = function () {
        TokenFactory.resync({
            serial: $scope.tokenSerial,
            otp1: $scope.otp1,
            otp2: $scope.otp2
        }, function (data) {
            $scope.otp1 = "";
            $scope.otp2 = "";
            $scope.resultResync = data.result.value;
            $scope.get();
        });
    };

    $scope.testOtp = function () {
        ValidateFactory.check({
            serial: $scope.tokenSerial,
            pass: $scope.testPassword
        }, function (data) {
            $scope.resultTestOtp  = {result:data.result.value,
                                     detail:data.detail.message};
            $scope.get();
        });
    };

});

myApp.controller("tokenEnrollController", function ($scope, TokenFactory,
                                                    $stateParams, AuthFactory) {
    $scope.loggedInUser = AuthFactory.getUser();
    $scope.newUser = {};
    $scope.tempData = {};
    // init the user, if token.enroll was called as a normal user
    if (AuthFactory.getRole() == 'user') {
        $scope.newUser.user = AuthFactory.getUser().username;
        $scope.newUser.realm = AuthFactory.getUser().realm;
    } else {
        // init the username with default realm
        $scope.newUser = {user: "", realm: $scope.defaultRealm};
        console.log("tokenEnrollController");
        console.log($scope.newUser);
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
            "radius": "RADIUS: Forward authentication request to a RADIUS server"},
        timesteps: [30, 60],
        otplens: [6, 8],
        hashlibs: ["sha1", "sha256", "sha512"]
    };
    // These are values that are also sent to the backend!
    $scope.form = {
        timestep: 30,
        otplen: 6,
        genkey: true,
        type: "hotp",
        hashlib: "sha1"
    };

    $scope.callback = function (data) {
        $scope.enrolledToken = data.detail;
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
});


myApp.controller("tokenImportController", function ($scope) {
    $scope.formInit = {
        fileTypes: ["OATH CSV", "Yubikey CSV"]
    };
    // These are values that are also sent to the backend!
    $scope.form = {
        type: "OATH CSV"
    };
});
