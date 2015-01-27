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
    $scope.formInit = {
        tokenTypes: ["hotp", "totp", "spass"],
        timesteps: [30, 60], otplens: [6, 8]
    };
    // These are values that are also sent to the backend!
    $scope.form = {
        timestep: 30,
        otplen: 6,
        generate: true,
        type: "hotp"
    };

    $scope.callback = function (data) {
        $scope.enrolledToken = data.detail;
        $scope.qrcode = $scope.enrolledToken.googleurl.img;
        $scope.image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAcIAAAHCAQAAAABUY/ToAAADsUlEQVR4nO2cW4rjOhCGvzo25FGGXkCWYu9s6CXNDuKl9AIarMeAzH8eJNlK0g3DTIfuhKoH44s+ZIEo1U0y8Xcy//eXIDjppJNOOumkk07+PNKK9NgUzWyKPTax5re5yRRrq+mb/9bJH0mOkqQFmIdOEM6m1wGkBcyG1YBOkqRL8jv+1skfScaqX8bl4vt8TOgUD9IJMLP+6/p08jnI/upZRNBsnSAess4xwoKNv7+qTyefm7QpJOyXEoxK2ESXVdAd+3Tyscmqh4KACCK+JObhvc86aPxtCKqC+pI+nXxKcjYzswFsAhjfDrIp9gCd7NfbjZv2oON08g5k1kO7fhFxNc0DxjxgwFov4TIt8ljjdPJ+JNldH5XqiyCx+fE60Sl7/qcgZa8tPz7WOJ28H0mZK0vXzJIyc5YtIBRSE0Iqk+uxxunk/cg6I0JCWrqqkUK9jEowLkUZ7Xc+h5ysUvyy8a0nR6cBRDzIbtquPcU8+rc+nXxGMkeFzA6yKb9fLS9oADqFszFbz/7uMcfp5D3IupZBtXga+3mbQ7ndtrT5WubkB2RIQNyCP7GsccVrW8BsAGbPlzl5I40LT5CqulE1ndknUtc8uh5ycpPqve9uPUBI2fZpDaD8zueQk9fSKJkiafP3a01RllD0lc8hJy9lt6lLADFfqjmd51BIWzxbHh9y8kr2XIdOIdUatND6YLnd9tX1kJMXUt2sOADxIJuPwrYYo2Dt1X5NlXiscTp5P7KxqS9WqwTkpFlt5zlXJz+WTQ+VyJCIL6mUn51AjeIBIAj71z6dfEaycfAJCZuAHGjcDKDc3GOMTn5Cmg2gU+xzRSMAej2ezcwOqgHs1SSdrYSQHnGcTt6DbBeqUWUPB9kUeusR8QUrJYydDM+5OvkpuZpN0aqSYTXmo8R8PNda2GimUzj7Plcnr2T3xnKqDGhKPJqwda5QWzxO7eS17LmOaj+nJmJdCkBCW23tc8jJS9GltNmMkChJsyZi7bWwTn5I7ud+ZI9+3u7GZbWya7o+ul/m5EdktoeW8lLS2XKwOh8DkveXJZiPquWyDzlOJ+9ANpWK7aaNujeoqUsDch7W7SEn/4QMCb0eU97wYRPFV9PrULdT/6S/dfJbyZuzY+bhvdf41ieIfdI8YJqtkxHeDcIX9Onkc5EX8aGlq5cmKkTjkjX7P3wtc/KSbM79CAmb4kH7CXpsNrVNwc/Sc/JKbs/9yJeE8k1IaMuSqWn8WON00kknnXTSSSed/Ez+B0ohDiBWFjiOAAAAAElFTkSuQmCC"
    };

    $scope.enrollToken = function () {
        console.log($scope.newUser.user);
        console.log($scope.newUser.realm);
        console.log($scope.newUser.pin);
        TokenFactory.enroll($scope.newUser,
            $scope.form, $scope.callback);
    }
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
