/**
 * A list of token types that do should not show a QR code in the last enrollment step dialog.
 */
export const NO_QR_CODE_TOKEN_TYPES = [
  "registration",
  "paper",
  "tan",
  "spass",
  "email",
  "yubico",
  "yubikey",
  "sms",
  "applspec",
  "indexedsecret"
];

/**
 * A list of token types that should not show a regenerate button in the last enrollment step dialog.
 */
export const NO_REGENERATE_TOKEN_TYPES = [
  "registration",
  "spass",
  "email",
  "yubico",
  "yubikey",
  "sms",
  "applspec",
  "indexedsecret"
];

/**
 * A list of token types for which the regenerate button should show "Values" instead of "QR Code".
 */
export const REGENERATE_AS_VALUES_TOKEN_TYPES = ["paper", "tan"];