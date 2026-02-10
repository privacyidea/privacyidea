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
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { SubscriptionService } from "./subscription.service";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { environment } from "../../../environments/environment";
import { provideHttpClient } from "@angular/common/http";

describe("SubscriptionService", () => {
  let service: SubscriptionService;
  let httpMock: HttpTestingController;
  let authMock: { getHeaders: jest.Mock };
  let notifyMock: { openSnackBar: jest.Mock };

  beforeEach(() => {
    authMock = { getHeaders: jest.fn(() => ({}) as any) } as any;
    notifyMock = { openSnackBar: jest.fn() } as any;

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        SubscriptionService,
        { provide: AuthService, useValue: authMock },
        { provide: NotificationService, useValue: notifyMock }
      ]
    });

    service = TestBed.inject(SubscriptionService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it("reload() should not throw", () => {
    expect(() => service.reload()).not.toThrow();
  });

  it("deleteSubscription should propagate error and show notification", (done) => {
    service.deleteSubscription("app1").subscribe({
      next: () => done.fail("should error"),
      error: () => {
        expect(notifyMock.openSnackBar).toHaveBeenCalled();
        done();
      }
    });

    const req = httpMock.expectOne(environment.proxyUrl + "/subscriptions/app1");
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { error: { message: "bad" } } }, { status: 400, statusText: "Bad Request" });
  });

  it("uploadSubscriptionFile should propagate error and show notification", (done) => {
    const file = new File(["abc"], "subs.txt");
    service.uploadSubscriptionFile(file).subscribe({
      next: () => done.fail("should error"),
      error: () => {
        expect(notifyMock.openSnackBar).toHaveBeenCalled();
        done();
      }
    });

    const req = httpMock.expectOne(environment.proxyUrl + "/subscriptions/");
    expect(req.request.method).toBe("POST");
    req.flush({ result: { error: { message: "bad" } } }, { status: 500, statusText: "Server Error" });
  });
});
