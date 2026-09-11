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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";

import { ReasonDetail, ReasonDetailDialogData } from "../reason-detail";
import { ReasonDetailDialog } from "./reason-detail-dialog";

describe("ReasonDetailDialog", () => {
  let fixture: ComponentFixture<ReasonDetailDialog>;

  async function render(detail: ReasonDetail, eventType = "MFA_FAIL"): Promise<void> {
    const data: ReasonDetailDialogData = { ...detail, eventType };
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ReasonDetailDialog],
      providers: [
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: data }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ReasonDetailDialog);
    fixture.detectChanges();
  }

  function rows(selector = ".reason-detail-table"): string[][] {
    return Array.from(fixture.nativeElement.querySelectorAll(`${selector} tbody tr`)).map((row) =>
      Array.from((row as HTMLElement).querySelectorAll("td")).map((cell) => cell.textContent!.trim())
    );
  }

  function serials(): string[] {
    return Array.from(fixture.nativeElement.querySelectorAll(".reason-detail-serials li")).map((item) =>
      (item as HTMLElement).textContent!.trim()
    );
  }

  function hints(): string[] {
    return Array.from(fixture.nativeElement.querySelectorAll(".reason-detail-hint")).map((hint) =>
      (hint as HTMLElement).textContent!.trim()
    );
  }

  function headings(): string[] {
    return Array.from(fixture.nativeElement.querySelectorAll(".reason-detail-heading")).map((heading) =>
      (heading as HTMLElement).textContent!.trim()
    );
  }

  it("shows each finding as its serial and its reason rather than as one line of JSON", async () => {
    await render({
      used: [
        { serial: "OATH0001", reason: "WRONG_OTP" },
        { serial: "TOTP002", reason: "TOKEN_DISABLED" }
      ],
      other: [],
      namesTokens: false,
      policies: []
    });

    expect(rows()).toEqual([
      ["OATH0001", "WRONG_OTP"],
      ["TOTP002", "TOKEN_DISABLED"]
    ]);
    // The entry names no token, so the findings are shown as the one table they explain the row by.
    expect(headings()).toEqual(["Tokens"]);
    // Nothing about policies for a request that named none.
    expect(fixture.nativeElement.querySelector(".reason-detail-policies")).toBeNull();
  });

  it("lists the deciding policies, and leaves out the token table when no token was found wanting", async () => {
    await render({ used: [], other: [], namesTokens: false, policies: ["deny_vpn", "auth_max_fail"] });

    expect(fixture.nativeElement.querySelector(".reason-detail-table")).toBeNull();
    const policies: HTMLLIElement[] = Array.from(fixture.nativeElement.querySelectorAll(".reason-detail-policies li"));
    expect(policies.map((policy) => policy.textContent!.trim())).toEqual(["deny_vpn", "auth_max_fail"]);
  });

  it("shows both halves when the request recorded both", async () => {
    await render({
      used: [{ serial: "OATH0001", reason: "WRONG_OTP" }],
      other: [],
      namesTokens: false,
      policies: ["deny_vpn"]
    });

    expect(rows()).toEqual([["OATH0001", "WRONG_OTP"]]);
    expect(fixture.nativeElement.querySelectorAll(".reason-detail-policies li").length).toBe(1);
  });

  it("says the group is the tokens used even where no other token was found wanting", async () => {
    // The heading follows what the entry named, not whether a second group exists.
    await render({
      used: [{ serial: "OATH0001", reason: "WRONG_OTP" }],
      other: [],
      namesTokens: true,
      policies: []
    });

    expect(headings()).toEqual(["Tokens used for this attempt"]);
    expect(rows()).toEqual([["OATH0001", "WRONG_OTP"]]);
  });

  it("separates the tokens the attempt was made against from those that had no part in it", async () => {
    // A wrong password beside a disabled token: as one list, being disabled would look like the reason.
    await render(
      {
        used: [{ serial: "OATH0001", reason: "" }],
        other: [{ serial: "TOTP002", reason: "TOKEN_DISABLED" }],
        namesTokens: true,
        policies: []
      },
      "PASSWORD_FAIL"
    );

    expect(headings()).toEqual(["Tokens used for this attempt", "Other tokens of the user"]);
    // No token records a finding for a wrong password, so the used ones are listed as serials and the event type
    // says what came of them.
    expect(serials()).toEqual(["OATH0001"]);
    expect(hints()[0]).toContain("PASSWORD_FAIL");
    // The bystanders keep the table, since they have something to put in it.
    expect(rows()).toEqual([["TOTP002", "TOKEN_DISABLED"]]);
  });

  it("keeps the reason of a used token that recorded one", async () => {
    // A wrong OTP does record a finding (WRONG_OTP), so that group is a table rather than a bare list of serials.
    // A used token beside it with no finding of its own gets a dash instead of an empty cell.
    await render({
      used: [
        { serial: "OATH0001", reason: "WRONG_OTP" },
        { serial: "WAN003", reason: "" }
      ],
      other: [{ serial: "TOTP002", reason: "TOKEN_DISABLED" }],
      namesTokens: true,
      policies: []
    });

    expect(fixture.nativeElement.querySelector(".reason-detail-serials")).toBeNull();
    expect(rows()).toEqual([
      ["OATH0001", "WRONG_OTP"],
      ["WAN003", "\u2014"],
      ["TOTP002", "TOKEN_DISABLED"]
    ]);
  });
});
