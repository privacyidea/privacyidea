/**
 * (c) NetKnights GmbH 2024,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-FileCopyrightText: 2024 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

myApp.factory("InfoFactory", ["AuthFactory", "$http", "$state", "$rootScope", "infoUrl",
    function (AuthFactory, $http, $state, $rootScope,
              infoUrl) {
        /**
         Each service - just like this service factory - is a singleton.
         */
        return {
            getRSS: function (callback) {
                $http.get(infoUrl + "/rss", {
                    headers: {'PI-Authorization': AuthFactory.getAuthToken()}
                }).then(function (response) {
                    callback(response.data.result.value)
                }, function (error) {
                    AuthFactory.authError(error.data)
                });
            }
        };
    }]);
