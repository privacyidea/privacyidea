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
import { TokenService } from "@services/token/token.service";
import { ValidateService } from "@services/validate/validate.service";
import {
    MockLocalService,
    MockMachineService,
    MockNotificationService,
    MockTokenService,
    MockValidateService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { TokenDetailsActionsComponent } from "./token-details-actions.component";

describe("TokenDetailsActionsComponent", () => {
  let fixture: ComponentFixture<TokenDetailsActionsComponent>;
  let component: TokenDetailsActionsComponent;

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

    fixture = TestBed.createComponent(TokenDetailsActionsComponent);
    component = fixture.componentInstance;

    component.tokenType = signal("hotp");
    component.setPinValue = signal("");
    component.repeatPinValue = signal("");
    component.passkeyTestResult = signal(null);

    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("emits testPasskey when triggered", () => {
    const spy = jest.fn();
    component.testPasskey.subscribe(spy);
    component.testPasskey.emit();
    expect(spy).toHaveBeenCalled();
  });
});
