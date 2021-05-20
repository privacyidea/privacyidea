/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2021-04-29 Henning Hollermann <henning.hollermann@netknights.it>
 *     Initial implementation of the token rollover functionality
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

myApp.controller("tokenRolloverController", ["$scope", "TokenFactory", "$timeout",
                                           "$stateParams", "$state", "instanceUrl",
                                           "versioningSuffixProvider",
    function tokenRolloverController($scope, TokenFactory, $timeout,
                                     $stateParams, $state, instanceUrl,
                                     versioningSuffixProvider) {

    $scope.tokenSerial = $stateParams.tokenSerial;
    $scope.qrCodeWidth = "250";
    $scope.fileVersionSuffix = versioningSuffixProvider.$get();

    // scroll to the top of the page
    document.body.scrollTop = document.documentElement.scrollTop = 0;

    // define functions
    $scope.get = function () {
        TokenFactory.getTokenForSerial($scope.tokenSerial, function (data) {
            $scope.token = data.result.value.tokens[0];
        });
    }

    $scope.getAndRegenerateToken = function () {
        TokenFactory.getTokenForSerial($scope.tokenSerial, function (data) {
            $scope.token = data.result.value.tokens[0];
            $scope.regenerateToken();
        });
    };

    $scope.regenerateToken = function () {
        var params = $scope.token;
        params.type = params.tokentype
        // force server key generation (HOTP, TOTP)
        params.genkey = true;
        // use 2stepinit if preferred
        params["2stepinit"] = $scope.checkRight(params.type + "_2step=force");
        if (!$scope.form) { $scope.form = {}; };
        $scope.form["2stepinit"] = params["2stepinit"];
        // enroll token using the current serial, type and options
        TokenFactory.enroll({}, params, $scope.callback);
    };

    // enrollment callback supports totp, hotp, push, paper, tan, registration
    $scope.callback = function (data) {
        $scope.enrolledToken = data.detail;
        if ($scope.enrolledToken.otps) {
            var otps_count = Object.keys($scope.enrolledToken.otps).length;
            $scope.otp_row_count = parseInt(otps_count/5 + 0.5);
            $scope.otp_rows = Object.keys($scope.enrolledToken.otps).slice(0, $scope.otp_row_count);
        }
        if ($scope.enrolledToken.rollout_state === "clientwait") {
            $scope.pollTokenInfo();
        }
        $('html,body').scrollTop(0);
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

    $scope.sendClientPart = function () {
        var params = {
            "otpkey": $scope.clientpart.replace(/ /g, ""),
            "otpkeyformat": "base32check",
            "serial": $scope.token.serial,
            "type": $scope.token.tokentype
        };
        TokenFactory.enroll({}, params, function (data) {
            $scope.clientpart = "";
            $scope.callback(data);
        });
    };

    // regenerate the token given by serial
    $scope.getAndRegenerateToken();

}]);