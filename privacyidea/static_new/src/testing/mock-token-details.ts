/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { TokenDetails } from "@services/token/token.service";

export function mockTokenDetails(overrides: Partial<TokenDetails> = {}): TokenDetails {
  return {
    active: true,
    container_serial: "",
    count: 0,
    count_window: 10,
    description: "",
    failcount: 0,
    id: 1,
    info: {},
    locked: false,
    maxfail: 10,
    otplen: 6,
    realms: [],
    resolver: "",
    revoked: false,
    rollout_state: "",
    serial: "Mock serial",
    sync_window: 1000,
    tokengroup: [],
    tokentype: "hotp",
    user_id: "",
    user_realm: "",
    username: "",
    ...overrides
  };
}
