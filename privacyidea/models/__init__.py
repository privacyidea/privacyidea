# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.

#  2018-06-20 Friedrich Weber <friedrich.weber@netknights.it>
#             Add PeriodicTask, PeriodicTaskOption, PeriodicTaskLastRun
#  2018-25-09 Paul Lettich <paul.lettich@netknights.it>
#             Add decrease/reset methods to EventCounter
#  2017-10-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add timeout and retries to radiuserver
#  2017-08-24 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Remote privacyIDEA Server
#  2017-08-11 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add AuthCache
#  2017-04-19 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add support for multiple challenge response token
#  2016-02-19 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add radiusserver table
#  2015-08-27 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add revocation of token
# Nov 11, 2014 Cornelius Kölbel, info@privacyidea.org

from .db import db
from .audit import Audit, audit_column_length
from .cache import AuthCache, UserCache
from .caconnector import CAConnector, CAConnectorConfig
from .challenge import Challenge, cleanup_challenges
from .config import (Config, NodeName, Admin, PasswordReset,
                     save_config_timestamp, PRIVACYIDEA_TIMESTAMP)
from .customuserattribute import CustomUserAttribute
from .event import EventHandler, EventHandlerOption, EventHandlerCondition
from .eventcounter import EventCounter
from .machine import (MachineResolver, MachineResolverConfig, MachineToken,
                      MachineTokenOptions, get_machineresolver_id,
                      get_machinetoken_ids)
from .monitoringstats import MonitoringStats
from .periodictask import PeriodicTask, PeriodicTaskOption, PeriodicTaskLastRun
from .policy import Policy, PolicyDescription, PolicyCondition
from .realm import Realm, ResolverRealm
from .resolver import Resolver, ResolverConfig
from .server import PrivacyIDEAServer, RADIUSServer, SMTPServer
from .serviceid import Serviceid
from .smsgateway import SMSGateway, SMSGatewayOption
from .subscription import ClientApplication, Subscription
from .token import (Token, TokenInfo, TokenOwner, TokenCredentialIdHash,
                    TokenRealm, get_token_id)
from .tokencontainer import (TokenContainer, TokenContainerInfo,
                             TokenContainerRealm, TokenContainerOwner,
                             TokenContainerStates, TokenContainerTemplate,
                             TokenContainerToken)
from .tokengroup import Tokengroup, TokenTokengroup

# We don't use "import *" but to avoid the unused import warning we define this
__all__ = ["db", "Audit", "audit_column_length", "AuthCache", "UserCache",
           "CAConnector", "CAConnectorConfig", "Challenge", "cleanup_challenges",
           "Config", "NodeName", "Admin", "PasswordReset", "save_config_timestamp",
           "PRIVACYIDEA_TIMESTAMP", "CustomUserAttribute",
           "EventHandler", "EventHandlerOption", "EventHandlerCondition", "EventCounter",
           "MachineResolver", "MachineResolverConfig", "MachineToken",
           "MachineTokenOptions", "get_machineresolver_id", "get_machinetoken_ids",
           "MonitoringStats",
           "PeriodicTask", "PeriodicTaskOption", "PeriodicTaskLastRun",
           "Policy", "PolicyDescription", "PolicyCondition",
           "Realm", "ResolverRealm", "Resolver", "ResolverConfig",
           "PrivacyIDEAServer", "RADIUSServer", "SMTPServer",
           "Serviceid", "SMSGateway", "SMSGatewayOption",
           "ClientApplication", "Subscription",
           "Token", "TokenInfo", "TokenOwner", "TokenCredentialIdHash",
           "TokenRealm", "get_token_id",
           "TokenContainer", "TokenContainerInfo",
           "TokenContainerRealm", "TokenContainerOwner",
           "TokenContainerStates", "TokenContainerTemplate",
           "TokenContainerToken",
           "Tokengroup", "TokenTokengroup"]
