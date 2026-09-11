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
import {
  ConditionalAccessDryRunOffDialogComponent,
  ConditionalAccessDryRunOffDialogData
} from "./conditional-access-dry-run-off-dialog.component";

describe("ConditionalAccessDryRunOffDialogComponent", () => {
  let component: ConditionalAccessDryRunOffDialogComponent;
  let fixture: ComponentFixture<ConditionalAccessDryRunOffDialogComponent>;
  let dialogRef: MockMatDialogRef<unknown, unknown>;

  const data: ConditionalAccessDryRunOffDialogData = { policyNames: ["My Policy"] };

  beforeEach(async () => {
    dialogRef = new MockMatDialogRef<unknown, unknown>();
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessDryRunOffDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: data },
        { provide: MatDialogRef, useValue: dialogRef }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionalAccessDryRunOffDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("mentions the policy name", () => {
    const text = (fixture.nativeElement as HTMLElement).textContent ?? "";
    expect(text).toContain("My Policy");
  });

  it("defaults to counting only from now on", () => {
    component.confirm();
    expect(dialogRef.close).toHaveBeenCalledWith({ resetCounters: true });
  });

  it("counts the events already in the window when the checkbox is checked", () => {
    component.countPastEvents.set(true);
    component.confirm();
    expect(dialogRef.close).toHaveBeenCalledWith({ resetCounters: false });
  });

  // The risk is what makes the checkbox a deliberate choice, so it is stated up front rather than
  // revealed once the box is already ticked.
  it("spells out the consequence of counting the older events", () => {
    const consequence = (fixture.nativeElement as HTMLElement).querySelector(".consequence")?.textContent ?? "";
    expect(consequence).toContain("stays silent");
  });

  it("closes with undefined on cancel", () => {
    component.cancel();
    expect(dialogRef.close).toHaveBeenCalledWith(undefined);
  });
});

describe("ConditionalAccessDryRunOffDialogComponent with multiple policies", () => {
  let fixture: ComponentFixture<ConditionalAccessDryRunOffDialogComponent>;

  const data: ConditionalAccessDryRunOffDialogData = { policyNames: ["Policy A", "Policy B"] };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessDryRunOffDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: data },
        { provide: MatDialogRef, useValue: new MockMatDialogRef<unknown, unknown>() }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionalAccessDryRunOffDialogComponent);
    fixture.detectChanges();
  });

  it("lists every policy name", () => {
    const text = (fixture.nativeElement as HTMLElement).textContent ?? "";
    expect(text).toContain("Policy A");
    expect(text).toContain("Policy B");
  });
});
