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
        'ngAnimate', 'privacyideaApp.config']);
myApp.config(function ($stateProvider, $urlRouterProvider) {
    //
    // For any unmatched url, redirect to /token
    $urlRouterProvider.otherwise("/token/");
    // We always open the list state, when the resolver state is chosen.
    //$urlRouterProvider.when('/config/resolvers', ' +
    //''/config/resolvers/list');
    //$urlRouterProvider.when('/realms', '/config/realms/list');
    //$urlRouterProvider.when('/config/realms', '/config/realms/list');
    //

});
myApp.constant("authUrl", "/auth");
myApp.constant("tokenUrl", "/token/");
myApp.constant("userUrl", "/user");
myApp.constant("resolverUrl", "/resolver");
myApp.constant("realmUrl", "/realm");
myApp.constant("defaultRealmUrl", "/defaultrealm");
myApp.constant("validateUrl", "/validate");
myApp.constant("systemUrl", "/system");
myApp.constant("auditUrl", "/audit");
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
                    // A state would be nicer, but we get a circular dependency
                    // $state.go("/offline");
                    var error = { error: { message: "The privacyIDEA system seams to be offline. The API is not reachable!"}};
                    $rootScope.restError = error;
                    return;
                }
                return $q.reject(rejection);
            }
        };
    });

}]);
