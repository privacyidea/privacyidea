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
import { SmsGatewaysComponent } from "./sms-gateways.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatDialog, MatDialogModule } from "@angular/material/dialog";
import { SmsGatewayService } from "../../../services/sms-gateway/sms-gateway.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { signal } from "@angular/core";
import { MockDialogService } from "../../../../testing/mock-services";
import { Subject } from "rxjs";
import { MockMatDialogRef } from "../../../../testing/mock-mat-dialog-ref";
import { SaveAndExitDialogResult } from "../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";

describe("SmsGatewaysComponent", () => {
  let component: SmsGatewaysComponent;
  let fixture: ComponentFixture<SmsGatewaysComponent>;
  let smsGatewayServiceMock: any;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<SaveAndExitDialogResult>;

  beforeEach(async () => {
    smsGatewayServiceMock = {
      smsGateways: signal([
        { name: "gw1", providermodule: "mod1" },
        { name: "gw2", providermodule: "mod2" }
      ]),
      deleteSmsGateway: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [SmsGatewaysComponent, NoopAnimationsModule, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SmsGatewayService, useValue: smsGatewayServiceMock },
        { provide: DialogService, useClass: MockDialogService }
      ]
    })
      .overrideComponent(SmsGatewaysComponent, {
        add: {
          providers: [{ provide: MatDialog, useValue: { open: jest.fn() } }]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(SmsGatewaysComponent);
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

  it("should display gateways from service", () => {
    expect(component.smsDataSource().data.length).toBe(2);
    expect(component.smsDataSource().data[0].name).toBe("gw1");
  });

  it("should filter gateways", () => {
    component.onFilterInput("gw1");
    expect(component.smsDataSource().filter).toBe("gw1");
  });

  it("should open edit dialog", () => {
    const dialog = fixture.debugElement.injector.get(MatDialog);
    const gateway = smsGatewayServiceMock.smsGateways()[0];
    component.openEditDialog(gateway);
    expect(dialog.open).toHaveBeenCalled();
  });

  it("should delete gateway after confirmation", () => {
    const gateway = smsGatewayServiceMock.smsGateways()[0];
    component.deleteGateway(gateway);
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next("discard");
    confirmClosed.complete();
    expect(smsGatewayServiceMock.deleteSmsGateway).toHaveBeenCalledWith("gw1");
  });
});
