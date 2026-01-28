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
import { NewCaConnectorComponent } from "./new-ca-connector.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";
import { CaConnectorService } from "../../../../services/ca-connector/ca-connector.service";

describe("NewCaConnectorComponent", () => {
  let component: NewCaConnectorComponent;
  let fixture: ComponentFixture<NewCaConnectorComponent>;
  let caConnectorServiceMock: any;
  let dialogRefMock: any;
  let dialogMock: any;

  beforeEach(async () => {

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
      imports: [NewCaConnectorComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: null },
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: CaConnectorService, useValue: caConnectorServiceMock },
      ]
    }).overrideComponent(NewCaConnectorComponent, {
      add: {
        providers: [
          { provide: MatDialog, useValue: dialogMock }
        ]
      }
    }).compileComponents();

    fixture = TestBed.createComponent(NewCaConnectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form with local type by default", () => {
    expect(component.caConnectorForm.get("type")?.value).toBe("local");
    expect(component.caConnectorForm.get("cacert")?.validator).toBeDefined();
  });

  it("should update validators when type changes", () => {
    component.caConnectorForm.get("type")?.setValue("microsoft");
    expect(component.caConnectorForm.get("cacert")?.validator).toBeNull();
    expect(component.caConnectorForm.get("hostname")?.validator).toBeDefined();
  });

  it("should load available CAs for microsoft type", async () => {
    component.caConnectorForm.get("type")?.setValue("microsoft");
    component.caConnectorForm.patchValue({ hostname: "test", port: "123" });
    await component.loadAvailableCas();
    expect(caConnectorServiceMock.getCaSpecificOptions).toHaveBeenCalled();
    expect(component.availableCas()).toEqual(["CA1", "CA2"]);
  });

  it("should call save when form is valid", async () => {
    component.caConnectorForm.patchValue({
      connectorname: "test",
      type: "local",
      cacert: "cert",
      cakey: "key",
      "openssl.cnf": "cnf"
    });
    await component.save();
    expect(caConnectorServiceMock.postCaConnector).toHaveBeenCalled();
    expect(dialogRefMock.close).toHaveBeenCalledWith(true);
  });
});
