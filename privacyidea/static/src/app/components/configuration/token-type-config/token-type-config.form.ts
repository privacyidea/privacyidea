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

import { computed, linkedSignal, Signal } from "@angular/core";
import {
  applyEach,
  applyWhenValue,
  FieldTree,
  pattern,
  SchemaFn,
  SchemaPathTree,
  validate
} from "@angular/forms/signals";
import {
  DAYPASSWORD_HASHLIB,
  DAYPASSWORD_TIME_STEP,
  EMAIL_SMTP_SERVER_KEY,
  EMAIL_VALIDITY_TIME_KEY,
  HOTP_HASHLIB,
  QUESTION_CONFIG_PREFIX,
  QUESTION_NUMBER_OF_ANSWERS,
  RADIUS_SERVER,
  REMOTE_SERVER,
  REMOTE_VERIFY_SSL,
  SMS_GATEWAY,
  SMS_PROVIDER_TIMEOUT,
  TIQR_AUTH_SERVER,
  TIQR_INFO_URL,
  TIQR_LOGO_URL,
  TIQR_OCRASUITE,
  TIQR_REG_SERVER,
  TIQR_SERVICE_DISPLAYNAME,
  TIQR_SERVICE_IDENTIFIER,
  TOTP_HASHLIB,
  TOTP_TIME_SHIFT,
  TOTP_TIME_STEP,
  TOTP_TIME_WINDOW,
  U2F_APP_ID,
  WEBAUTHN_TRUST_ANCHOR_DIR,
  YUBICO_ID,
  YUBICO_SECRET,
  YUBICO_URL
} from "@constants/token.constants";
import { ERR, requiredNonBlank } from "@utils/form-rules.utils";
import { parseBooleanValue } from "@utils/parse-boolean-value";

/**
 * Model of the whole token type configuration form. `values` holds the system config entries in their wire
 * format (every value is a string), including entries no panel edits such as `yubikey.apiid.*` and the unrelated
 * system config. `verifySsl` is the boolean behind the Remote panel checkbox; the wire format is "True" / "False".
 */
export interface TokenTypeConfigModel {
  values: Record<string, string>;
  verifySsl: boolean;
}

export type TokenTypeConfigForm = FieldTree<TokenTypeConfigModel>;

const HOTP_KEYS = [HOTP_HASHLIB] as const;
export const TOTP_KEYS = [TOTP_TIME_STEP, TOTP_TIME_WINDOW, TOTP_HASHLIB, TOTP_TIME_SHIFT] as const;
const DAYPASSWORD_KEYS = [DAYPASSWORD_TIME_STEP, DAYPASSWORD_HASHLIB] as const;
const RADIUS_KEYS = [RADIUS_SERVER] as const;
const WEBAUTHN_KEYS = [WEBAUTHN_TRUST_ANCHOR_DIR] as const;
export const YUBICO_KEYS = [YUBICO_SECRET, YUBICO_ID, YUBICO_URL] as const;
const YUBICO_CREDENTIAL_KEYS = [YUBICO_ID, YUBICO_SECRET] as const;
const REMOTE_KEYS = [REMOTE_SERVER] as const;
export const SMS_KEYS = [SMS_GATEWAY, SMS_PROVIDER_TIMEOUT] as const;
export const TIQR_KEYS = [
  TIQR_REG_SERVER,
  TIQR_AUTH_SERVER,
  TIQR_SERVICE_DISPLAYNAME,
  TIQR_SERVICE_IDENTIFIER,
  TIQR_LOGO_URL,
  TIQR_OCRASUITE,
  TIQR_INFO_URL
] as const;
export const EMAIL_KEYS = [EMAIL_SMTP_SERVER_KEY, EMAIL_VALIDITY_TIME_KEY] as const;
const U2F_KEYS = [U2F_APP_ID] as const;

/**
 * The entries the panels bind to. The model holds each of them (empty when the backend has none), because a field
 * of a `Record` model exists only for a key the model holds.
 */
export const TOKEN_TYPE_CONFIG_KEYS: readonly string[] = [
  ...HOTP_KEYS,
  ...TOTP_KEYS,
  ...DAYPASSWORD_KEYS,
  ...RADIUS_KEYS,
  ...WEBAUTHN_KEYS,
  ...YUBICO_KEYS,
  ...REMOTE_KEYS,
  ...SMS_KEYS,
  ...TIQR_KEYS,
  ...EMAIL_KEYS,
  ...U2F_KEYS,
  QUESTION_NUMBER_OF_ANSWERS
];

/**
 * Entries the backend falls back to a default for (`yubico.url`, the DayPassword defaults, `tiqr.infoUrl`,
 * `question.num_answers`). An empty entry is left out of the saved config and deleted in the backend, because the
 * backend reads a stored empty string as a value and the default applies only to an absent entry.
 */
const OMIT_WHEN_EMPTY_KEYS: ReadonlySet<string> = new Set([
  YUBICO_URL,
  DAYPASSWORD_TIME_STEP,
  DAYPASSWORD_HASHLIB,
  TIQR_INFO_URL,
  QUESTION_NUMBER_OF_ANSWERS
]);

/** Digits only: the number of answers is a count, so a sign, a decimal point or an exponent is rejected. */
const WHOLE_NUMBER_PATTERN = /^\d+$/;

const PANEL_KEY_SET: ReadonlySet<string> = new Set(TOKEN_TYPE_CONFIG_KEYS);

/** True when the backend uses its own default for the entry while it is absent, so an empty entry is not saved. */
export function isOmittedWhenEmpty(key: string): boolean {
  return OMIT_WHEN_EMPTY_KEYS.has(key);
}

/** True when the entry is a question of the questionnaire token. */
export function isQuestionKey(key: string): boolean {
  return key.startsWith(QUESTION_CONFIG_PREFIX);
}

/** Builds the form model from the system config: every panel key is present and the SSL flag is a boolean. */
export function toTokenTypeConfigModel(config: Record<string, string>): TokenTypeConfigModel {
  const values = { ...config };
  delete values[REMOTE_VERIFY_SSL];
  for (const key of TOKEN_TYPE_CONFIG_KEYS) {
    values[key] ??= "";
  }
  return { values, verifySsl: parseBooleanValue(config[REMOTE_VERIFY_SSL]) };
}

/**
 * Builds the system config the model stands for. A panel entry that the backend does not hold and that is still
 * empty is left out, so a panel nobody touched adds nothing to the saved config. An empty entry the backend defaults
 * for is always left out. The SSL flag keeps the backend's own spelling while its meaning is unchanged.
 */
export function toSystemConfig(model: TokenTypeConfigModel, backend: Record<string, string>): Record<string, string> {
  const config: Record<string, string> = {};
  for (const [key, value] of Object.entries(model.values)) {
    if (value === "" && (isOmittedWhenEmpty(key) || (PANEL_KEY_SET.has(key) && !(key in backend)))) continue;
    config[key] = value;
  }
  if (REMOTE_VERIFY_SSL in backend && parseBooleanValue(backend[REMOTE_VERIFY_SSL]) === model.verifySsl) {
    config[REMOTE_VERIFY_SSL] = backend[REMOTE_VERIFY_SSL];
  } else if (model.verifySsl || REMOTE_VERIFY_SSL in backend) {
    config[REMOTE_VERIFY_SSL] = model.verifySsl ? "True" : "False";
  }
  return config;
}

/** The system config without the entries that are empty and that the backend defaults for, which hold nothing. */
export function withoutEmptyDefaulted(config: Record<string, string>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(config).filter(([key, value]) => !(value === "" && isOmittedWhenEmpty(key)))
  );
}

/** True when the two system configs differ in a key or a value. */
export function systemConfigDiffers(current: Record<string, string>, original: Record<string, string>): boolean {
  const keys = Object.keys(current);
  return keys.length !== Object.keys(original).length || keys.some((key) => current[key] !== original[key]);
}

/** True when `text` holds something other than whitespace. */
function isFilled(text: string | undefined): boolean {
  return (text ?? "").trim() !== "";
}

/**
 * Makes `requiredKeys` required while the panel is partly filled, which is when one of the panel's `keys` holds
 * text. An admin can leave a panel empty and still save the others.
 */
function requireWhenPanelFilled(
  values: SchemaPathTree<Record<string, string>>,
  keys: readonly string[],
  requiredKeys: readonly string[]
): void {
  applyWhenValue(
    values,
    (current) => keys.some((key) => isFilled(current[key])),
    (panel) => requiredKeys.forEach((key) => requiredNonBlank(panel[key]))
  );
}

/**
 * Rules of the token type configuration. Only an entry the backend cannot do without is required, and only while its
 * panel is partly filled, so an admin can leave a panel empty and still save the others: the Yubico API client ID
 * and key (a pair, the URL defaults to YubiCloud) once either is filled, and the TiQR registration server and logo
 * URL (the others default) once any TiQR entry is filled. The DayPassword entries and the number of answers
 * default in the backend, so they have no rule. The number of answers must be a whole number. A question of the
 * questionnaire must hold text as soon as its slot exists.
 */
export const tokenTypeConfigSchema: SchemaFn<TokenTypeConfigModel> = (path) => {
  requireWhenPanelFilled(path.values, YUBICO_CREDENTIAL_KEYS, YUBICO_CREDENTIAL_KEYS);
  requireWhenPanelFilled(path.values, TIQR_KEYS, [TIQR_REG_SERVER, TIQR_LOGO_URL]);
  pattern(path.values[QUESTION_NUMBER_OF_ANSWERS], WHOLE_NUMBER_PATTERN);
  applyEach(path.values, (value) => {
    validate(value, (ctx) => (isQuestionKey(ctx.key()) && !isFilled(ctx.value()) ? [{ kind: ERR.required }] : []));
  });
};

/**
 * The state of one panel for its header: `incomplete` is true while one of the panel's entries is invalid, which is
 * the reason Save is disabled; `revealed` turns true with it and stays true, so the panel opens once and the user
 * can still collapse it.
 */
export function panelCompleteness(
  config: () => TokenTypeConfigForm,
  keys: () => readonly string[]
): { incomplete: Signal<boolean>; revealed: Signal<boolean> } {
  const incomplete = computed(() => keys().some((key) => config().values[key]?.().invalid() ?? false));
  const revealed = linkedSignal<boolean, boolean>({
    source: incomplete,
    computation: (current, previous) => current || (previous?.value ?? false)
  });
  return { incomplete, revealed };
}
