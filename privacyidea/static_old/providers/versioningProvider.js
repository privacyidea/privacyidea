/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2019-12-16 Jean-Pierre Höhmann, <jean-pierre.hoehmann@netknights.it>
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

var versioning = angular.module('privacyideaApp.versioning', []);

/*
 * The length of the random string chosen for the version number when running in development mode.
 */
versioning.constant('RANDOM_VERSION_STRING_LENGTH', 5);

/*
 * The version number of the privacyIDEA server software.
 */
versioning.constant('PRIVACYIDEA_VERSION_NUMBER', document.getElementById('PRIVACYIDEA_VERSION_NUMBER').value);

/*
 * A suffix, that can be appended to an url to invalidate the caches when necessary.
 *
 * This factory will provide a provider to provide a suffix for an url that sets a parameter `v` to either the
 * privacyideaVersionNumber, if known, or a random string otherwise. This has the effect of preserving caches, but not
 * across updates of the privacyIDEA server software and not if the user is running a development version of
 * privacyIDEA.
 */
versioning.provider('versioningSuffixProvider', [
    'RANDOM_VERSION_STRING_LENGTH',
    'PRIVACYIDEA_VERSION_NUMBER',
    function(
        RANDOM_VERSION_STRING_LENGTH,
        PRIVACYIDEA_VERSION_NUMBER
    ) {
        this.$get = function() {
            return new (function() {
                this.$get = function() {
                    return '?v=' + (PRIVACYIDEA_VERSION_NUMBER
                        || Math.random().toString(36).substring(2, 2 + RANDOM_VERSION_STRING_LENGTH));
                };
            });
        };
    }
]);
