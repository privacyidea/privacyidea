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
import { AuthService } from "@services/auth/auth.service";
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

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("is hidden when the server is not running in debug mode", () => {
    mockAuthService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, is_debug: false, role: "admin" });
    fixture.detectChanges();

    expect(component.visible()).toBe(false);
    expect(fixture.nativeElement.querySelector(".debug-ribbon")).toBeNull();
  });

  it("is hidden for a self-service user even in debug mode", () => {
    mockAuthService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, is_debug: true, role: "user" });
    fixture.detectChanges();

    expect(component.visible()).toBe(false);
  });

  it("is shown for an admin when the server is running in debug mode", () => {
    mockAuthService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, is_debug: true, role: "admin" });
    fixture.detectChanges();

    expect(component.visible()).toBe(true);
    expect(fixture.nativeElement.querySelector(".debug-ribbon")).toBeTruthy();
  });

  it("stays shown after being clicked, since it cannot be dismissed", () => {
    mockAuthService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, is_debug: true, role: "admin" });
    fixture.detectChanges();

    const ribbon: HTMLElement = fixture.nativeElement.querySelector(".debug-ribbon");
    ribbon.click();
    fixture.detectChanges();

    expect(component.visible()).toBe(true);
    expect(fixture.nativeElement.querySelector(".debug-ribbon")).toBeTruthy();
  });
});
