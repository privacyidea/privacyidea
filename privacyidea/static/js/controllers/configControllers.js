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
myApp.controller("configController", function ($scope, $location,
                                               $rootScope, $state,
                                               ConfigFactory) {
    // go to the system view by default
    if ($location.path() == "/config") {
        $location.path("/config/system");
    }
    if ($location.path() == "/config/resolvers") {
        $location.path("/config/resolvers/list");
    }
    if ($location.path() == "/config/realms") {
        $location.path("/config/realms/list");
    }

    // TODO: This information needs to be fetched from the server
    $scope.availableResolverTypes = ['passwdresolver', 'ldapresolver', 'sqlresolver'];

    $scope.getResolvers = function () {
        ConfigFactory.getResolvers(function (data) {
            $scope.resolvers = data.result.value
        });
    };

    $scope.delResolver = function (name) {
        ConfigFactory.delResolver(name, function (data) {
            $scope.resolvers = data.result.value;
            $scope.getResolvers();
        });
    };

    $scope.getRealms = function () {
        ConfigFactory.getRealms(function (data) {
            $scope.realms = data.result.value;
        });
    };

    $scope.setRealm = function (name) {
        var resolvers = [];
        angular.forEach($scope.selectedResolvers, function (value, resolver) {
            if (value === true) {
                resolvers.push(resolver)
            }
        });

        var pObject = {resolvers: resolvers.join(',')};

        ConfigFactory.setRealm(name, pObject, function (data) {
            $scope.set_result = data.result.value;
            $scope.cancelEdit();
            $scope.getRealms();
        });
    };

    $scope.delRealm = function (name) {
        ConfigFactory.delRealm(name, function (data) {
            $scope.set_result = data.result.value;
            $scope.getRealms();
        });
    };

    $scope.setDefaultRealm = function (name) {
        ConfigFactory.setDefaultRealm(name, function (data) {
            $scope.set_result = data.result.value;
            $scope.getRealms();
        });
    };

    $scope.clearDefaultRealm = function () {
        ConfigFactory.clearDefaultRealm(function (data) {
            $scope.set_result = data.result.value;
            $scope.getRealms();
        });
    };

    $scope.startEdit = function (realmname, realm) {
        $scope.editRealm = realmname;
        // fill the selectedResolvers with the resolver of the realm
        $scope.selectedResolvers = {};
        angular.forEach(realm.resolver, function (resolver, _keyreso) {
            $scope.selectedResolvers[resolver.name] = true;
        })
    };

    $scope.cancelEdit = function () {
        $scope.editRealm = null;
        $scope.selectedResolvers = {};
    };

    $scope.editResolver = function (resolvername, r_type) {
        // change the view to the config.resolvers.edit
        $state.go("config.resolvers.edit"+r_type, {'resolvername': resolvername});
        $rootScope.returnTo = "config.resolvers.list";
    };

    $scope.getRealms();
    $scope.getResolvers();
    $scope.selectedResolvers = {};

});

myApp.controller("PasswdResolverController", function ($scope, ConfigFactory, $state, $stateParams) {
    $scope.params = {type: 'passwdresolver',
                    fileName: "/etc/passwd"};

    $scope.resolvername = $stateParams.resolvername;
    if ($scope.resolvername) {
        /* If we have a resolvername, we do an Edit
        and we need to fill all the $scope.params */
        ConfigFactory.getResolver($scope.resolvername, function (data) {
            var resolver = data.result.value[$scope.resolvername];
            $scope.params = resolver.data;
            $scope.params.type = 'passwdresolver';
        });
    }

    $scope.setResolver = function () {
        ConfigFactory.setResolver($scope.resolvername, $scope.params, function (data) {
            $scope.set_result = data.result.value;
            $scope.getResolvers();
            $state.go("config.resolvers.list");
        });
    };
});

myApp.controller("LdapResolverController", function ($scope, ConfigFactory, $state, $stateParams) {
    /*
     BINDDN, BINDPW, LDAPURI, TIMEOUT, LDAPBASE, LOGINNAMEATTRIBUTE,
     LDAPSEARCHFILTER,
     LDAPFILTER, USERINFO, SIZELIMIT, NOREFERRALS, CACERTIFICATE
     */
    $scope.params = {
        SIZELIMIT: 500,
        TIMEOUT: 5,
        UIDTYPE: "DN",
        type: 'ldapresolver'
    };
    $scope.result = {};
    $scope.resolvername = $stateParams.resolvername;
    $scope.showResult = false;

    if ($scope.resolvername) {
        /* If we have a resolvername, we do an Edit
        and we need to fill all the $scope.params */
        ConfigFactory.getResolver($scope.resolvername, function (data) {
            var resolver = data.result.value[$scope.resolvername];
            console.log(resolver);
            $scope.params = resolver.data;
            $scope.params.NOREFERRALS = ($scope.params.NOREFERRALS == "1");
            $scope.params.type = 'ldapresolver';
        });
    }

    $scope.presetAD = function () {
        $scope.params.LOGINNAMEATTRIBUTE = "sAMAcountName";
        $scope.params.LDAPSEARCHFILTER = "(sAMAccountName=*)(objectClass=person)";
        $scope.params.LDAPFILTER = "(&(sAMAccountName=%s)(objectClass=person))";
        $scope.params.USERINFO = '{ "username": "sAMAccountName", "phone" : "telephoneNumber", "mobile" : "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }';
        $scope.params.NOREFERRALS = true;
        $scope.params.SIZELIMIT = 500;
        $scope.params.UIDTYPE = "DN";
    };

    $scope.presetLDAP = function () {
        $scope.params.LOGINNAMEATTRIBUTE = "uid";
        $scope.params.LDAPSEARCHFILTER = "(uid=*)(objectClass=inetOrgPerson)";
        $scope.params.LDAPFILTER = "(&(uid=%s)(objectClass=inetOrgPerson))";
        $scope.params.USERINFO = '{ "username": "uid", "phone" : "telephoneNumber", "mobile" : "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }';
        $scope.params.NOREFERRALS = true;
        $scope.params.SIZELIMIT = 500;
        $scope.params.UIDTYPE = "entryUUID";
    };

    $scope.setLDAPResolver = function () {
        ConfigFactory.setResolver($scope.resolvername, $scope.params, function (data) {
            $scope.set_result = data.result.value;
            $scope.getResolvers();
            $state.go("config.resolvers.list");
        });
    };

    $scope.testLDAP = function () {
        ConfigFactory.testLDAPResolver($scope.params, function (data) {
            $scope.result = {
                result: data.result.value,
                description: data.detail.description
            };
            $scope.showResult = true;
        });
    }
});
