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
import { AuthService, LogLevel } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services";
import { DebugNoticeComponent } from "./debug-notice.component";

describe("DebugNoticeComponent", () => {
  let mockAuthService: MockAuthService;
  let fixture: ComponentFixture<DebugNoticeComponent>;
  let component: DebugNoticeComponent;

  beforeEach(async () => {
    mockAuthService = new MockAuthService();

    await TestBed.configureTestingModule({
      imports: [DebugNoticeComponent],
      providers: [{ provide: AuthService, useValue: mockAuthService }]
    }).compileComponents();

    fixture = TestBed.createComponent(DebugNoticeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    // The dismiss flag persists in sessionStorage; clear it so it does not leak between tests.
    sessionStorage.clear();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("is hidden when the backend log level is not DEBUG", () => {
    mockAuthService.logLevel.set(LogLevel.Info);
    mockAuthService.role.set("admin");
    fixture.detectChanges();

    expect(component.visible()).toBe(false);
    expect(fixture.nativeElement.querySelector(".debug-ribbon")).toBeNull();
  });

  it("is hidden for a self-service user even when the log level is DEBUG", () => {
    mockAuthService.logLevel.set(LogLevel.Debug);
    mockAuthService.role.set("user");
    fixture.detectChanges();

    expect(component.visible()).toBe(false);
  });

  it("is shown for an admin when the backend log level is DEBUG", () => {
    mockAuthService.logLevel.set(LogLevel.Debug);
    mockAuthService.role.set("admin");
    fixture.detectChanges();

    expect(component.visible()).toBe(true);
    expect(fixture.nativeElement.querySelector(".debug-ribbon")).toBeTruthy();
  });

  it("escalates to the passwords variant, which also implies debug logging", () => {
    mockAuthService.logLevel.set(LogLevel.Debug - 1);
    mockAuthService.role.set("admin");
    fixture.detectChanges();

    expect(component.visible()).toBe(true);
    expect(fixture.nativeElement.querySelector(".debug-ribbon-text-passwords")).toBeTruthy();
  });

  it("shows the passwords variant at log level 0 (NOTSET), where lib/log.py still logs passwords", () => {
    mockAuthService.logLevel.set(LogLevel.NotSet);
    mockAuthService.role.set("admin");
    fixture.detectChanges();

    expect(component.visible()).toBe(true);
    expect(fixture.nativeElement.querySelector(".debug-ribbon-text-passwords")).toBeTruthy();
  });

  it("does not show the passwords variant for plain debug logging", () => {
    mockAuthService.logLevel.set(LogLevel.Debug);
    mockAuthService.role.set("admin");
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector(".debug-ribbon-text")).toBeTruthy();
    expect(fixture.nativeElement.querySelector(".debug-ribbon-text-passwords")).toBeNull();
  });

  it("is dismissed when clicked", () => {
    mockAuthService.logLevel.set(LogLevel.Debug);
    mockAuthService.role.set("admin");
    fixture.detectChanges();

    const ribbonText: HTMLElement = fixture.nativeElement.querySelector(".debug-ribbon-text");
    ribbonText.click();
    fixture.detectChanges();

    expect(component.dismissed()).toBe(true);
    expect(component.visible()).toBe(false);
    expect(fixture.nativeElement.querySelector(".debug-ribbon")).toBeNull();
  });
});
