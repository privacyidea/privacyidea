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
import { NewServiceIdComponent } from "./new-service-id.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";
import { ServiceIdService } from "../../../../services/service-id/service-id.service";

describe("NewServiceIdComponent", () => {
  let component: NewServiceIdComponent;
  let fixture: ComponentFixture<NewServiceIdComponent>;
  let serviceIdServiceMock: any;
  let dialogRefMock: any;
  let dialogMock: any;

  beforeEach(async () => {
    serviceIdServiceMock = {
      postServiceId: jest.fn().mockResolvedValue(true),
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
      imports: [NewServiceIdComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: null },
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: ServiceIdService, useValue: serviceIdServiceMock },
      ]
    }).overrideComponent(NewServiceIdComponent, {
      add: {
        providers: [
          { provide: MatDialog, useValue: dialogMock }
        ]
      }
    }).compileComponents();

    fixture = TestBed.createComponent(NewServiceIdComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form for create mode", () => {
    expect(component.isEditMode).toBe(false);
    expect(component.serviceIdForm.get("servicename")?.value).toBe("");
  });

  it("should call save when form is valid", async () => {
    component.serviceIdForm.patchValue({
      servicename: "test",
      description: "desc"
    });
    await component.save();
    expect(serviceIdServiceMock.postServiceId).toHaveBeenCalled();
    expect(dialogRefMock.close).toHaveBeenCalledWith(true);
  });
});
