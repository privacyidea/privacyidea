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
import { parseReasonDetail } from "./reason-detail";

describe("parseReasonDetail", () => {
  it("reads the per-serial findings and the deciding policies of one entry", () => {
    expect(
      parseReasonDetail({
        reason_detail: {
          reasons: { OATH0001: "WRONG_OTP", TOTP002: "TOKEN_DISABLED" },
          policies: ["deny_vpn"]
        },
        client_label: "vpn"
      })
    ).toEqual({
      // No serial named, so there is nothing to contrast and every finding is the explanation.
      used: [
        { serial: "OATH0001", reason: "WRONG_OTP" },
        { serial: "TOTP002", reason: "TOKEN_DISABLED" }
      ],
      other: [],
      namesTokens: false,
      policies: ["deny_vpn"]
    });
  });

  it("keeps the half the request recorded, since each layer records only its own", () => {
    expect(parseReasonDetail({ reason_detail: { reasons: { OATH0001: "WRONG_OTP" } } })).toEqual({
      used: [{ serial: "OATH0001", reason: "WRONG_OTP" }],
      other: [],
      namesTokens: false,
      policies: []
    });
    expect(parseReasonDetail({ reason_detail: { policies: ["auth_max_fail"] } })).toEqual({
      used: [],
      other: [],
      namesTokens: false,
      policies: ["auth_max_fail"]
    });
  });

  it("splits the findings by the tokens the entry names", () => {
    // The tokens the attempt was made against explain the outcome; one the request never got to check is context.
    expect(
      parseReasonDetail({ reason_detail: { reasons: { OATH0001: "WRONG_OTP", TOTP002: "TOKEN_DISABLED" } } }, [
        "OATH0001"
      ])
    ).toEqual({
      used: [{ serial: "OATH0001", reason: "WRONG_OTP" }],
      other: [{ serial: "TOTP002", reason: "TOKEN_DISABLED" }],
      namesTokens: true,
      policies: []
    });
  });

  it("records that an entry names its tokens even where no other token was found wanting", () => {
    // What the group is does not depend on a second group existing (see the dialog's heading).
    expect(parseReasonDetail({ reason_detail: { reasons: { OATH0001: "WRONG_OTP" } } }, ["OATH0001"])).toEqual({
      used: [{ serial: "OATH0001", reason: "WRONG_OTP" }],
      other: [],
      namesTokens: true,
      policies: []
    });
  });

  it("names a token the entry used without a finding of its own", () => {
    // The normal shape of a wrong first factor: PASSWORD_FAIL names the credential, so the token records no reason
    // - and is exactly the one an admin is looking for.
    expect(
      parseReasonDetail({ reason_detail: { reasons: { TOTP002: "TOKEN_DISABLED" } } }, ["OATH0001", "WAN003"])
    ).toEqual({
      used: [
        { serial: "OATH0001", reason: "" },
        { serial: "WAN003", reason: "" }
      ],
      other: [{ serial: "TOTP002", reason: "TOKEN_DISABLED" }],
      namesTokens: true,
      policies: []
    });
  });

  it("reports nothing to show for an entry that only names tokens", () => {
    // The serials are already a column of the log, so a dialog repeating them adds nothing.
    expect(parseReasonDetail({ reason_detail: {} }, ["OATH0001"])).toBeNull();
    expect(parseReasonDetail({ client_label: "vpn" }, ["OATH0001"])).toBeNull();
  });

  it("reports nothing to show for an entry whose reasons nobody detailed", () => {
    // Which is what leaves the Reasons column without its dialog button.
    expect(parseReasonDetail(null)).toBeNull();
    expect(parseReasonDetail({})).toBeNull();
    expect(parseReasonDetail({ client_label: "vpn" })).toBeNull();
    expect(parseReasonDetail({ reason_detail: {} })).toBeNull();
    expect(parseReasonDetail({ reason_detail: { reasons: {}, policies: [] } })).toBeNull();
  });

  it("yields no detail for a value of an unexpected shape rather than a broken cell", () => {
    // other_info is a free-form JSON column, and the table's skeleton rows set every column to "".
    expect(parseReasonDetail("")).toBeNull();
    expect(parseReasonDetail(["reason_detail"])).toBeNull();
    expect(parseReasonDetail({ reason_detail: "WRONG_OTP" })).toBeNull();
    expect(parseReasonDetail({ reason_detail: { reasons: "WRONG_OTP" } })).toBeNull();
    expect(parseReasonDetail({ reason_detail: { reasons: { OATH0001: "WRONG_OTP" }, policies: "deny_vpn" } })).toEqual({
      used: [{ serial: "OATH0001", reason: "WRONG_OTP" }],
      other: [],
      namesTokens: false,
      policies: []
    });
  });

  it("renders a recorded value that is not a plain string rather than dropping it", () => {
    // A mislabelled reason is worth seeing: hiding it would hide that it was recorded that way.
    expect(
      parseReasonDetail({ reason_detail: { reasons: { OATH0001: { code: 3 }, TOTP002: 7, WAN003: null } } })
    ).toEqual({
      used: [
        { serial: "OATH0001", reason: '{"code":3}' },
        { serial: "TOTP002", reason: "7" },
        { serial: "WAN003", reason: "" }
      ],
      other: [],
      namesTokens: false,
      policies: []
    });
  });
});
