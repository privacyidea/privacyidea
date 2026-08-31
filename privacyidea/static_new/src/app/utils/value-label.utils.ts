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
  any_pin: $localize`:@@valueLabelAnyPin:Any PIN`,
  challenge: $localize`:@@valueLabelChallenge:Challenge`,
  clientwait: $localize`:@@valueLabelClientWait:Client wait`,
  damaged: $localize`:@@valueLabelDamaged:Damaged`,
  deactivated: $localize`:@@valueLabelDeactivated:Deactivated`,
  disabled: $localize`:@@valueLabelDeactivated:Deactivated`,
  deny_access: $localize`:@@valueLabelDenyAccess:Deny access`,
  grant_access: $localize`:@@valueLabelGrantAccess:Grant access`,
  locked: $localize`:@@valueLabelLocked:Locked`,
  lockscreen: $localize`:@@valueLabelLockScreen:Lock screen`,
  logged_in_user: $localize`:@@valueLabelLoggedInUser:Logged-in user`,
  lost: $localize`:@@valueLabelLost:Lost`,
  pin: $localize`:@@valueLabelPin:PIN`,
  reject: $localize`:@@valueLabelReject:Reject`,
  require_and_verify: $localize`:@@valueLabelRequireAndVerify:Require and verify`,
  revoked: $localize`:@@valueLabelRevoked:Revoked`,
  sha1: $localize`:@@valueLabelSha1:SHA-1`,
  sha256: $localize`:@@valueLabelSha256:SHA-256`,
  sha512: $localize`:@@valueLabelSha512:SHA-512`,
  tokenowner: $localize`:@@valueLabelTokenOwner:Token owner`,
  tokenpin: $localize`:@@valueLabelTokenPin:Token PIN`,
  userstore: $localize`:@@valueLabelUserStore:User store`
};

function normalizeValue(value: DisplayableValue): string {
  return String(value).toLowerCase();
}

function matchingBooleanPair(values: readonly DisplayableValue[] | undefined): readonly [string, string] | undefined {
  if (!values || values.length !== 2) return undefined;
  const normalized = values.map(normalizeValue);
  return BOOLEAN_VALUE_PAIRS.find((pair) => pair.every((value) => normalized.includes(value)));
}

function hasVocabularyEntry(values: readonly DisplayableValue[] | undefined): boolean {
  return !!values?.some((value) => normalizeValue(value) in VALUE_VOCABULARY);
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function valueDisplayLabel(
  value: DisplayableValue | undefined,
  values: readonly DisplayableValue[] | undefined,
  preset: BooleanValueLabelPreset = "switch"
): string {
  if (value === undefined || value === null) return "";
  const raw = String(value);
  const normalized = normalizeValue(value);
  if (!values?.some((candidate) => normalizeValue(candidate) === normalized)) return raw;

  const booleanPair = matchingBooleanPair(values);
  if (booleanPair) {
    const index = booleanPair.indexOf(normalized);
    if (index >= 0) return BOOLEAN_PRESET_LABELS[preset][index];
    return raw;
  }

  const vocabularyLabel = VALUE_VOCABULARY[normalized];
  if (vocabularyLabel) return vocabularyLabel;
  if (raw === normalized && hasVocabularyEntry(values)) return capitalize(raw);
  return raw;
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

export function valueDisplayLabels(
  values: readonly DisplayableValue[] | undefined,
  preset: BooleanValueLabelPreset = "switch"
): string[] | undefined {
  if (!values || values.length === 0) return undefined;
  const labels = values.map((value) => valueDisplayLabel(value, values, preset));
  return labels.some((label, index) => label !== String(values[index])) ? labels : undefined;
}
