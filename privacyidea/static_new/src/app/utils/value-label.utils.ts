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

import { tokenTypeLabel } from "./token.utils";

export type DisplayableValue = string | number | boolean;

export type BooleanValueLabelPreset = "switch" | "predicate";

const BOOLEAN_VALUE_PAIRS: readonly (readonly [string, string])[] = [
  ["0", "1"],
  ["false", "true"]
];

const BOOLEAN_PRESET_LABELS: Record<BooleanValueLabelPreset, readonly [string, string]> = {
  switch: [$localize`:@@valueLabelOff:Off`, $localize`:@@valueLabelOn:On`],
  predicate: [$localize`:@@valueLabelNo:No`, $localize`:@@valueLabelYes:Yes`]
};

const VALUE_VOCABULARY: Record<string, string> = {
  accept: $localize`:@@valueLabelAccept:Accept`,
  active: $localize`:@@valueLabelActive:Active`,
  admin: $localize`:@@valueLabelAdministrator:Administrator`,
  "admin realm": $localize`:@@valueLabelAdminRealm:Admin realm`,
  allow: $localize`:@@valueLabelAllowed:Allowed`,
  allowed: $localize`:@@valueLabelAllowed:Allowed`,
  any: $localize`:@@valueLabelAny:Any`,
  any_pin: $localize`:@@valueLabelAnyPin:Any PIN`,
  background: $localize`:@@valueLabelInBackground:In background`,
  biometric: $localize`:@@valueLabelBiometric:Biometric`,
  broken: $localize`:@@valueLabelBroken:Broken`,
  challenge: $localize`:@@valueLabelChallenge:Challenge`,
  clientwait: $localize`:@@valueLabelClientWait:Client wait`,
  damaged: $localize`:@@valueLabelDamaged:Damaged`,
  deactivated: $localize`:@@valueLabelDeactivated:Deactivated`,
  declined: $localize`:@@valueLabelDeclined:Declined`,
  denied: $localize`:@@valueLabelDenied:Denied`,
  deny_access: $localize`:@@valueLabelDenyAccess:Deny access`,
  disable: $localize`:@@valueLabelDisabled:Disabled`,
  disabled: $localize`:@@valueLabelDeactivated:Deactivated`,
  email: $localize`:@@valueLabelEmail:Email`,
  enrolled: $localize`:@@valueLabelEnrolled:Enrolled`,
  failed: $localize`:@@valueLabelFailed:Failed`,
  force: $localize`:@@valueLabelForced:Forced`,
  generic: $localize`:@@valueLabelGeneric:Generic`,
  grant_access: $localize`:@@valueLabelGrantAccess:Grant access`,
  hide: $localize`:@@valueLabelHide:Hide`,
  html: "HTML",
  ignore: $localize`:@@valueLabelIgnore:Ignore`,
  "internal admin": $localize`:@@valueLabelInternalAdmin:Internal admin`,
  locked: $localize`:@@valueLabelLocked:Locked`,
  lockscreen: $localize`:@@valueLabelLockScreen:Lock screen`,
  logged_in_user: $localize`:@@valueLabelLoggedInUser:Logged-in user`,
  logout: $localize`:@@valueLabelLogout:Logout`,
  lost: $localize`:@@valueLabelLost:Lost`,
  luks: "LUKS",
  none: $localize`:@@valueLabelNone:None`,
  offline: $localize`:@@valueLabelOffline:Offline`,
  pending: $localize`:@@valueLabelPending:Pending`,
  pin: $localize`:@@valueLabelPin:PIN`,
  plain: $localize`:@@valueLabelPlainText:Plain text`,
  privacyidea: "privacyIDEA",
  reject: $localize`:@@valueLabelReject:Reject`,
  require_and_verify: $localize`:@@valueLabelRequireAndVerify:Require and verify`,
  revoked: $localize`:@@valueLabelRevoked:Revoked`,
  sha1: "SHA-1",
  sha256: "SHA-256",
  sha512: "SHA-512",
  show: $localize`:@@valueLabelShow:Show`,
  smartphone: $localize`:@@valueLabelSmartphone:Smartphone`,
  ssh: "SSH",
  tokenowner: $localize`:@@valueLabelTokenOwner:Token owner`,
  tokenpin: $localize`:@@valueLabelTokenPin:Token PIN`,
  user: $localize`:@@valueLabelUser:User`,
  userstore: $localize`:@@valueLabelUserStore:User store`,
  verify: $localize`:@@valueLabelVerify:Verify`,
  wait: $localize`:@@valueLabelWait:Wait`,
  yubikey: "Yubikey"
};

/**
 * Policy actions whose allowed values the backend spells out as constants, so the vocabulary may be
 * applied to them. Every other action is left alone: realms, resolvers, RADIUS and SMTP identifiers
 * reach the same dropdowns (see get_static_policy_definitions), and a name the installation chose
 * must stay readable. A missing entry here only costs a nicer label, a wrong one renames a name.
 */
export const POLICY_VOCABULARY_ACTIONS: ReadonlySet<string> = new Set([
  "autoassignment",
  "daypassword_hashlib",
  "hashlib",
  "hotp_hashlib",
  "login_mode",
  "otppin",
  "remote_user",
  "timeout_action",
  "totp_hashlib"
]);

export const TOKEN_STATE_VALUES = ["active", "deactivated", "revoked", "locked"] as const;

export const CONTAINER_STATE_VALUES = ["active", "disabled", "lost", "damaged"] as const;

export const AUTHENTICATION_VALUES = ["accept", "challenge", "reject", "declined"] as const;

export const ROLLOUT_STATE_VALUES = [
  "clientwait",
  "pending",
  "verify",
  "enrolled",
  "broken",
  "failed",
  "denied"
] as const;

function normalizeValue(value: DisplayableValue): string {
  return String(value).toLowerCase();
}

function matchingBooleanPair(values: readonly DisplayableValue[] | undefined): readonly [string, string] | undefined {
  if (!values || values.length !== 2) return undefined;
  const normalized = values.map(normalizeValue);
  return BOOLEAN_VALUE_PAIRS.find((pair) => pair.every((value) => normalized.includes(value)));
}

/**
 * True when every value of the list carries a vocabulary label. Only then is the list a closed
 * vocabulary the backend spells out, and not a list of names the installation defines itself
 * (realms, resolvers, server configurations, template names) which must be shown verbatim.
 */
function isClosedVocabulary(values: readonly DisplayableValue[] | undefined): boolean {
  return !!values?.length && values.every((value) => normalizeValue(value) in VALUE_VOCABULARY);
}

function holdsTokenTypes(values: readonly DisplayableValue[] | undefined): boolean {
  const tokenTypeCount = values?.filter((value) => !!tokenTypeLabel(normalizeValue(value))).length ?? 0;
  return tokenTypeCount >= 2;
}

export interface ValueLabelOptions {
  preset?: BooleanValueLabelPreset;
  /**
   * Consult the value vocabulary. Off by default, because a list of allowed values alone does not
   * say where it comes from: realms, resolvers, token groups, SMS gateway and server identifiers
   * reach the same dropdowns and are named by the installation, so a token group called "offline"
   * or a realm called "admin" would be renamed. Only a caller that knows its list is a fixed
   * backend enum may turn this on.
   */
  vocabulary?: boolean;
}

export function valueDisplayLabel(
  value: DisplayableValue | undefined | null,
  values: readonly DisplayableValue[] | undefined,
  options: ValueLabelOptions = {}
): string {
  if (value === undefined || value === null) return "";
  const raw = String(value);
  const normalized = normalizeValue(value);
  if (!values?.some((candidate) => normalizeValue(candidate) === normalized)) return raw;

  const booleanPair = matchingBooleanPair(values);
  if (booleanPair) {
    const index = booleanPair.indexOf(normalized);
    if (index >= 0) return BOOLEAN_PRESET_LABELS[options.preset ?? "switch"][index];
    return raw;
  }

  if (holdsTokenTypes(values)) {
    const tokenLabel = tokenTypeLabel(normalized);
    if (tokenLabel) return tokenLabel;
  }

  if (options.vocabulary && isClosedVocabulary(values)) return VALUE_VOCABULARY[normalized];
  return raw;
}

/** Display label of a token state ("active", "deactivated", "revoked", "locked"). */
export function tokenStateLabel(state: string): string {
  return valueDisplayLabel(state, TOKEN_STATE_VALUES, { vocabulary: true });
}

/** Display label of a container state ("active", "disabled", "lost", "damaged"). */
export function containerStateLabel(state: string | undefined | null): string {
  return valueDisplayLabel(state, CONTAINER_STATE_VALUES, { vocabulary: true });
}

export function booleanDisplayLabel(
  value: DisplayableValue | undefined | null,
  preset: BooleanValueLabelPreset = "switch"
): string {
  if (value === undefined || value === null || value === "") return "";
  const normalized = normalizeValue(value);
  const pair = BOOLEAN_VALUE_PAIRS.find((candidate) => candidate.includes(normalized));
  if (!pair) return String(value);
  return BOOLEAN_PRESET_LABELS[preset][pair.indexOf(normalized)];
}

/**
 * Labels of the whole list, or undefined when no value maps to a label of its own. Consumers read
 * that as "render the raw values" - see the `labels` input of the selector buttons.
 */
export function valueDisplayLabels(
  values: readonly DisplayableValue[] | undefined,
  options: ValueLabelOptions = {}
): string[] | undefined {
  if (!values || values.length === 0) return undefined;
  const labels = values.map((value) => valueDisplayLabel(value, values, options));
  return labels.some((label, index) => label !== String(values[index])) ? labels : undefined;
}

export interface LabeledValue<T extends DisplayableValue = DisplayableValue> {
  value: T;
  label: string;
}

/** Pairs every value with its label, for option lists that bind the value and the text separately. */
export function labeledOptions<T extends DisplayableValue>(
  values: readonly T[] | undefined,
  options: ValueLabelOptions = {}
): LabeledValue<T>[] {
  return (values ?? []).map((value) => ({ value, label: valueDisplayLabel(value, values, options) }));
}
