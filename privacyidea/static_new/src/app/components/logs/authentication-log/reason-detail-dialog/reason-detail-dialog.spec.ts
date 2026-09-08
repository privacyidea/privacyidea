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

import { ReasonDetail } from "../reason-detail";
import { ReasonDetailDialog } from "./reason-detail-dialog";

describe("ReasonDetailDialog", () => {
  let fixture: ComponentFixture<ReasonDetailDialog>;

  async function render(data: ReasonDetail): Promise<void> {
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

  function rows(): string[][] {
    return Array.from(fixture.nativeElement.querySelectorAll(".reason-detail-table tbody tr")).map((row) =>
      Array.from((row as HTMLElement).querySelectorAll("td")).map((cell) => cell.textContent!.trim())
    );
  }

  it("shows each finding as its serial and its reason rather than as one line of JSON", async () => {
    await render({
      tokens: [
        { serial: "OATH0001", reason: "WRONG_OTP" },
        { serial: "TOTP002", reason: "TOKEN_DISABLED" }
      ],
      policies: []
    });

    expect(rows()).toEqual([
      ["OATH0001", "WRONG_OTP"],
      ["TOTP002", "TOKEN_DISABLED"]
    ]);
    // Nothing about policies for a request that named none.
    expect(fixture.nativeElement.querySelector(".reason-detail-policies")).toBeNull();
  });

  it("lists the deciding policies, and leaves out the token table when no token was found wanting", async () => {
    await render({ tokens: [], policies: ["deny_vpn", "auth_max_fail"] });

    expect(fixture.nativeElement.querySelector(".reason-detail-table")).toBeNull();
    const policies: HTMLLIElement[] = Array.from(fixture.nativeElement.querySelectorAll(".reason-detail-policies li"));
    expect(policies.map((policy) => policy.textContent!.trim())).toEqual(["deny_vpn", "auth_max_fail"]);
  });

  it("shows both halves when the request recorded both", async () => {
    await render({ tokens: [{ serial: "OATH0001", reason: "WRONG_OTP" }], policies: ["deny_vpn"] });

    expect(rows()).toEqual([["OATH0001", "WRONG_OTP"]]);
    expect(fixture.nativeElement.querySelectorAll(".reason-detail-policies li").length).toBe(1);
  });
});
