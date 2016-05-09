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
    ['ui.router', 'ui.bootstrap', 'TokenModule',
        'ngAnimate', 'ngIdle',
        'privacyideaAuth',
        'privacyideaApp.auditStates',
        'privacyideaApp.configStates',
        'privacyideaApp.tokenStates',
        'privacyideaApp.userStates',
        'privacyideaApp.machineStates',
        'privacyideaApp.registerStates',
        'privacyideaApp.recoveryStates',
        'privacyideaApp.loginStates',
        'isteven-multi-select', 'angularFileUpload',
        'inform', 'gettext', 'cfp.hotkeys']);
myApp.config(function ($urlRouterProvider) {
    // For any unmatched url, redirect to /token
    $urlRouterProvider.otherwise("/token/list");
});
myApp.config(['KeepaliveProvider', 'IdleProvider',
    function (KeepaliveProvider, IdleProvider) {
    // Logout configuration.
    // Default to 120 seconds
    IdleProvider.idle(110);
    IdleProvider.timeout(10);
    KeepaliveProvider.interval(3);
}]);

var instance = window.location.pathname;
if (instance === "/") {
    instance = "";
}
var backendUrl = "";
myApp.constant("instanceUrl", instance);
myApp.constant("authUrl", backendUrl + instance + "/auth");
myApp.constant("tokenUrl", backendUrl + instance + "/token");
myApp.constant("userUrl", backendUrl + instance + "/user");
myApp.constant("resolverUrl", backendUrl + instance + "/resolver");
myApp.constant("machineResolverUrl", backendUrl + instance + "/machineresolver");
myApp.constant("machineUrl", backendUrl + instance + "/machine");
myApp.constant("applicationUrl", backendUrl + instance + "/application");
myApp.constant("realmUrl", backendUrl + instance + "/realm");
myApp.constant("eventUrl", backendUrl + instance + "/event");
myApp.constant("defaultRealmUrl", backendUrl + instance + "/defaultrealm");
myApp.constant("validateUrl", backendUrl + instance + "/validate");
myApp.constant("systemUrl", backendUrl + instance + "/system");
myApp.constant("auditUrl", backendUrl + instance + "/audit");
myApp.constant("policyUrl", backendUrl + instance + "/policy");
myApp.constant("registerUrl", backendUrl + instance + "/register");
myApp.constant("CAConnectorUrl", backendUrl + instance + "/caconnector");
myApp.constant("smtpServerUrl", backendUrl + instance + "/smtpserver");
myApp.constant("radiusServerUrl", backendUrl + instance + "/radiusserver");
myApp.constant("recoveryUrl", backendUrl + instance + "/recover");
myApp.run(['$rootScope', '$state', '$stateParams', 'gettextCatalog',
        function ($rootScope, $state, $stateParams, gettextCatalog) {

            // It's very handy to add references to $state and $stateParams to the $rootScope
            // so that you can access them from any scope within your applications.For example,
            // <li ng-class="{ active: $state.includes('contacts.list') }"> will set the <li>
            // to active whenever 'contacts.list' or one of its decendents is active.
            $rootScope.$state = $state;
            $rootScope.$stateParams = $stateParams;
            console.log("Browser language "+browserLanguage);
            // remove everythin after the - like en-US -> en
            var nlang = browserLanguage.replace('/-\*$/', '');
            if (["de"].indexOf(nlang) === -1) {
                // if language is not contained in translations,
                // we use default to "en"
                nlang = "en";
            }
            console.log("Setting language to " + nlang);
            gettextCatalog.setCurrentLanguage(nlang);
            gettextCatalog.debug = true;
        }
    ]
);
myApp.config(['$httpProvider', function ($httpProvider, inform, gettext) {
    $httpProvider.interceptors.push(function ($q, inform, gettext) {
        return {
            responseError: function (rejection) {
                console.log(rejection);
                if(rejection.status === 0) {
                    if (rejection.config.timeout) {
                        // The Request was canceled on purpose (getUsers)
                        console.log("user canceled");
                    } else {
                        // The API is offline, not reachable
                        inform.add(gettext("The privacyIDEA system seems to be" +
                        " offline. The API is not reachable!"),
                            {type: "danger", ttl: 10000});
                    }
                    return;
                }

                return $q.reject(rejection);
            }
        };
    });

}]);

myApp.config(['$compileProvider',
    function ($compileProvider) {
        $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|tel|file|blob):/);
}]);
