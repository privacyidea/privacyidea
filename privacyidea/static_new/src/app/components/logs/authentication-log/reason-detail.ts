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
// backend's per-serial map (see build_reason_detail); *reason* is empty for a token the row names but recorded no
// finding for, the normal shape of a wrong first factor (the event type already names the credential).
export interface TokenReason {
  serial: string;
  reason: string;
}

// The reason detail of one entry. Either half can be empty: each layer records only its own - the token layer the
// per-serial findings, a policy layer the rules that decided - and they are merged into one dict on the way into the
// row (see build_reason_detail and ConditionalAccessContext.reclassify).
//
// *used* and *other* split those findings by the tokens the row names, which for a failure are the ones the attempt
// was made against (see AUTH_EVENT_SERIALS_KEY): a token that was disabled or past its failcounter never got that
// far, so its finding is context rather than the explanation. Where the row names none - NO_USABLE_TOKEN - there is
// nothing to contrast and every finding stays in *used*.
//
// *namesTokens* says which of those two *used* is, recorded rather than guessed from ``other.length``: a row can name
// its tokens and still have no finding on any other one (a single wrong OTP, a policy denying a valid
// authentication), and that group is still "the tokens used".
export interface ReasonDetail {
  used: TokenReason[];
  other: TokenReason[];
  namesTokens: boolean;
  policies: string[];
}

// What the dialog is handed: the entry's detail plus the event type it explains. The classification is what stands in
// for a finding where a used token has none of its own - a wrong first factor is logged as PASSWORD_FAIL or PIN_FAIL,
// which already names the credential that did not match - so the dialog can say what came of those tokens instead of
// showing them against an empty column.
export interface ReasonDetailDialogData extends ReasonDetail {
  eventType: string;
}

/**
 * The reason detail of an entry's *other_info*, or `null` when it carries nothing to show - which is what an entry
 * whose reasons nobody detailed looks like, and the answer that leaves the Reasons column without its dialog button.
 *
 * `other_info` is a free-form JSON column, so every level is checked rather than trusted (and the table's skeleton
 * rows set *every* column to `""`, so even "a record" is not a promise the loading state keeps). Anything of an
 * unexpected shape yields no detail rather than a broken cell.
 *
 * *usedSerials* are the tokens the row names, passed only for a failed entry (see ReasonDetail). One with no finding
 * still becomes a row of *used*: "this token was used and nothing else was found about it" is the answer for a wrong
 * PIN or password.
 *
 * Findings or policies are what make a detail worth opening; naming tokens does not, since the serials are already a
 * column of the log.
 */
export function parseReasonDetail(info: unknown, usedSerials: string[] = []): ReasonDetail | null {
  if (!isRecord(info)) return null;
  const detail = info[REASON_DETAIL_INFO_KEY];
  if (!isRecord(detail)) return null;
  const reasons = detail["reasons"];
  const findings = isRecord(reasons)
    ? Object.entries(reasons).map(([serial, reason]) => ({ serial, reason: asText(reason) }))
    : [];
  const policies = Array.isArray(detail["policies"]) ? detail["policies"].map((policy) => asText(policy)) : [];
  if (!findings.length && !policies.length) return null;

  const used = usedSerials.map((serial) => ({
    serial,
    reason: findings.find((finding) => finding.serial === serial)?.reason ?? ""
  }));
  const other = findings.filter((finding) => !usedSerials.includes(finding.serial));
  // Without named serials there is nothing to contrast: every finding is the explanation, so it stays in *used* and
  // the dialog renders it as a single table.
  return usedSerials.length
    ? { used, other, namesTokens: true, policies }
    : { used: findings, other: [], namesTokens: false, policies };
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
