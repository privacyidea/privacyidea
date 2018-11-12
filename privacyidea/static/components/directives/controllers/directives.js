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
myApp.directive('tokenDataEdit', function(AuthFactory, instanceUrl) {
    return {
        scope: {
            text: '@',
            buttonText: '@',
            tokenData: '@',
            tokenLocked: '@',
            tokenKey: '@',
            hideButtons: '@',
            setRight: '@',
            inputPattern: '@',
            inputType: '@',
            callback: '&',
            callbackCancel: '&'
        },
        templateUrl: instanceUrl + "/static/components/directives/views/directive.tokendata.html",
        link: function(scope, element, attr, ctrl) {
            scope.loggedInUser = AuthFactory.getUser();
            //debug: console.log("tokenDataEdit");
            //debug: console.log(scope.loggedInUser);
        }
    };
});

myApp.directive("piFilter", function (instanceUrl) {
    return {
        require: 'ngModel',
        restrict: 'E',
        scope: {},
        templateUrl: instanceUrl + "/static/components/directives/views/directive.filter.table.html",
        link: function (scope, element, attr, ctrl) {
            scope.updateFilter = function() {
                ctrl.$setViewValue(scope.filterValue);
            };
            ctrl.$viewChangeListeners.push(function(){
              scope.$eval(attr.ngChange);
            });
        }
    };
});

myApp.directive("piSortBy", function(){
    return {
        restrict: 'A',
        link: function(scope, element, attr) {
            element.on('click', function() {
                var column = attr.piSortBy;
                scope.params.sortby=column;
                scope.reverse=!scope.reverse;
                $(".sortUp").addClass("unsorted");
                $(".sortDown").addClass("unsorted");
                $(".sortUp").removeClass("sortUp");
                $(".sortDown").removeClass("sortDown");
                element.removeClass("unsorted");
                if (scope.reverse) {
                    element.addClass("sortDown");
                } else {
                    element.addClass("sortUp");
                }
                scope.get();
            });
        }
    };
});


myApp.directive('assignUser', function($http, $rootScope, userUrl, AuthFactory, instanceUrl) {
    /*
    This directive is used to select a user from a realm

    newUserObject consists of .user and .realm
     */
    return {
        scope: {
            newUserObject: '=',
            realms: '='
        },
        templateUrl: instanceUrl + "/static/components/directives/views/directive.assignuser.html",
        link: function (scope, element, attr) {
            //debug: console.log("Entering assignUser directive");
            //debug: console.log(scope.realms);
            //debug: console.log(scope.newUserObject);

            // toggle enable/disable loadUsers calls
            scope.toggleLoadUsers = function($toggle) {
                // only trigger if the search_on_enter policy is active
                if ($rootScope.search_on_enter) {
                    var $viewValue = scope.newUserObject.user;
                    scope.newUserObject.toggle = $toggle;
                    // update field value with a placeholder to trigger typeahead
                    if (scope.newUserObject.toggle
                        && $viewValue.charAt($viewValue.length - 1) != "*") {
                        var ctrl = element.find('input').controller('ngModel');
                        ctrl.$setViewValue($viewValue + "*");
                    }
                }
            };

            scope.loadUsers = function($viewValue) {
            if ($rootScope.search_on_enter && (!$viewValue || $viewValue == "*" || !scope.newUserObject.toggle)) {
                // only use existing result if any, and if search_on_enter policy is active
                return scope.newUserObject.loadedUsers;
            }
            var auth_token = AuthFactory.getAuthToken();
            return $http({
                method: 'GET',
                url: userUrl + "/?username=*" + $viewValue + "*" +
                    "&realm=" + scope.newUserObject.realm,
                headers: {'PI-Authorization': auth_token}
            }).then(function ($response) {
                scope.newUserObject.loadedUsers = $response.data.result.value.map(function (item) {
                    scope.newUserObject.email = item.email;
                    scope.newUserObject.mobile = item.mobile;
                    scope.newUserObject.phone = item.phone;
                    return "[" + item.userid + "] " + item.username +
                        " (" + item.givenname + " " + item.surname + ")";
                });
                return scope.newUserObject.loadedUsers;
            });
            };
        }
    };
});

myApp.directive('assignToken', function($http, $rootScope, tokenUrl,
                                        AuthFactory, instanceUrl) {
    /*
    This directive is used to select a serial number and assign it
    to the user.

    newTokenObject consists of .serial and .pin
     */
    return {
        scope: {
            newTokenObject: '='
        },
        templateUrl: instanceUrl + "/static/components/directives/views/directive.assigntoken.html",
        link: function (scope, element, attr) {
            // Toggle enable/disable loadSerials call
            scope.toggleLoadSerials = function($toggle) {
                // only trigger if the search_on_enter policy is active
                if ($rootScope.search_on_enter) {
                    var $viewValue = scope.newTokenObject.serial;
                    scope.newTokenObject.toggle = $toggle;
                    // update field value with a placeholder to trigger typeahead
                    if (scope.newTokenObject.toggle
                        && $viewValue.charAt($viewValue.length - 1) != "*") {
                        var ctrl = element.find('input').controller('ngModel');
                        ctrl.$setViewValue($viewValue + "*");
                    }
                }
            };
            scope.loadSerials = function($viewValue) {
            if ($rootScope.search_on_enter && (!$viewValue || $viewValue == "*" || !scope.newTokenObject.toggle)) {
                // only use existing result if any, and if search_on_enter policy is active
                return scope.newTokenObject.loadedSerials;
            }
            var auth_token = AuthFactory.getAuthToken();
            return $http({
                method: 'GET',
                url: tokenUrl + "/",
                headers: {'PI-Authorization': auth_token},
                params: {assigned: "False",
                serial: "*" + $viewValue + "*"}
            }).then(function ($response) {
                scope.newTokenObject.loadedSerials = $response.data.result.value.tokens.map(function (item) {
                    return item.serial + " (" + item.tokentype + ")";
                });
                return scope.newTokenObject.loadedSerials;
            });
            };
        }
    };
});


myApp.directive('attachToken', function($http, tokenUrl,
                                        AuthFactory, instanceUrl) {
    /*
    This directive is used to select a serial number and attach it to a machine

    newTokenObject consists of .serial
     */
    return {
        scope: {
            newTokenObject: '='
        },
        templateUrl: instanceUrl + "/static/components/directives/views/directive.attachtoken.html",
        link: function (scope, element, attr) {
            scope.loadSerials = function($viewValue) {
            var auth_token = AuthFactory.getAuthToken();
            return $http({
                method: 'GET',
                url: tokenUrl + "/",
                headers: {'PI-Authorization': auth_token},
                params: {serial: "*" + $viewValue + "*"}
            }).then(function ($response) {
                return $response.data.result.value.tokens.map(function (item) {
                    return item.serial + " (" + item.tokentype + ")";
                });
            });
            };
        }
    };
});


myApp.directive('attachMachine', function($http, machineUrl,
                                          AuthFactory, instanceUrl) {
    /*
    This directive is used to select a machine.
     */
    return {
        scope: {
            newMachine: '='
        },
        templateUrl: instanceUrl + "/static/components/directives/views/directive.attachmachine.html",
        link: function (scope, element, attr) {
            scope.loadMachines = function($viewValue) {
            var auth_token = AuthFactory.getAuthToken();
            return $http({
                method: 'GET',
                url: machineUrl + "/",
                headers: {'PI-Authorization': auth_token},
                params: {any: $viewValue}
            }).then(function ($response) {
                //debug: console.log($response.data.result.value);
                return $response.data.result.value.map(function (item) {
                    return item.hostname + " [" + item.ip + "] (" +
                        item.id + " in " + item.resolver_name + ")";
                });
            });
            };
        }
    };
});


myApp.directive('equals', function() {
  return {
    restrict: 'A', // only activate on element attribute
    require: '?ngModel', // get a hold of NgModelController
    link: function(scope, elem, attrs, ngModel) {
      if(!ngModel) { // do nothing if no ng-model
          return;
      }

      // watch own value and re-validate on change
      scope.$watch(attrs.ngModel, function() {
        validate();
      });

      // observe the other value and re-validate on change
      attrs.$observe('equals', function (val) {
        validate();
      });

      var validate = function() {
        // values
        var val1 = ngModel.$viewValue || "";
        var val2 = attrs.equals || "";

        // set validity
        ngModel.$setValidity('equals', val1 === val2);
      };
    }
  };
});

myApp.directive('statusClass', function() {
    return {
        link: function (scope, element, attrs, ngModel) {
            if (["OK", "1", 1].indexOf( attrs.statusClass )>-1) {
                element.addClass("label label-success");
                element.removeClass("label-danger");
            } else {
                element.addClass("label label-danger");
                element.removeClass("label-success");
            }
        }
    };
});

// See http://blog.techdev.de/an-angularjs-directive-to-download-pdf-files/
myApp.directive('csvDownload', function(AuthFactory, $http, instanceUrl) {
    return {
        restrict: 'E',
        templateUrl: instanceUrl + "/static/components/directives/views/directive.csvdownload.html",
        scope: true,
        link: function (scope, element, attr) {
            var anchor = element.children()[0];

            // When the download starts, disable the link
            scope.$on('download-start', function () {
                $(anchor).attr('disabled', 'disabled')
                    .text('Please Wait! Crunching data...');
                scope.downloadProgress = true;
            });

            // When the download finishes, attach the data to the link. Enable the link and change its appearance.
            scope.$on('downloaded', function (event, data) {
                $(anchor).attr({
                    href: 'data:text/csv;utf-8,' + encodeURI(data),
                    download: attr.filename
                })
                    .removeAttr('disabled')
                    .text('Save')
                    .removeClass('btn-primary')
                    .addClass('btn-success');
                scope.downloadProgress = false;
                // Also overwrite the download pdf function to do nothing.
                scope.downloadCSV = function () {
                };
            });
        },
        controller: ['$scope', '$attrs', '$http', function ($scope, $attrs, $http) {
            $scope.downloadCSV = function () {
                $scope.$emit('download-start');
                //debug: console.log("Download start.");
                $scope.getParams();
                $http.get($attrs.url, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    params: $scope.params
                }).then(function (response) {
                    //debug: console.log("Downloaded.");
                    $scope.$emit('downloaded', response.data);
                });
            };
        }]
    }
});

myApp.directive('spinner', function() {
    return {
        scope: {
            name: '@?',
            register: '=?'
        },
        template: [
            '<div ng-show="showSpinner">',
            '<span class="glyphicon glyphicon-refresh spin" style="margin: 50% 5px 0 0; font-size:120%; color: #787878;" aria-hidden="true"></span>',
            '</div>'
        ].join(''),
        controller: function($scope, $rootScope) {
            $scope.loading_queue = 0;
            $scope.$watch('loading_queue', function(loading_queue) {
                if (loading_queue > 0) {
                    $scope.showSpinner = true;
                    $rootScope.showReload = false;
                } else if (loading_queue < 0) {
                    $scope.loading_queue = 0;
                } else {
                    $scope.showSpinner = false;
                    $rootScope.showReload = true;
                }
            });
            $scope.$on('spinnerEvent', function(event, data) {
                if(data.action === 'increment') {
                    $scope.loading_queue++;
                } else if(data.action === 'decrement') {
                    $scope.loading_queue--;
                }
            });
        }
    };
});

myApp.directive('focus', function($timeout){
    return {
 scope : {
   trigger : '@focus'
 },
 link : function(scope, element) {
  scope.$watch('trigger', function(value) {
    if (value === "true") {
      $timeout(function() {
       element[0].focus();
      });
   }
 });
 }
};
});