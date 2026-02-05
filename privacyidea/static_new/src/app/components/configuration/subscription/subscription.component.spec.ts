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
import { SubscriptionComponent } from "./subscription.component";
import { MatSnackBarModule } from "@angular/material/snack-bar";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { SubscriptionService } from "../../../services/subscription/subscription.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { AuthService } from "../../../services/auth/auth.service";
import { MockAuthService, MockNotificationService, MockPiResponse, MockSubscriptionService } from "../../../../testing/mock-services";
import { of } from "rxjs";
import { By } from "@angular/platform-browser";

describe("SubscriptionComponent", () => {
  let component: SubscriptionComponent;
  let fixture: ComponentFixture<SubscriptionComponent>;
  let subscriptionService: MockSubscriptionService;
  let notificationService: MockNotificationService;
  let authService: MockAuthService;

  const mockSubscriptions = {
    "app1": {
      application: "app1",
      timedelta: -20,
      level: "Gold",
      num_users: 100,
      active_users: 50,
      num_tokens: 200,
      active_tokens: 80,
      num_clients: 10,
      date_from: "2024-01-01",
      date_till: "2025-01-01",
      for_name: "Customer A",
      for_email: "a@example.com",
      for_address: "Address A",
      for_phone: "123",
      for_url: "http://a.com",
      for_comment: "Comment A",
      by_name: "Issuer X",
      by_url: "http://x.com",
      by_address: "Address X",
      by_email: "x@example.com",
      by_phone: "456"
    }
  };

  beforeEach(async () => {
    subscriptionService = new MockSubscriptionService();
    notificationService = new MockNotificationService();
    authService = new MockAuthService();

    await TestBed.configureTestingModule({
      imports: [
        SubscriptionComponent,
        MatSnackBarModule,
        BrowserAnimationsModule
      ],
      providers: [
        { provide: SubscriptionService, useValue: subscriptionService },
        { provide: NotificationService, useValue: notificationService },
        { provide: AuthService, useValue: authService }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(SubscriptionComponent);
    component = fixture.componentInstance;
  });

  it("should create", () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it("should render subscriptions", () => {
    subscriptionService.subscriptionsResource.set(MockPiResponse.fromValue(mockSubscriptions));
    fixture.detectChanges();

    const detailElements = fixture.debugElement.queryAll(By.css(".subscription-details"));
    expect(detailElements.length).toBe(1);
    expect(fixture.nativeElement.textContent).toContain("app1");
    expect(fixture.nativeElement.textContent).toContain("Gold");
  });

  it("should show valid subscription alert when timedelta < -14", () => {
    subscriptionService.subscriptionsResource.set(MockPiResponse.fromValue(mockSubscriptions));
    fixture.detectChanges();

    const alert = fixture.debugElement.query(By.css(".alert-success"));
    expect(alert).toBeTruthy();
    expect(alert.nativeElement.textContent).toContain("Valid subscription");
  });

  it("should show warning alert when -14 <= timedelta < 0", () => {
    const subscriptions = {
      "app1": { ...mockSubscriptions.app1, timedelta: -5 }
    };
    subscriptionService.subscriptionsResource.set(MockPiResponse.fromValue(subscriptions));
    fixture.detectChanges();

    const alert = fixture.debugElement.query(By.css(".alert-warning"));
    expect(alert).toBeTruthy();
    expect(alert.nativeElement.textContent).toContain("Subscription about to expire");
  });

  it("should show danger alert when timedelta >= 0", () => {
    const subscriptions = {
      "app1": { ...mockSubscriptions.app1, timedelta: 5 }
    };
    subscriptionService.subscriptionsResource.set(MockPiResponse.fromValue(subscriptions));
    fixture.detectChanges();

    const alert = fixture.debugElement.query(By.css(".alert-danger"));
    expect(alert).toBeTruthy();
    expect(alert.nativeElement.textContent).toContain("Subscription expired");
  });

  it("should call upload and show success snackbar", () => {
    fixture.detectChanges();
    const file = new File([""], "test.txt");
    const event = {
      currentTarget: {
        files: [file]
      }
    } as unknown as Event;

    subscriptionService.uploadSubscriptionFile.mockReturnValue(of(MockPiResponse.fromValue({})));
    
    component.upload(event);

    expect(subscriptionService.uploadSubscriptionFile).toHaveBeenCalledWith(file);
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("File uploaded successfully.");
    expect(subscriptionService.reload).toHaveBeenCalled();
  });

  it("should call deleteSubscription and show success snackbar", () => {
    fixture.detectChanges();
    subscriptionService.deleteSubscription.mockReturnValue(of(MockPiResponse.fromValue(true)));

    component.deleteSubscription("app1");

    expect(subscriptionService.deleteSubscription).toHaveBeenCalledWith("app1");
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Subscription deleted successfully.");
    expect(subscriptionService.reload).toHaveBeenCalled();
  });

  it("should hide delete button if action not allowed", () => {
    authService.actionAllowed.mockReturnValue(false);
    subscriptionService.subscriptionsResource.set(MockPiResponse.fromValue(mockSubscriptions));
    fixture.detectChanges();

    const deleteBtn = fixture.debugElement.query(By.css(".action-button-delete"));
    expect(deleteBtn).toBeFalsy();
  });

  it("should show delete button if action allowed", () => {
    authService.actionAllowed.mockReturnValue(true);
    subscriptionService.subscriptionsResource.set(MockPiResponse.fromValue(mockSubscriptions));
    fixture.detectChanges();

    const deleteBtn = fixture.debugElement.query(By.css(".action-button-delete"));
    expect(deleteBtn).toBeTruthy();
  });
});
