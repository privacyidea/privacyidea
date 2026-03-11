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
import { OtpValuesComponent } from "./otp-values.component";

describe("OtpValuesComponent", () => {
  let component: OtpValuesComponent;
  let fixture: ComponentFixture<OtpValuesComponent>;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    fixture = TestBed.createComponent(OtpValuesComponent);
    component = fixture.componentInstance;
  })

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("printOtps should open window", async () => {
      const mockPrintWindow = {
        document: { open: jest.fn(), write: jest.fn(), close: jest.fn() },
        focus: jest.fn(),
        print: jest.fn(),
        close: jest.fn()
      };
      jest.spyOn(window, "open").mockReturnValue(mockPrintWindow as any);
      component.printOtps();
      expect(window.open).toHaveBeenCalledWith("", "_blank", "width=800,height=600");
      expect(mockPrintWindow.document.open).toHaveBeenCalled();
      expect(mockPrintWindow.document.write).toHaveBeenCalled();
      expect(mockPrintWindow.document.close).toHaveBeenCalled();
      expect(mockPrintWindow.focus).toHaveBeenCalled();
      expect(mockPrintWindow.print).toHaveBeenCalled();
      expect(mockPrintWindow.close).toHaveBeenCalled();
    });
});