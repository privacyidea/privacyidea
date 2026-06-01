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
import { MatDialog } from "@angular/material/dialog";
import { AuthService } from "@services/auth/auth.service";
import { MachineService } from "@services/machine/machine.service";
import { NotificationService } from "@services/notification/notification.service";
import { TokenService, TokenTypeKey } from "@services/token/token.service";
import { ValidateService } from "@services/validate/validate.service";
import {
  MockLocalService,
  MockMachineService,
  MockNotificationService,
  MockTokenService,
  MockValidateService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { of } from "rxjs";
import { TokenDetailsActionsComponent } from "./token-details-actions.component";

describe("TokenDetailsActionsComponent", () => {
  let fixture: ComponentFixture<TokenDetailsActionsComponent>;
  let component: TokenDetailsActionsComponent;

  let machineService: MockMachineService;
  let notificationService: MockNotificationService;
  let dialog: jest.Mocked<MatDialog>;

  const matDialogOpen = jest.fn();
  const matDialogMock = {
    open: matDialogOpen
  };

  beforeEach(async () => {
    jest.clearAllMocks();
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [TokenDetailsActionsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: MachineService, useClass: MockMachineService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: MatDialog, useValue: matDialogMock },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    machineService = TestBed.inject(MachineService) as unknown as MockMachineService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    dialog = TestBed.inject(MatDialog) as unknown as jest.Mocked<MatDialog>;
    fixture = TestBed.createComponent(TokenDetailsActionsComponent);
    component = fixture.componentInstance;

    component.tokenSerial = signal("SER-1");
    fixture.componentRef.setInput("tokenType", "hotp");
    fixture.componentRef.setInput("setPinValue", "");
    fixture.componentRef.setInput("repeatPinValue", "");

    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("isAttachedToMachine is false when no applications; true when there is at least one", () => {
    machineService.tokenApplications.set([]);
    expect(component.isAttachedToMachine()).toBe(false);

    machineService.tokenApplications.set([{ id: 42 } as any]);
    expect(component.isAttachedToMachine()).toBe(true);
  });

  it("testPasskey notifies on success", () => {
    component.testPasskey();
    expect(notificationService.success).toHaveBeenCalled();
    const msg = (notificationService.success as jest.Mock).mock.calls[0][0] as string;
    expect(msg).toMatch(/Test successful/i);
  });

  it("attachSshToMachineDialog opens dialog, resolves request, and reloads tokenApplicationResource", async () => {
    const reloadSpy = machineService.tokenApplicationResource.reload as jest.Mock;
    reloadSpy.mockClear();

    matDialogOpen.mockReturnValue({
      afterClosed: () => of(of({}))
    });

    component.attachSshToMachineDialog();

    await Promise.resolve();
    expect(matDialogOpen).toHaveBeenCalledTimes(1);
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("attachHotpToMachineDialog opens dialog, resolves request, and reloads (when request is provided)", async () => {
    const reloadSpy = machineService.tokenApplicationResource.reload as jest.Mock;
    reloadSpy.mockClear();

    matDialogOpen.mockReturnValue({
      afterClosed: () => of(of({}))
    });

    component.attachHotpToMachineDialog();

    await Promise.resolve();
    expect(matDialogOpen).toHaveBeenCalledTimes(1);
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("attachHotpToMachineDialog does not reload when request is null/undefined", async () => {
    const reloadSpy = machineService.tokenApplicationResource.reload as jest.Mock;
    reloadSpy.mockClear();

    matDialogOpen.mockReturnValue({
      afterClosed: () => of(null)
    });

    component.attachHotpToMachineDialog();

    await Promise.resolve();
    expect(matDialogOpen).toHaveBeenCalledTimes(1);
    expect(reloadSpy).not.toHaveBeenCalled();
  });

  it("attachPasskeyToMachine posts assignment and reloads", () => {
    const postSpy = jest.spyOn(machineService, "postAssignMachineToToken");
    const reloadSpy = machineService.tokenApplicationResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.attachPasskeyToMachine();

    expect(postSpy).toHaveBeenCalledWith({
      serial: "SER-1",
      application: "offline",
      machineid: 0,
      resolver: ""
    });
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("removePasskeyFromMachine deletes assignment using first token application id and reloads", () => {
    machineService.tokenApplications.set([{ id: 77 } as any]);

    const delSpy = jest.spyOn(machineService, "deleteAssignMachineToToken");
    const reloadSpy = machineService.tokenApplicationResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.removePasskeyFromMachine();

    expect(delSpy).toHaveBeenCalledWith({
      serial: "SER-1",
      application: "offline",
      mtid: "77"
    });
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("rolloverTokenTypes determined correctly", () => {
    expect(component.rolloverTokenTypes()).toContain("totp");
    expect(component.rolloverTokenTypes()).toContain("hotp");
  });

  it("tokenTypeKey is set correctly", () => {
    fixture.componentRef.setInput("tokenType", "yubikey");
    expect(component.tokenTypeKey()).toEqual("yubikey" as TokenTypeKey);
    expect(component.rolloverTokenTypes().indexOf(component.tokenTypeKey())).toBe(-1);

    fixture.componentRef.setInput("tokenType", "daypassword");
    expect(component.tokenTypeKey()).toEqual("daypassword" as TokenTypeKey);
    expect(component.rolloverTokenTypes().indexOf(component.tokenTypeKey())).toBeGreaterThan(-1);
  });

  describe("openLostTokenDialog()", () => {
    it("passes the isLost & tokenSerial signals to the dialog", () => {
      const reloadSpy = machineService.tokenApplicationResource.reload as jest.Mock;
      reloadSpy.mockClear();

      matDialogOpen.mockReturnValue({
        afterClosed: () => of(of({}))
      });

      component.openLostTokenDialog();
      expect(dialog.open).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          data: {
            isLost: component.isLost,
            tokenSerial: component.tokenSerial
          },
          disableClose: false,
          hasBackdrop: true
        })
      );
    });
  });
});
