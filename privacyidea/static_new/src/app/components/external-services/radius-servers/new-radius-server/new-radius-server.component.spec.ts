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
import { NewRadiusServerComponent } from "./new-radius-server.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";
import { RadiusService } from "../../../../services/radius/radius.service";

describe("NewRadiusServerComponent", () => {
  let component: NewRadiusServerComponent;
  let fixture: ComponentFixture<NewRadiusServerComponent>;
  let radiusServiceMock: any;
  let dialogRefMock: any;
  let dialogMock: any;

  beforeEach(async () => {
    radiusServiceMock = {
      postRadiusServer: jest.fn().mockResolvedValue(true),
      testRadiusServer: jest.fn().mockResolvedValue(true),
    };

    dialogRefMock = {
      disableClose: false,
      backdropClick: jest.fn().mockReturnValue(of()),
      keydownEvents: jest.fn().mockReturnValue(of()),
      close: jest.fn()
    };

    dialogMock = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of(true) }),
    };

    await TestBed.configureTestingModule({
      imports: [NewRadiusServerComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: null },
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: RadiusService, useValue: radiusServiceMock },
      ]
    }).overrideComponent(NewRadiusServerComponent, {
      add: {
        providers: [
          { provide: MatDialog, useValue: dialogMock }
        ]
      }
    }).compileComponents();

    fixture = TestBed.createComponent(NewRadiusServerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form for create mode", () => {
    expect(component.isEditMode).toBe(false);
    expect(component.radiusForm.get("identifier")?.value).toBe("");
  });

  it("should call save when form is valid", async () => {
    component.radiusForm.patchValue({
      identifier: "test",
      server: "1.2.3.4",
      secret: "secret",
      port: 1812,
      timeout: 5,
      retries: 3
    });
    await component.save();
    expect(radiusServiceMock.postRadiusServer).toHaveBeenCalled();
    expect(dialogRefMock.close).toHaveBeenCalledWith(true);
  });

  it("should call test when form is valid", async () => {
    component.radiusForm.patchValue({
      identifier: "test",
      server: "1.2.3.4",
      secret: "secret",
      port: 1812,
      timeout: 5,
      retries: 3
    });
    await component.test();
    expect(radiusServiceMock.testRadiusServer).toHaveBeenCalled();
  });
});
