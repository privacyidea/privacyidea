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
import { provideRouter } from "@angular/router";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services";
import { SubscriptionExpiredNoticeComponent } from "./subscription-expired-notice.component";

describe("SubscriptionExpiredNoticeComponent", () => {
  let mockAuthService: MockAuthService;
  let fixture: ComponentFixture<SubscriptionExpiredNoticeComponent>;

  const setStatus = (status: number, rights: string[] = ["managesubscription"]) => {
    mockAuthService.authData.update((data) => ({ ...data!, subscription_status: status, rights }));
    fixture.detectChanges();
  };
  const notice = () => fixture.nativeElement.querySelector(".subscription-expired-notice");

  beforeEach(async () => {
    mockAuthService = new MockAuthService();

    await TestBed.configureTestingModule({
      imports: [SubscriptionExpiredNoticeComponent],
      providers: [provideRouter([]), { provide: AuthService, useValue: mockAuthService }]
    }).compileComponents();

    fixture = TestBed.createComponent(SubscriptionExpiredNoticeComponent);
    fixture.detectChanges();
  });

  it("is shown when the subscription status is 2", () => {
    setStatus(2);

    expect(fixture.componentInstance.visible()).toBe(true);
    expect(notice()).toBeTruthy();
    expect(notice().getAttribute("role")).toBe("status");
  });

  it("links to the subscription page for an admin who may manage the subscription", () => {
    setStatus(2);

    expect(notice().querySelector("a").getAttribute("href")).toBe("/configuration/subscription");
  });

  it("shows the warning without a link for an admin who may not manage the subscription", () => {
    setStatus(2, []);

    expect(notice()).toBeTruthy();
    expect(notice().querySelector("a")).toBeNull();
    expect(notice().textContent).toContain("contact an administrator");
  });

  it.each([0, 1, 3])("is hidden for subscription status %i", (status) => {
    setStatus(status);

    expect(fixture.componentInstance.visible()).toBe(false);
    expect(notice()).toBeNull();
  });

  it("disappears when the status changes from 2 to 3", () => {
    setStatus(2);
    expect(notice()).toBeTruthy();

    setStatus(3);
    expect(notice()).toBeNull();
  });
});
