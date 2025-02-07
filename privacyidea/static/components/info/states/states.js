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

angular.module('privacyideaApp.infoStates', ['ui.router', 'privacyideaApp.versioning']).config(
    ['$stateProvider', 'versioningSuffixProviderProvider',
        function ($stateProvider, versioningSuffixProviderProvider) {
            // get the instance, the pathname part
            let instance = window.location.pathname;
            if (instance === "/") {
               instance = "";
            }
            const infopath = instance + "/static/components/info/views/";
            $stateProvider
                .state('info', {
                    url: "/info",
                    templateUrl: infopath + "info.rss.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "infoController"
                })
            .state('info.rss', {
                    url: "/info/rss",
                    templateUrl: infopath + "info.rss.html" + versioningSuffixProviderProvider.$get().$get()
                })
    }]);
