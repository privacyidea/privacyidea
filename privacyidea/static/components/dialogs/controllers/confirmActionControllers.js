/**
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
angular.module("privacyideaApp").controller("confirmActionController", [
    "$modalInstance",
    "heading",
    "question",
    "action",
    function(
        $modalInstance,
        heading,
        question,
        action
    ) {
        var $ctrl = this;
        $ctrl.heading = heading;
        $ctrl.question = question;
        $ctrl.action = action;

        $ctrl.ok = function() {
            $modalInstance.close();
        };

        $ctrl.cancel = function () {
            $modalInstance.dismiss("cancel");
        }
    }
]);
