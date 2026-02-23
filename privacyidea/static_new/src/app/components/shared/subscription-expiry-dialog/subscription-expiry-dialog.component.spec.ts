/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { SubscriptionExpiryDialogComponent, SubscriptionExpiryDialogData } from "./subscription-expiry-dialog.component";
import { MAT_DIALOG_DATA, MatDialogModule } from "@angular/material/dialog";
import { By } from "@angular/platform-browser";

const dialogData: SubscriptionExpiryDialogData = {
  items: [
    { application: "appA", date_till: "2026-03-10", timedelta: -10 },
    { application: "appB", date_till: "2026-02-20", timedelta: -1 }
  ]
};

describe("SubscriptionExpiryDialogComponent", () => {
  let fixture: ComponentFixture<SubscriptionExpiryDialogComponent>;
  let component: SubscriptionExpiryDialogComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SubscriptionExpiryDialogComponent, MatDialogModule],
      providers: [{ provide: MAT_DIALOG_DATA, useValue: dialogData }]
    }).compileComponents();

    fixture = TestBed.createComponent(SubscriptionExpiryDialogComponent);
    component = fixture.componentInstance;
  });

  it("should create", () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it("renders each item row with remaining days", () => {
    fixture.detectChanges();

    const rows = fixture.debugElement.queryAll(By.css(".row"));
    expect(rows.length).toBe(2);

    const text = fixture.nativeElement.textContent;
    expect(text).toContain("appA");
    expect(text).toContain("appB");
    expect(text).toContain("10");
    expect(text).toContain("1");
  });

  it("remainingDays() clamps positive timedelta to 0", () => {
    const value = component.remainingDays({ application: "x", date_till: "d", timedelta: 5 });
    expect(value).toBe(0);
  });
});
