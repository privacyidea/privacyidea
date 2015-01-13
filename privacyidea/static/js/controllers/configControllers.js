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
angular.module("privacyideaApp")
    .controller("configController", function ($scope, $http,
                                                resolverUrl,
                                                realmUrl, defaultRealmUrl, auth,
                                                $rootScope, $state) {

        $scope.user = auth.getUser();

        $scope.getResolvers = function () {
            var auth_token = auth.getAuthToken();
            $http.get(resolverUrl, {
                headers: {'Authorization': auth_token }
            }).success(function (data) {
                $scope.resolvers = data.result.value;
            }).error(function (error) {
                $rootScope.restError = error.result;
            });
        };

        $scope.setResolver = function (name, file) {
            var auth_token = auth.getAuthToken();

            var pObject = { fileName: file,
                            type: 'passwdresolver'};

            var request = $http({method: "post",
                url: resolverUrl + "/" + name,
                data: pObject,
                headers: {'Authorization': auth_token,
                          'Content-Type': 'application/json'}
            });
            request.success(function (data) {
                $scope.set_result = data.result.value;
                $scope.getResolvers();
                $state.go("config.resolvers.list");
            }).error(function (error) {
                $rootScope.restError = error.result;
            });
        };

        $scope.delResolver = function (name) {
            var auth_token = auth.getAuthToken();
            $http.delete(resolverUrl + "/" + name, {
                headers: {'Authorization': auth_token }
            }).success(function (data) {
                $scope.resolvers = data.result.value;
                $scope.getResolvers();
            }).error(function (error) {
                $rootScope.restError = error.result;
            });
        };

        $scope.getRealms = function () {
            var auth_token = auth.getAuthToken();
            $http.get(realmUrl, {
                headers: {'Authorization': auth_token }
            }).success(function (data) {
                $scope.realms = data.result.value;
            }).error(function (error) {
                $rootScope.restError = error.result;
            });
        };

        $scope.setRealm = function (name) {
            var auth_token = auth.getAuthToken();

            var resolvers = [];
            angular.forEach($scope.selectedResolvers, function(value, resolver) {
                if (value === true) {
                    resolvers.push(resolver)
                }
            });

            var pObject = { resolvers: resolvers.join(',') };

            var request = $http({method: "POST",
                url: realmUrl + "/" + name,
                data: pObject,
                headers: {'Authorization': auth_token,
                          'Content-Type': 'application/json'}
            });
            request.success(function (data) {
                $scope.set_result = data.result.value;
                $scope.cancelEdit();
                $scope.getRealms();
            }).error(function (error) {
                $rootScope.restError = error.result;
            });
        };

        $scope.delRealm = function (name) {
            var auth_token = auth.getAuthToken();

            var request = $http({method: "delete",
                url: realmUrl + "/" + name,
                headers: {'Authorization': auth_token,
                          'Content-Type': 'application/json'}
            });
            request.success(function (data) {
                $scope.set_result = data.result.value;
                $scope.getRealms();
            }).error(function (error) {
                $rootScope.restError = error.result;
            });
        };

        $scope.setDefaultRealm = function (name) {
            var auth_token = auth.getAuthToken();

            var request = $http({method: "post",
                url: defaultRealmUrl + "/" + name,
                headers: {'Authorization': auth_token,
                          'Content-Type': 'application/json'}
            });
            request.success(function (data) {
                $scope.set_result = data.result.value;
                $scope.getRealms();
            }).error(function (error) {
                $rootScope.restError = error.result;
            });
        };


        $scope.clearDefaultRealm = function () {
            var auth_token = auth.getAuthToken();

            var request = $http({method: "delete",
                url: defaultRealmUrl,
                headers: {'Authorization': auth_token,
                          'Content-Type': 'application/json'}
            });
            request.success(function (data) {
                $scope.set_result = data.result.value;
                $scope.getRealms();
            }).error(function (error) {
                $rootScope.restError = error.result;
            });
        };

        $scope.startEdit = function(realmname, realm) {
            $scope.editRealm = realmname;
            // fill the selectedResolvers with the resolver of the realm
            $scope.selectedResolvers = {};
            angular.forEach(realm.resolver, function (resolver, _keyreso) {
                $scope.selectedResolvers[resolver.name] = true;
            })
        };

        $scope.cancelEdit = function() {
            $scope.editRealm = null;
            $scope.selectedResolvers = {};
        };

        $scope.getRealms();
        $scope.getResolvers();
        $scope.selectedResolvers = {};

    });
