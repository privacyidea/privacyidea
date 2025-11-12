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
import { LostTokenComponent } from "./lost-token.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { signal, WritableSignal } from "@angular/core";
import { Subject } from "rxjs";
import { NotificationService } from "../../../../../services/notification/notification.service";
import { MockNotificationService, MockTokenService } from "../../../../../../testing/mock-services";
import { TokenService } from "../../../../../services/token/token.service";
import "@angular/localize/init";

describe("LostTokenComponent", () => {
  let component: LostTokenComponent;
  let fixture: ComponentFixture<LostTokenComponent>;

  let afterClosed$!: Subject<void>;
  let dialogRefMock!: { disableClose: boolean; close: jest.Mock; afterClosed: () => any };

  let isLost!: WritableSignal<boolean>;
  let tokenSerial!: WritableSignal<string>;

  let tokenService: MockTokenService;
  let notification: MockNotificationService;

  beforeEach(async () => {
    afterClosed$ = new Subject<void>();
    dialogRefMock = {
      disableClose: false,
      close: jest.fn(),
      afterClosed: () => afterClosed$.asObservable()
    };

    isLost = signal(false);
    tokenSerial = signal("Mock serial");

    await TestBed.configureTestingModule({
      imports: [LostTokenComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: MAT_DIALOG_DATA, useValue: { tokenSerial, isLost } },
        { provide: MatDialogRef, useValue: dialogRefMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(LostTokenComponent);
    component = fixture.componentInstance;

    tokenService = TestBed.inject(TokenService) as any;
    notification = TestBed.inject(NotificationService) as any;

    jest.spyOn(console, "error").mockImplementation(() => {});
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("binds dialogRef.disableClose to isLost signal via effect", () => {
    expect(isLost()).toBe(false);
    expect(dialogRefMock.disableClose).toBe(false);

    isLost.set(true);
    fixture.detectChanges();
    expect(dialogRefMock.disableClose).toBe(true);

    isLost.set(false);
    fixture.detectChanges();
    expect(dialogRefMock.disableClose).toBe(false);
  });

  it("resets isLost to false when dialog is closed (afterClosed subscription)", () => {
    isLost.set(true);
    expect(isLost()).toBe(true);

    afterClosed$.next();
    fixture.detectChanges();

    expect(isLost()).toBe(false);
  });

  it("lostToken() calls service, sets state, stores response and shows snackbar", () => {
    isLost.set(false);
    tokenSerial.set("SER-123");

    component.lostToken();

    expect(tokenService.lostToken).toHaveBeenCalledWith("SER-123");
    expect(isLost()).toBe(true);
    expect(component.lostTokenData).toBeTruthy();
    expect(component.lostTokenData?.serial).toBe("SER-123");
    expect(notification.openSnackBar).toHaveBeenCalledWith("Token marked as lost: SER-123");
  });

  it("tokenSelected() without value shows warning and does not close dialog", () => {
    component.tokenSelected(undefined);
    expect(notification.openSnackBar).toHaveBeenCalledWith("No token selected, please select a token.");
    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  it("tokenSelected(value) closes dialog and updates tokenSerial", () => {
    tokenSerial.set("OLD");
    component.tokenSelected("NEW-999");

    expect(dialogRefMock.close).toHaveBeenCalledTimes(1);
    expect(tokenSerial()).toBe("NEW-999");
  });
});
