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
import { DialogService } from "@services/dialog/dialog.service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";

import { ReasonDetailDialog } from "../../reason-detail-dialog/reason-detail-dialog";
import { ReasonCell } from "./reason-cell";

describe("ReasonCell", () => {
  let component: ReasonCell;
  let fixture: ComponentFixture<ReasonCell>;
  let dialogService: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReasonCell],
      providers: [{ provide: DialogService, useClass: MockDialogService }]
    }).compileComponents();

    fixture = TestBed.createComponent(ReasonCell);
    component = fixture.componentInstance;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
  });

  function renderedReasons(): string[] {
    return Array.from(fixture.nativeElement.querySelectorAll(".reason-entry")).map((entry) =>
      (entry as HTMLElement).textContent!.trim()
    );
  }

  function detailButton(): HTMLButtonElement | null {
    return fixture.nativeElement.querySelector(".reason-detail-button");
  }

  function placeholder(): HTMLElement | null {
    return fixture.nativeElement.querySelector(".reason-placeholder");
  }

  it("lists every reason of the entry, not just the first", () => {
    fixture.componentRef.setInput("reasons", ["TOKEN_DISABLED", "WRONG_OTP"]);
    fixture.detectChanges();

    expect(renderedReasons()).toEqual(["TOKEN_DISABLED", "WRONG_OTP"]);
  });

  it("renders nothing for an entry that produced no reason", () => {
    fixture.componentRef.setInput("reasons", null);
    fixture.detectChanges();

    expect(renderedReasons()).toEqual([]);
    expect(detailButton()).toBeNull();
    // Neither a reason nor a detail: a placeholder on every success row would be noise.
    expect(component.showsPlaceholder()).toBe(false);
    expect(placeholder()).toBeNull();
  });

  it("points at the dialog when the entry has a detail but no reason of its own", () => {
    // What a wrong PIN looks like: the deciding token records no reason (PIN_FAIL already names the cause), while the
    // tokens the request never checked keep their findings in the detail.
    fixture.componentRef.setInput("reasons", []);
    fixture.componentRef.setInput("info", {
      reason_detail: { reasons: { OATH0001: "TOKEN_FAILCOUNT_EXCEEDED" } }
    });
    fixture.detectChanges();

    expect(renderedReasons()).toEqual([]);
    expect(component.showsPlaceholder()).toBe(true);
    expect(placeholder()?.textContent?.trim()).toBe("see details");
    expect(detailButton()).not.toBeNull();
  });

  it("stands aside once the entry carries a reason of its own", () => {
    fixture.componentRef.setInput("reasons", ["WRONG_OTP"]);
    fixture.componentRef.setInput("info", { reason_detail: { reasons: { OATH0001: "WRONG_OTP" } } });
    fixture.detectChanges();

    expect(component.showsPlaceholder()).toBe(false);
    expect(placeholder()).toBeNull();
  });

  it("offers no detail button while the entry carries no reason detail", () => {
    // A button that opened an empty dialog would be a promise the row cannot keep.
    fixture.componentRef.setInput("reasons", ["WRONG_OTP"]);
    fixture.componentRef.setInput("info", { client_label: "vpn" });
    fixture.detectChanges();

    expect(component.detail()).toBeNull();
    expect(detailButton()).toBeNull();
  });

  it("opens the dialog with the entry's own detail", () => {
    fixture.componentRef.setInput("reasons", ["WRONG_OTP"]);
    fixture.componentRef.setInput("info", {
      reason_detail: { reasons: { OATH0001: "WRONG_OTP" }, policies: ["deny_vpn"] }
    });
    fixture.detectChanges();

    detailButton()!.click();

    expect(dialogService.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({
        component: ReasonDetailDialog,
        data: {
          used: [{ serial: "OATH0001", reason: "WRONG_OTP" }],
          other: [],
          namesTokens: false,
          policies: ["deny_vpn"],
          eventType: ""
        }
      })
    );
  });

  it("splits the detail by the tokens the entry names", () => {
    // The table passes them for a failed entry only.
    fixture.componentRef.setInput("reasons", []);
    fixture.componentRef.setInput("info", {
      reason_detail: { reasons: { TOTP002: "TOKEN_DISABLED" } }
    });
    fixture.componentRef.setInput("usedSerials", ["OATH0001"]);
    fixture.detectChanges();

    expect(component.detail()).toEqual({
      used: [{ serial: "OATH0001", reason: "" }],
      other: [{ serial: "TOTP002", reason: "TOKEN_DISABLED" }],
      namesTokens: true,
      policies: []
    });
    // A row with a detail but no reason of its own still points at the dialog.
    expect(component.showsPlaceholder()).toBe(true);
  });

  it("names what the button opens, since it carries no visible text", () => {
    fixture.componentRef.setInput("info", { reason_detail: { policies: ["deny_vpn"] } });
    fixture.detectChanges();

    const button = detailButton()!;
    expect(button.getAttribute("aria-label")).toBe(component.detailLabel);
  });
});
