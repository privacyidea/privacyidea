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


myApp.controller("infoController", ["InfoFactory", "$scope", "$location",
    function (InfoFactory, $scope, $location) {

        $('html,body').scrollTop(0);

        $scope.rss = [];
        $scope.getRSS = function () {
            InfoFactory.getRSS(function (rssfeeds) {
                // RFC-822 pub_date strings -> Date so the date filter works.
                angular.forEach(rssfeeds, function (feed) {
                    angular.forEach(feed, function (item) {
                        if (item.pub_date) item.pub_date = new Date(item.pub_date);
                    });
                });
                $scope.rss = rssfeeds;
            });
        }

        $scope.getRSS()

        // listen to the reload broadcast
        $scope.$on("piReload", function () {
            $scope.getRSS();
        });

    }]);