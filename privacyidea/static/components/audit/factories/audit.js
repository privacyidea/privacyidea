/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2018-11-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *            Remove audit based statistics
 * 2015-07-16 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
 *     Add statistics endpoint
 * 2015-01-20 Cornelius Kölbel, <cornelius@privacyidea.org>
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

myApp.factory("AuditFactory", function (AuthFactory,
                                        $http, $state, $rootScope, auditUrl,
                                        inform) {
        /**
         Each service - just like this service factory - is a singleton.
         */
        return {
            get: function (params, callback) {
                $http.get(auditUrl + "/", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    params: params
                }).success(callback
                ).error(AuthFactory.authError);
            },
            download: function(params, filename, callback) {
                $http.get(auditUrl + "/" + filename, {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()},
                    params: params
                }).success(callback
                ).error(AuthFactory.authError);
            }
        }
    });

