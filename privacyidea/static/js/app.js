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
myApp = angular.module("privacyideaApp",
    ['privacyideaAuth',
        'ui.router', 'ui.bootstrap', 'TokenModule',
        'ngAnimate', 'ngIdle', 'privacyideaApp.config',
    'multi-select', 'angularFileUpload']);
myApp.config(function ($urlRouterProvider) {
    // For any unmatched url, redirect to /token
    $urlRouterProvider.otherwise("/token/");
});
myApp.config(['KeepaliveProvider', 'IdleProvider',
    function (KeepaliveProvider, IdleProvider) {
    // Logout configuration
    IdleProvider.idle(20);
    IdleProvider.timeout(10);
    KeepaliveProvider.interval(3);
}]);

var instance = window.location.pathname;
if (instance == "/") {
    instance = "";
}
myApp.constant("instanceUrl", instance);
myApp.constant("authUrl", instance + "/auth");
myApp.constant("tokenUrl", instance + "/token");
myApp.constant("userUrl", instance + "/user");
myApp.constant("resolverUrl", instance + "/resolver");
myApp.constant("realmUrl", instance + "/realm");
myApp.constant("defaultRealmUrl", instance + "/defaultrealm");
myApp.constant("validateUrl", instance + "/validate");
myApp.constant("systemUrl", instance + "/system");
myApp.constant("auditUrl", instance + "/audit");
myApp.constant("policyUrl", instance + "/policy");
myApp.run(['$rootScope', '$state', '$stateParams',
        function ($rootScope, $state, $stateParams) {

            // It's very handy to add references to $state and $stateParams to the $rootScope
            // so that you can access them from any scope within your applications.For example,
            // <li ng-class="{ active: $state.includes('contacts.list') }"> will set the <li>
            // to active whenever 'contacts.list' or one of its decendents is active.
            $rootScope.$state = $state;
            $rootScope.$stateParams = $stateParams;
        }
    ]
);
myApp.config(['$httpProvider', function ($httpProvider) {
    $httpProvider.interceptors.push(function ($q, $rootScope) {
        return {
            responseError: function (rejection) {
                if(rejection.status == 0) {
                    // The API is offline, not reachable
                    var error = { error: { message: "The privacyIDEA system seems to be offline. The API is not reachable!"}};
                    $rootScope.restError = error;
                    $rootScope.showError = true;
                    return;
                }
                return $q.reject(rejection);
            }
        };
    });

}]);
