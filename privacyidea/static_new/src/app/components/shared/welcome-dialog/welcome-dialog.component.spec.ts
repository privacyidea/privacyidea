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
import { TestBed } from "@angular/core/testing";
import { WelcomeDialogComponent } from "./welcome-dialog.component";
import { MatDialogRef } from "@angular/material/dialog";
import { AuthService } from "../../../services/auth/auth.service";
import { signal } from "@angular/core";

describe("WelcomeDialogComponent", () => {
  let component: WelcomeDialogComponent;
  let dialogRefMock: { close: jest.Mock };
  let authMock: {
    hideWelcome: ReturnType<typeof signal<boolean>>;
    subscriptionStatus: ReturnType<typeof signal<number>>;
  };

  beforeEach(() => {
    dialogRefMock = { close: jest.fn() };
    authMock = {
      hideWelcome: signal(false),
      subscriptionStatus: signal(0)
    };

    TestBed.configureTestingModule({
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: AuthService, useValue: authMock }
      ]
    });

    component = TestBed.createComponent(WelcomeDialogComponent).componentInstance;
  });

  it("should start at step 0 by default", () => {
    expect(component.step()).toBe(0);
  });

  it("should start at step 4 if hideWelcome is true", () => {
    authMock.hideWelcome.set(true);
    const c = TestBed.createComponent(WelcomeDialogComponent).componentInstance;
    expect(c.step()).toBe(4);
  });

  it("nextWelcome should increment step and close at >=5", () => {
    component.nextWelcome();
    expect(component.step()).toBe(1);
    component.nextWelcome();
    expect(component.step()).toBe(2);
    component.nextWelcome();
    expect(component.step()).toBe(3);

    authMock.subscriptionStatus.set(0);
    component.nextWelcome();
    expect(dialogRefMock.close).toHaveBeenCalled();
  });

  it("should allow step 4 when subscriptionStatus is 1, then close on next", () => {
    component = TestBed.createComponent(WelcomeDialogComponent).componentInstance;
    authMock.subscriptionStatus.set(1);
    component.nextWelcome(); // 1
    component.nextWelcome(); // 2
    component.nextWelcome(); // 3

    component.nextWelcome();
    expect(component.step()).toBe(4);
    expect(dialogRefMock.close).not.toHaveBeenCalled();

    component.nextWelcome();
    expect(dialogRefMock.close).toHaveBeenCalled();
  });

  it("resetWelcome should set step back to 0", () => {
    component.step.set(3);
    component.resetWelcome();
    expect(component.step()).toBe(0);
  });
});