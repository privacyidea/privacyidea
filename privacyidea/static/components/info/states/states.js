/**
 * http://www.privacyidea.org
 *
 * (c) Cornelius Kölbel, <cornelius.koelbel@netknights.it>
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

angular.module('privacyideaApp.infoStates', ['ui.router', 'privacyideaApp.versioning']).config(
    ['$stateProvider', 'versioningSuffixProviderProvider',
        function ($stateProvider, versioningSuffixProviderProvider) {
            // get the instance, the pathname part
            var instance = window.location.pathname;
            if (instance === "/") {
               instance = "";
            }
            var dashboardpath = instance + "/static/components/info/views/";
            $stateProvider
                .state('info', {
                    url: "/info",
                    templateUrl: dashboardpath + "info.rss.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "infoController"
                })
                .state('info.news', {
                    url: "/info/news",
                    templateUrl: tokenPath + "info.rss.html" + versioningSuffixProviderProvider.$get().$get(),
                    controller: "infoController"
                })
    }]);
