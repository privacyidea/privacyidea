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

// The key the backend records the reason detail under inside an entry's other_info (REASON_DETAIL_INFO_KEY in
// privacyidea/lib/conditional_access/authentication_event_types.py).
//
// The detail explains the row's *reasons*, so it belongs to the Reasons column and not to the Info cell, which skips
// it (see InfoCell): a nested map in a narrow JSON column can only be folded into a one-line dump, while the Reasons
// column can offer it as the serial/reason pairs it actually is (see ReasonCell and ReasonDetailDialog).
export const REASON_DETAIL_INFO_KEY = "reason_detail";

// One token's finding: what this request found the token with that serial to be. The serials are the keys of the
// backend's per-serial map (see build_reason_detail).
export interface TokenReason {
  serial: string;
  reason: string;
}

// The reason detail of one entry. Either half can be empty: each layer records only its own - the token layer the
// per-serial findings, a policy layer the rules that decided - and they are merged into one dict on the way into the
// row (see build_reason_detail and ConditionalAccessContext.reclassify).
export interface ReasonDetail {
  tokens: TokenReason[];
  policies: string[];
}

/**
 * The reason detail of an entry's *other_info*, or `null` when it carries nothing to show - which is what an entry
 * whose reasons nobody detailed looks like, and the answer that leaves the Reasons column without its dialog button.
 *
 * `other_info` is a free-form JSON column, so every level is checked rather than trusted (and the table's skeleton
 * rows set *every* column to `""`, so even "a record" is not a promise the loading state keeps). Anything of an
 * unexpected shape yields no detail rather than a broken cell.
 */
export function parseReasonDetail(info: unknown): ReasonDetail | null {
  if (!isRecord(info)) return null;
  const detail = info[REASON_DETAIL_INFO_KEY];
  if (!isRecord(detail)) return null;
  const reasons = detail["reasons"];
  const tokens = isRecord(reasons)
    ? Object.entries(reasons).map(([serial, reason]) => ({ serial, reason: asText(reason) }))
    : [];
  const policies = Array.isArray(detail["policies"]) ? detail["policies"].map((policy) => asText(policy)) : [];
  return tokens.length || policies.length ? { tokens, policies } : null;
}

// Renders whatever the column holds: the backend writes a string per serial and a list of names, and a value that is
// neither is still shown - a mislabelled reason is worth seeing, and dropping it would hide that it was recorded.
function asText(value: unknown): string {
  if (value === null || value === undefined) return "";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
