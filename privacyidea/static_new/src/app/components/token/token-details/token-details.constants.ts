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
export const TIMESTAMP_INFO_KEYS = ["creation_date", "assignment_date", "last_auth"] as const;
export const USER_TIMESTAMP_INFO_KEYS = ["assignment_date"] as const;

type TokenDetailGroup = "identity" | "counters" | "assignment";

export const tokenDetailsKeyMap: { key: string; label: string; group: TokenDetailGroup }[] = [
  { key: "tokentype", label: "Type", group: "identity" },
  { key: "active", label: "Status", group: "identity" },
  { key: "rollout_state", label: "Rollout State", group: "identity" },
  { key: "failcount", label: "Fail Count", group: "identity" },
  { key: "creation_date", label: "Created", group: "identity" },
  { key: "last_auth", label: "Last Authentication", group: "identity" },
  { key: "maxfail", label: "Max Count", group: "counters" },
  { key: "otplen", label: "OTP Length", group: "counters" },
  { key: "count_window", label: "Count Window", group: "counters" },
  { key: "sync_window", label: "Sync Window", group: "counters" },
  { key: "count", label: "Count", group: "counters" },
  { key: "description", label: "Description", group: "assignment" },
  { key: "realms", label: "Token Realms", group: "assignment" },
  { key: "tokengroup", label: "Token Groups", group: "assignment" },
  { key: "container_serial", label: "Container Serial", group: "assignment" }
];

export function formatTokenTimestamp(value: string | undefined): string | undefined {
  if (value === undefined || value === "") return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export const tokenDetailsRightsMap = [
  { key: "maxfail", right: "set" },
  { key: "count_window", right: "set" },
  { key: "sync_window", right: "set" },
  { key: "description", right: "setdescription" },
  { key: "realms", right: "tokenrealms" },
  { key: "tokengroup", right: "tokengroups" },
  { key: "container_serial", right: "container_add_token" }
];

export const userDetailsKeyMap = [
  { key: "username", label: "User" },
  { key: "user_realm", label: "Realm" },
  { key: "assignment_date", label: "Last Assigned" },
  { key: "resolver", label: "Resolver" },
  { key: "user_id", label: "User ID" }
];

export const infoDetailsKeyMap = [{ key: "info", label: "Information" }];
