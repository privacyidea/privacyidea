myApp.controller("tokenGetSerialController", function ($scope,
                                                  TokenFactory) {
    $scope.params = {};

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
            "sms": "SMS: Send a One Time Password to the users mobile phone"},
        assigned: {"assigned": "The token is assigned to a user",
            "unassigned": "The token is not assigned to a user",
            "don't care": "It does not matter, if the token is assigned or not"}
    };

    $scope.getSerial = function() {
        $scope.params.assigned = null;
        $scope.params.unassigned = null;
        if ($scope.assigned === "assigned") {
            $scope.params.assigned = 1;
        }
        if ($scope.assigned === "unassigned") {
            $scope.params.unassigned = 1;
        }
        TokenFactory.getserial($scope.otp, $scope.params, function (data) {
            $scope.serial = data.result.value.serial;
            $scope.newOtp = false;
        });
    };
});
