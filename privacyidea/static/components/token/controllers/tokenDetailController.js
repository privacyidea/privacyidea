
function date_object_to_string(date_obj) {
    var s = "";
    if (date_obj) {
        var Y = date_obj.getFullYear();
        var D = date_obj.getDate();
        D = (D>9 ? '' : '0') + D;
        var M = date_obj.getMonth()+1;
        M = (M>9 ? '' : '0') + M;
        var h = date_obj.getHours();
        h = (h>9 ? '' : '0') + h;
        var m = date_obj.getMinutes();
        m = (m>9 ? '' : '0') + m;

        var tz = date_obj.getTimezoneOffset();
        var tz_abs = Math.abs(tz);
        var hours = Math.floor(tz_abs/60);
        hours = (hours>9 ? '': '0') + hours;
        var minutes = tz_abs % 60;
        minutes = (minutes>9 ? '': '0') + minutes;
        var sign = "-";
        if (tz < 0) {
            // The offset for +0100 is -60!
            sign = "+";
        }
        var o = sign + hours + minutes;
        s = Y + "-" + M + "-" + D + "T" + h + ":" + m + o;
    }
    return s;
}

function string_to_date_object(s) {
    date_obj = null;
    if (s) {
        if (s.substring(2, 3) === "/") {
            var day = s.substring(0, 2);
            var month = s.substring(3, 5);
            var rest = s.substring(6);
            s = month + "/" + day + "/" + rest;
        }
        var date_obj = new Date();
        var d = Date.parse(s);
        date_obj.setTime(d);
    }
    return date_obj;
}

myApp.controller("tokenDetailController", function ($scope,
                                                    TokenFactory, UserFactory,
                                                    $stateParams,
                                                    $state, $rootScope,
                                                    ValidateFactory,
                                                    AuthFactory,
                                                    ConfigFactory,
                                                    MachineFactory, inform,
                                                    gettextCatalog) {
    $scope.tokenSerial = $stateParams.tokenSerial;
    // This is the parents object
    $scope.selectedToken.serial = $scope.tokenSerial;
    $scope.editCountWindow = false;
    $scope.selectedRealms = {};
    $scope.newUser = {user: "", realm: $scope.defaultRealm};
    $scope.loggedInUser = AuthFactory.getUser();
    $scope.machinesPerPage = 15;
    $scope.params = {page: 1};
    $scope.form = {options: {}};
    $scope.testTokenPlaceholder = gettextCatalog.getString('Enter PIN and OTP to check the' +
        ' token.');
    ConfigFactory.getSystemConfig(function(data) {
        prepend = data.result.value.PrependPin;
        //debug: console.log(prepend);
        if (!$scope.isChecked(prepend)) {
            $scope.testTokenPlaceholder = gettextCatalog.getString('Enter OTP + PIN to' +
                ' check the token.');
        }
    });
    // scroll to the top of the page
    document.body.scrollTop = document.documentElement.scrollTop = 0;


    // define functions
    $scope.get = function () {
        TokenFactory.getTokenForSerial($scope.tokenSerial, function (data) {
            $scope.token = data.result.value.tokens[0];
            $scope.max_auth_count = parseInt($scope.token.info.count_auth_max);
            $scope.max_success_auth_count = parseInt($scope.token.info.count_auth_success_max);
            $scope.validity_period_start = string_to_date_object($scope.token.info.validity_period_start);
            $scope.validity_period_end = string_to_date_object($scope.token.info.validity_period_end);
            //debug: console.log($scope.token);
            // Add a certificateBlob, if it exists
            if ($scope.token.info.certificate) {
                var blob = new Blob([ $scope.token.info.certificate ],
                    { type : 'text/plain' });
                $scope.certificateBlob = (window.URL || window.webkitURL).createObjectURL( blob );
            }
            if ($scope.token.info.pkcs12) {
                var bytechars = atob($scope.token.info.pkcs12);
                var byteNumbers = new Array(bytechars.length);
                for (var i = 0; i < bytechars.length; i++) {
                    byteNumbers[i] = bytechars.charCodeAt(i);
                }
                var byteArray = new Uint8Array(byteNumbers);
                var blob = new Blob([byteArray], {type: 'application/x-pkcs12'});
                $scope.pkcs12Blob = (window.URL || window.webkitURL).createObjectURL( blob );
            }
        });
    };

    // initialize
    $scope.get();


    $scope.return_to = function () {
        // After deleting the token, we return here.
        // history.back();
        $state.go($rootScope.previousState.state,
            $rootScope.previousState.params);
    };

    $scope.unassignAskAdmin = function() {
        $scope.confirm(
            $scope.confirm_action_levels["easy"],
            "Unassign Token",
            "Do you really want to remove this token from this users account?",
            "Unassign",
            $scope.unassign);
    };

    $scope.unassignAskUser = function() {
        $scope.confirm(
            $scope.confirm_action_levels["difficult"],
            "Unassign Token",
            "Do you really want to remove this token from your account?",
            "Unassign",
            $scope.unassign);
    };

    $scope.unassign = function () {
        if ($scope.loggedInUser.role === 'user') {
            TokenFactory.unassign($scope.tokenSerial, $state.go('token.list'));
        } else {
            TokenFactory.unassign($scope.tokenSerial, $scope.get);
        }
    };

    $scope.enableAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["always"],
            "Enable Token",
            "Do you want to enable this token?",
            "Enable Token",
            $scope.enable);
    };

    $scope.enable = function () {
        TokenFactory.enable($scope.tokenSerial, $scope.get);
    };

    $scope.disableAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["easy"],
            "Disable Token",
            "Do you really want to disable this token?",
            "Disable Token",
            $scope.disable);
    };

    $scope.disable = function () {
        TokenFactory.disable($scope.tokenSerial, $scope.get);
    };

    $scope.revokeAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["difficult"],
            "Revoke Token",
            "Do you really want to revoke this token?",
            "Revoke Token",
            $scope.revoke);
    };

    $scope.revoke = function () {
        TokenFactory.revoke($scope.tokenSerial, $scope.get);
    };

    $scope.set = function (key, value) {
        TokenFactory.set($scope.tokenSerial, key, value, $scope.get);
    };

    $scope.setdescription = function (description) {
        TokenFactory.set_description($scope.tokenSerial, description, $scope.get);
    };

    $scope.resetAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["always"],
            "Reset Fail Counter",
            "Do you want to reset the fail counter for this token?",
            "Reset",
            $scope.reset);
    };

    $scope.reset = function () {
        TokenFactory.reset($scope.tokenSerial, $scope.get);
    };

    $scope.startEditRealm = function () {
        // fill the selectedRealms with the realms of the token
        $scope.selectedRealms = {};
        $scope.editTokenRealm = true;
        angular.forEach($scope.token.realms, function (realmname, _index) {
            $scope.selectedRealms[realmname] = true;
        });
    };

    $scope.cancelEditRealm = function () {
        $scope.editTokenRealm = false;
        $scope.selectedRealms = {};
    };

    $scope.saveRealmAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["easy"],
            "Edit Token Realm",
            "Do you want to apply your changes to the realm assignments for this token?",
            "Save Realm",
            $scope.saveRealm);
    };

    $scope.saveRealm = function () {
        var realms = [];
        for (var realm in $scope.selectedRealms) {
            if ($scope.selectedRealms[realm] === true) {
                realms.push(realm);
            }
        }
        TokenFactory.setrealm($scope.tokenSerial, realms, $scope.get);
        $scope.cancelEditRealm();
    };

    $scope.saveTokenInfoAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["difficult"],
            "Edit Token Information",
            "Do you want to apply your changes the information for this token?",
            "Save Token Info",
            function() {
                $scope.editTokenInfo = 0;
                $scope.saveTokenInfo();
            });
    };

    $scope.saveTokenInfo = function () {
        var start = date_object_to_string($scope.validity_period_start);
        var end = date_object_to_string($scope.validity_period_end);
        TokenFactory.set_dict($scope.tokenSerial,
            {count_auth_max: $scope.max_auth_count,
             count_auth_success_max: $scope.max_success_auth_count,
             validity_period_end: end,
             validity_period_start: start},
            $scope.get);
    };

    $scope.assignUserAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["always"],
            "Assign User",
            "Do you really want to assign the user to this token?",
            "Assign",
            $scope.assignUser);
    };

    $scope.assignUser = function () {
        TokenFactory.assign({
            serial: $scope.tokenSerial,
            user: fixUser($scope.newUser.user),
            realm: $scope.newUser.realm,
            pin: $scope.newUser.pin
        }, $scope.get);
    };

    $scope.deleteAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["severe"],
            "Delete Token",
            "Are you sure you want to delete this token? CAUTION: THIS MAY BE DIFFICULT OR IMPOSSIBLE TO REVERT!",
            "Yes, really delete this token!",
            $scope.delete);
    };

    $scope.delete = function () {
        TokenFactory.delete($scope.tokenSerial, $scope.return_to);
    };

    $scope.setRandomPinAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["difficult"],
            "Set Random Token PIN",
            "Dou you really want to change the PIN for this token?",
            "Set PIN",
            $scope.setRandomPin);
    };

    $scope.setRandomPin = function () {
        TokenFactory.setrandompin($scope.tokenSerial, function (data) {
                if (data.result.value >= 1) {
                    inform.add(gettextCatalog.getString("PIN set successfully."),
                        {type: "info", ttl: 5000})
                } else {
                    inform.add(gettextCatalog.getString("Failed to set PIN."),
                        {type: "danger", ttl: 10000})
                }
                $scope.randomPin = data.detail.pin;
            });
    };

    $scope.setPinAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["difficult"],
            "Set Token PIN",
            "Dou you really want to change the PIN for this token?",
            "Set PIN",
            $scope.setPin);
    };

    $scope.setPin = function () {
        TokenFactory.setpin($scope.tokenSerial, "otppin",
            $scope.pin1, function (data) {
                if (data.result.value >= 1) {
                    inform.add(gettextCatalog.getString("PIN set successfully."),
                        {type: "info", ttl: 5000})
                } else {
                    inform.add(gettextCatalog.getString("Failed to set PIN."),
                        {type: "danger", ttl: 10000})
                }
                $scope.pin1 = "";
                $scope.pin2 = "";
                // in case of certificate tokens we need to reread the token
                // information. Since the PKCS12 is encrypted with the new PIN.
                if ($scope.token.tokentype === "certificate") {
                    $scope.get();
                }
            });
    };

    $scope.resyncTokenAsk = function() {
        $scope.confirm(
            $scope.confirm_action_levels["always"],
            "Resync Token",
            "Do you want to resync this token using the OTP value you entered?",
            "Resync Token",
            $scope.resyncToken);
    };

    $scope.resyncToken = function () {
        TokenFactory.resync({
            serial: $scope.tokenSerial,
            otp1: $scope.otp1,
            otp2: $scope.otp2
        }, function (data) {
            $scope.otp1 = "";
            $scope.otp2 = "";
            if (data.result.value === true) {
                inform.add(gettextCatalog.getString("Token resync successful."),
                                {type: "info", ttl: 10000});
            } else {
                inform.add(gettextCatalog.getString("Token resync failed."),
                                {type: "danger", ttl: 10000});
            }
            $scope.get();
        });
    };

    $scope.testOtp = function (otponly) {
        var params = {
            serial: $scope.tokenSerial,
            pass: $scope.testPassword
        };
        if (otponly) {
            params["otponly"] = "1";
        }
        ValidateFactory.check(params, function (data) {
            //debug: console.log(data);
            // refresh the token data
            $scope.get();
            if (data.result.value === true) {
                inform.add(gettextCatalog.getString("Successfully authenticated."),
                    {type: "success", ttl: 10000});
            } else {
                inform.add(data.detail.message,
                    {type: "danger", ttl: 10000});
            }
        });
    };

    //----------------------------------------------------------------
    //   Admin functions
    //

    if ($scope.loggedInUser.role === "admin") {
        // These are functions that can only be used by administrators.
        // If the user is admin, we can fetch all realms
        // If the loggedInUser is only a user, we do not need the realm list,
        // as we do not assign a token
        ConfigFactory.getRealms(function (data) {
                $scope.realms = data.result.value;
        });

        $scope.attachMachineAsk = function() {
            $scope.confirm(
                $scope.confirm_action_levels["always"],
                "Attach Machine to Token",
                "Are you sure you want to attach the machine to this token?",
                "Attach Machine",
                $scope.attachMachine);
        };

        $scope.attachMachine = function () {
            // newToken.serial, application
            var params = $scope.form.options;
            // First we set all the application specific option than add the
            // needed standard values
            var machineObject = fixMachine($scope.newMachine);
            params["serial"] = $scope.tokenSerial;
            params["application"] = $scope.form.application;
            params["machineid"] = machineObject.id;
            params["resolver"] = machineObject.resolver;
            MachineFactory.attachTokenMachine(params, function (data) {
                // clear form
                $scope.form.application = null;
                $scope.newToken = null;
                $scope.form.options = {};
                $scope.getMachines();
            });
        };

        $scope.detachMachineTokenAsk = function(machineid, resolver, application) {
            $scope.confirm(
                $scope.confirm_action_levels["easy"],
                "Detach Machine from Token",
                "Do you really want to detach the machine from this token?",
                "Detach Machine",
                function() {
                    $scope.detachMachineToken(machineid, resolver, application);
                });
        };

        $scope.detachMachineToken = function (machineid, resolver, application) {
            MachineFactory.detachTokenMachine({serial: $scope.tokenSerial,
                    application: application,
                    machineid: machineid,
                    resolver: resolver
            }, function (data) {
                $scope.getMachines();
            });
        };

        $scope.saveOptionsAsk = function(machineid, resolver, application, options) {
            $scope.confirm(
                $scope.confirm_action_levels["difficult"],
                "Save Machine Options",
                "Do you want to apply the changes you have made to the options for this machine?",
                "Save Options",
                function() {
                    $scope.saveOptions(machineid, resolver, application, options);
                    $scope.machine.optionsEdit = false;
                });
        };

        $scope.saveOptions = function(machineid, resolver, application, options) {
            var params = options;
            params["machineid"] = machineid;
            params["resolver"] = resolver;
            params["serial"] = $scope.tokenSerial;
            params["application"] = application;
            MachineFactory.saveOptions(params, function (data) {
                $scope.getMachines();
                //debug: console.log(data);
            });
        };

        $scope.getMachines = function () {
            MachineFactory.getMachineTokens({serial: $scope.tokenSerial},
                    function (data) {
                        machinelist = data.result.value;
                        //debug: console.log(machinelist);
                        $scope.machineCount = machinelist.length;
                        var start = ($scope.params.page - 1) * $scope.machinesPerPage;
                        var stop = start + $scope.machinesPerPage;
                        $scope.machinedata = machinelist.slice(start, stop);
                    });
        };
        // Change the pagination
        $scope.pageChanged = function () {
            //debug: console.log('Page changed to: ' + $scope.params.page);
            $scope.getMachines();
        };

        if (AuthFactory.checkRight("manage_machine_tokens")) {
            // read the application definition from the server
            MachineFactory.getApplicationDefinition(function (data) {
                $scope.Applications = data.result.value;
                var applications = [];
                for (var k in $scope.Applications) applications.push(k);
                $scope.formInit = {application: applications};
            });
            $scope.getMachines();
        }

    }  // End of admin functions


    // ===========================================================
    // =============== Tokeninfo Date stuff ======================
    // ===========================================================

    $scope.openDate = function($event) {
        $event.preventDefault();
        $event.stopPropagation();
        return true;
    };

    // listen to the reload broadcast
    $scope.$on("piReload", $scope.get);


});
