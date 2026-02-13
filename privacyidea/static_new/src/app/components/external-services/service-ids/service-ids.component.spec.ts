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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatDialogModule, MatDialog } from "@angular/material/dialog";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { provideRouter } from "@angular/router";
import { Subject } from "rxjs";
import { MockMatDialogRef } from "../../../../testing/mock-mat-dialog-ref";
import { MockDialogService } from "../../../../testing/mock-services";
import { DialogService } from "../../../services/dialog/dialog.service";
import { ServiceIdService } from "../../../services/service-id/service-id.service";
import { ServiceIdsComponent } from "./service-ids.component";

describe("ServiceIdsComponent", () => {
  let component: ServiceIdsComponent;
  let fixture: ComponentFixture<ServiceIdsComponent>;
  let serviceIdServiceMock: any;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;

  beforeEach(async () => {
    serviceIdServiceMock = {
      serviceIds: signal([
        { servicename: "service1", description: "desc1", id: 1 },
        { servicename: "service2", description: "desc2", id: 2 }
      ]),
      deleteServiceId: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [ServiceIdsComponent, NoopAnimationsModule, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ServiceIdService, useValue: serviceIdServiceMock },
        { provide: DialogService, useClass: MockDialogService }
      ]
    })
      .overrideComponent(ServiceIdsComponent, {
        add: {
          providers: [{ provide: MatDialog, useValue: { open: jest.fn() } }]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(ServiceIdsComponent);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    confirmClosed = new Subject();
    let dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display service IDs from service", () => {
    expect(component.serviceIdDataSource().data.length).toBe(2);
    expect(component.serviceIdDataSource().data[0].servicename).toBe("service1");
  });

  it("should filter service IDs", () => {
    component.onFilterInput("service1");
    expect(component.serviceIdDataSource().filter).toBe("service1");
  });

  it("should open edit dialog", () => {
    const dialog = fixture.debugElement.injector.get(MatDialog);
    const serviceId = serviceIdServiceMock.serviceIds()[0];
    component.openEditDialog(serviceId);
    expect(dialog.open).toHaveBeenCalled();
  });

  it("should delete service ID after confirmation", async () => {
    const serviceId = serviceIdServiceMock.serviceIds()[0];
    component.deleteServiceId(serviceId);
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();
    expect(serviceIdServiceMock.deleteServiceId).toHaveBeenCalledWith("service1");
  });
});
