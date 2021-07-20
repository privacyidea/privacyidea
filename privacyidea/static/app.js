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
        'ngIdle', 'ui.highlight', 'ngSanitize',
        'privacyideaAuth',
        'privacyideaApp.auditStates',
        'privacyideaApp.configStates',
        'privacyideaApp.tokenStates',
        'privacyideaApp.dashboardStates',
        'privacyideaApp.userStates',
        'privacyideaApp.machineStates',
        'privacyideaApp.registerStates',
        'privacyideaApp.recoveryStates',
        'privacyideaApp.loginStates',
        'privacyideaApp.componentStates',
        'privacyideaApp.versioning',
        'isteven-multi-select', 'ngFileUpload',
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
myApp.constant("periodicTaskUrl", backendUrl + instance + "/periodictask");
myApp.constant("smsgatewayUrl", backendUrl + instance + "/smsgateway");
myApp.constant("defaultRealmUrl", backendUrl + instance + "/defaultrealm");
myApp.constant("validateUrl", backendUrl + instance + "/validate");
myApp.constant("systemUrl", backendUrl + instance + "/system");
myApp.constant("auditUrl", backendUrl + instance + "/audit");
myApp.constant("clientUrl", backendUrl + instance + "/client");
myApp.constant("subscriptionsUrl", backendUrl + instance + "/subscriptions");
myApp.constant("policyUrl", backendUrl + instance + "/policy");
myApp.constant("registerUrl", backendUrl + instance + "/register");
myApp.constant("CAConnectorUrl", backendUrl + instance + "/caconnector");
myApp.constant("smtpServerUrl", backendUrl + instance + "/smtpserver");
myApp.constant("radiusServerUrl", backendUrl + instance + "/radiusserver");
myApp.constant("privacyideaServerUrl", backendUrl + instance + "/privacyideaserver");
myApp.constant("recoveryUrl", backendUrl + instance + "/recover");
myApp.constant("resourceNamePatterns", {
    simple: {pattern: "^[a-zA-Z0-9_.-]+$",
        title: gettext("The resource name must consist of letters, numbers and '_', '-', '.'")},
/* we have to ignore "test" and "test_request" as a resource name explicitly */
    withoutTest: {pattern: "^(?!test$)([A-Za-z0-9_.-]+)$",
        title: gettext("The resource name must consist of letters, numbers and '_', '-', '.' " +
            "and must not be the word 'test'")},
    withoutTestEmail: {pattern: "^(?!send_test_email$)([A-Za-z0-9_.-]+)$",
        title: gettext("The resource name must consist of letters, numbers and '_', '-', '.' " +
            "and must not be the word 'send_test_email'")},
    withoutTestRequest: {pattern: "^(?!test_request$)([a-zA-Z0-9_.-]+)$",
        title: gettext("The resource name must consist of letters, numbers and '_', '-', '.' " +
            "and must not be the word 'test_request'")}});
myApp.run(['$rootScope', '$state', '$stateParams', 'gettextCatalog',
        function ($rootScope, $state, $stateParams, gettextCatalog) {

            // It's very handy to add references to $state and $stateParams to the $rootScope
            // so that you can access them from any scope within your applications.For example,
            // <li ng-class="{ active: $state.includes('contacts.list') }"> will set the <li>
            // to active whenever 'contacts.list' or one of its descendents is active.
            $rootScope.$state = $state;
            $rootScope.$stateParams = $stateParams;
            gettextCatalog.setCurrentLanguage(browserLanguage);

            // we set this, so we can use it in templates
            $rootScope.browserLanguage = browserLanguage;

            $rootScope.publicLink = "https://netknights.it/" + gettextCatalog.getCurrentLanguage() + "/support-link-public";
            $rootScope.privacyideaSupportLink = $rootScope.publicLink;
        }
    ]
);
myApp.config(['$httpProvider', function ($httpProvider, inform, gettext) {
    $httpProvider.interceptors.push(function ($rootScope, $q, inform, gettext) {
        return {
            request: function(config) {
                $rootScope.$broadcast('spinnerEvent', {
                    action: 'increment'
                });
                return config || $q.when(config);
            },
            response: function(response) {
                $rootScope.$broadcast('spinnerEvent', {
                    action: 'decrement'
                });
                return response || $q.when(response);
            },
            responseError: function (rejection) {
                //debug: console.log(rejection);
                $rootScope.$broadcast('spinnerEvent', {
                    action: 'decrement'
                });
                if(rejection.status === 0) {
                    if (rejection.config.timeout) {
                        // The Request was canceled on purpose (getUsers)
                        //debug: console.log("user canceled");
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
        $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|tel|file|blob|otpauth):/);
}]);

isTrue = function (value) {
    return ["1", "true", true, "True"].indexOf(value) > -1;
};

// this is for the translation of the constants (see
// https://github.com/rubenv/angular-gettext/issues/67 )
function gettext (string) {
  return string;
}
