
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

myApp.controller("tokenDetailController", ['$scope', 'TokenFactory',
                                           'UserFactory', '$stateParams',
                                           '$state', '$rootScope',
                                           'ValidateFactory', 'AuthFactory',
                                           'ConfigFactory', 'MachineFactory',
                                           'inform', 'gettextCatalog',
                                           function ($scope, TokenFactory,
                                                     UserFactory, $stateParams,
                                                     $state, $rootScope,
                                                     ValidateFactory,
                                                     AuthFactory, ConfigFactory,
                                                     MachineFactory, inform,
                                                     gettextCatalog) {
    $scope.tokenSerial = $stateParams.tokenSerial;
    // This is the parents object
    $scope.selectedToken.serial = $scope.tokenSerial;
    $scope.editCountWindow = false;
    $scope.selectedRealms = {};
    $scope.selectedTokenGroups = {};
    $scope.newUser = {user: "", realm: $scope.defaultRealm};
    $scope.loggedInUser = AuthFactory.getUser();
    $scope.machinesPerPage = 15;
    $scope.params = {page: 1};
    $scope.form = {options: {}};
    $scope.editTokenInfo = 0;
    $scope.pin1 = $scope.pin2 = "";
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

    $scope.unassign = function () {
        if ($scope.loggedInUser.role === 'user') {
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
    $scope.revoke = function () {
        TokenFactory.revoke($scope.tokenSerial, $scope.get);
    };
    $scope.set = function (key, value) {
        TokenFactory.set($scope.tokenSerial, key, value, $scope.get);
    };
    $scope.setdescription = function (description) {
        TokenFactory.set_description($scope.tokenSerial, description, $scope.get);
    };
    $scope.reset = function () {
        TokenFactory.reset($scope.tokenSerial, $scope.get);
    };

    $scope.startEditTokenGroups = function() {
        // fill the selectedTokenGroups with the groups of the token
        $scope.selectedTokenGroups = {};
        $scope.editTokenGroups = true;
        angular.forEach($scope.token.tokengroup, function (groupname, _index) {
            $scope.selectedTokenGroups[groupname] = true;
        });
    };

    $scope.startEditRealm = function () {
        // fill the selectedRealms with the realms of the token
        $scope.selectedRealms = {};
        $scope.editTokenRealm = true;
        angular.forEach($scope.token.realms, function (realmname, _index) {
            $scope.selectedRealms[realmname] = true;
        });
    };

    $scope.cancelEditTokenGroups = function () {
        $scope.editTokenGroups = false;
        $scope.selectedTokenGroups = {};
    }

    $scope.cancelEditRealm = function () {
        $scope.editTokenRealm = false;
        $scope.selectedRealms = {};
    };

    $scope.saveTokenGroups = function () {
        var tokengroups = [];
        for (var tokengroup in $scope.selectedTokenGroups) {
            if ($scope.selectedTokenGroups[tokengroup] === true) {
                tokengroups.push(tokengroup);
            }
        }
        TokenFactory.settokengroups($scope.tokenSerial, tokengroups, $scope.get);
        $scope.cancelEditTokenGroups();
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

    $scope.startEditTokenInfo = function() {
        $scope.validity_period_start = string_to_date_object($scope.token.info.validity_period_start);
        $scope.validity_period_end = string_to_date_object($scope.token.info.validity_period_end);
        $scope.editTokenInfo = 1;
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
        $scope.editTokenInfo = 0;
    };

    $scope.assignUser = function () {
        TokenFactory.assign({
            serial: $scope.tokenSerial,
            user: fixUser($scope.newUser.user),
            realm: $scope.newUser.realm,
            pin: $scope.newUser.pin
        }, $scope.get);
    };

    $scope.deleteTokenAsk = function() {
        var tokenType = $scope.token.info.tokenkind;
        if (tokenType == "hardware"){
            $('#dialogTokenDelete').modal();
        } else {
            $scope.delete();
        };
     };


    $scope.delete = function () {
        TokenFactory.delete($scope.tokenSerial, $scope.return_to);
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

    $scope.sendVerifyResponse = function () {
        var params = {
            "serial": $scope.token.serial,
            "verify": $scope.token.verifyResponse,
            "type": $scope.token.tokentype
        };
        TokenFactory.enroll($scope.newUser, params, function (data) {
            $scope.token.verifyResponse = "";
            if (data.result.value === true) {
                inform.add(gettextCatalog.getString("Enrollment successfully verified."),
                                {type: "info", ttl: 10000});
            } else {
                inform.add(gettextCatalog.getString("Enrollment verification failed."),
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

        if (AuthFactory.checkRight("tokengroup_list")) {
            ConfigFactory.getTokengroup("", function (data) {
                $scope.tokengroups = data.result.value;
            });
        }

        $scope.attachMachine = function () {
            // newToken.serial, application
            var params = $scope.form.options;
            // First we set all the application specific option than add the
            // needed standard values
            var machineObject = fixMachine($scope.newMachine);
            params["serial"] = $scope.tokenSerial;
            params["application"] = $scope.form.application;
            if ($scope.form.application === "offline") {
                // We force to be not attached to a machine
                params["machineid"] = 0;
                params["resolver"] = "";
            } else {
                params["machineid"] = machineObject.id;
                params["resolver"] = machineObject.resolver;
            }
            MachineFactory.attachTokenMachine(params, function (data) {
                // clear form
                $scope.form.application = null;
                $scope.newToken = null;
                $scope.form.options = {};
                $scope.getMachines();
            });
        };

        $scope.detachMachineToken = function (application, mtid) {
            MachineFactory.detachTokenMachine({serial: $scope.tokenSerial,
                    application: application,
                    mtid: mtid
            }, function (data) {
                $scope.getMachines();
            });
        };

        $scope.saveOptions = function(mtid, options) {
            var params = options;
            params["mtid"] = mtid;
            MachineFactory.saveOptions(params, function (data) {
                $scope.getMachines();
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

    $scope.rolloverTokenAllowed = function(token) {
        if ( typeof(token) != 'undefined' ) {
            if ($scope.checkEnroll() && (token.tokentype in $scope.token_rollover) &&
                token.info.tokenkind === 'software') {
                return true;
            }
        }
        return false;
    };


}]);
