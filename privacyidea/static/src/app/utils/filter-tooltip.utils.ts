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

// Kept as complete sentences rather than noun interpolation, so a translation can pick its own word order and case.
const FILTER_VALUE_TOOLTIPS: Record<string, string> = {
  action: $localize`:@@common.filterByAction:Filter by this action`,
  action_detail: $localize`:@@common.filterByActionDetail:Filter by this action detail`,
  administrator: $localize`:@@common.filterByAdministrator:Filter by this administrator`,
  attempt_id: $localize`:@@common.filterByAttemptId:Filter by this attempt ID`,
  client: $localize`:@@common.filterByClient:Filter by this client`,
  container_serial: $localize`:@@common.filterByContainer:Filter by this container`,
  date: $localize`:@@common.filterByDay:Filter by this day`,
  error_message: $localize`:@@common.filterByErrorMessage:Filter by this error message`,
  event: $localize`:@@common.filterByEvent:Filter by this event`,
  peer_ip: $localize`:@@common.filterByPeerAddress:Filter by this peer address`,
  policies: $localize`:@@common.filterByPolicy:Filter by this policy`,
  privacyidea_server: $localize`:@@common.filterByServer:Filter by this server`,
  realm: $localize`:@@common.filterByRealm:Filter by this realm`,
  resolver: $localize`:@@common.filterByResolver:Filter by this resolver`,
  resolver_name: $localize`:@@common.filterByResolver:Filter by this resolver`,
  serial: $localize`:@@common.filterBySerial:Filter by this serial`,
  service_id: $localize`:@@common.filterByServiceId:Filter by this service ID`,
  source_ip: $localize`:@@common.filterBySourceIp:Filter by this source IP`,
  startdate: $localize`:@@common.filterByDay:Filter by this day`,
  transaction_id: $localize`:@@common.filterByTransactionId:Filter by this transaction ID`,
  user: $localize`:@@common.filterByUser:Filter by this user`,
  user_agent: $localize`:@@common.filterByUserAgent:Filter by this user agent`,
  user_name: $localize`:@@common.filterByUser:Filter by this user`,
  username: $localize`:@@common.filterByUser:Filter by this user`
};

/** The label of a cell's inline "filter by this value" button, falling back to the generic phrasing. */
export function filterValueTooltip(columnKey: string): string {
  return FILTER_VALUE_TOOLTIPS[columnKey] ?? $localize`:@@common.filterByValue:Filter by this value`;
}
