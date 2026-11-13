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
import { QrCodeTextComponent } from "./qr-code-text.component";
import { axe } from "@testing/axe";

describe("QrCodeTextComponent", () => {
  let component: QrCodeTextComponent;
  let fixture: ComponentFixture<QrCodeTextComponent>;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    fixture = TestBed.createComponent(QrCodeTextComponent);
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("passes the axe accessibility checks", async () => {
    fixture.componentRef.setInput("tokenType", "hotp");
    fixture.componentRef.setInput("url", "otpauth://hotp/OATH0001?secret=GEZDGNBVGY3TQOJQ&counter=0");
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
