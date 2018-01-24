/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2015-12-28 Cornelius Kölbel, <cornelius@privacyidea.org>
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
myApp.controller("smtpServerController", function($scope, $stateParams, inform,
                                                  gettextCatalog, $state,
                                                  $location, ConfigFactory) {
    if ($location.path() === "/config/smtp") {
        $location.path("/config/smtp/list");
    }

    $scope.identifier = $stateParams.identifier;
    if ($scope.identifier) {
        // We are editing an existing SMTP Server
        $scope.getSmtpServers($scope.identifier);
    }

    // Get all servers
    $scope.getSmtpServers = function (identifier) {
        ConfigFactory.getSmtp(function(data) {
            $scope.smtpServers = data.result.value;
            //debug: console.log("Fetched all smtp servers");
            //debug: console.log($scope.smtpServers);
            // return one single smtp server
            if (identifier) {
                $scope.params = $scope.smtpServers[identifier];
                $scope.params["identifier"] = identifier;
            }
        });
    };

    $scope.delSmtpServer = function (identifier) {
        ConfigFactory.delSmtp(identifier, function(data) {
            $scope.getSmtpServers();
        });
    };

    $scope.addSmtpServer = function (params) {
        ConfigFactory.addSmtp(params, function(data) {
            $scope.getSmtpServers();
        });
    };

    $scope.getSmtpServers();

    $scope.sendTestEmail = function() {
        ConfigFactory.testSmtp($scope.params, function(data) {
           if (data.result.value === true) {
               inform.add(gettextCatalog.getString("Test Email sent" +
                   " successfully."),
                   {type: "info"});
           }
        });
    };

    $scope.saveSMTPServer = function() {
        ConfigFactory.addSmtp($scope.params, function(data){
            if (data.result.status === true) {
                inform.add(gettextCatalog.getString("SMTP Config saved."),
                                {type: "info"});
                $state.go('config.smtp.list');
            }
        });
    };

    // listen to the reload broadcast
    $scope.$on("piReload", $scope.getSmtpServers);
});
