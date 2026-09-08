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
      tokens: [
        { serial: "OATH0001", reason: "WRONG_OTP" },
        { serial: "TOTP002", reason: "TOKEN_DISABLED" }
      ],
      policies: ["deny_vpn"]
    });
  });

  it("keeps the half the request recorded, since each layer records only its own", () => {
    expect(parseReasonDetail({ reason_detail: { reasons: { OATH0001: "WRONG_OTP" } } })).toEqual({
      tokens: [{ serial: "OATH0001", reason: "WRONG_OTP" }],
      policies: []
    });
    expect(parseReasonDetail({ reason_detail: { policies: ["auth_max_fail"] } })).toEqual({
      tokens: [],
      policies: ["auth_max_fail"]
    });
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
      tokens: [{ serial: "OATH0001", reason: "WRONG_OTP" }],
      policies: []
    });
  });

  it("renders a recorded value that is not a plain string rather than dropping it", () => {
    // A mislabelled reason is worth seeing: hiding it would hide that it was recorded that way.
    expect(
      parseReasonDetail({ reason_detail: { reasons: { OATH0001: { code: 3 }, TOTP002: 7, WAN003: null } } })
    ).toEqual({
      tokens: [
        { serial: "OATH0001", reason: '{"code":3}' },
        { serial: "TOTP002", reason: "7" },
        { serial: "WAN003", reason: "" }
      ],
      policies: []
    });
  });
});
