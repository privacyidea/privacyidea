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
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { NotificationDeliveryHealth, SystemService } from "@services/system/system.service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { of, throwError } from "rxjs";
import { NotificationDeliveryWidgetComponent } from "./notification-delivery-widget.component";

function makeResponse<T>(value: T): PiResponse<T> {
  return {
    id: 1,
    jsonrpc: "2.0",
    signature: "",
    time: 0,
    version: "",
    versionnumber: "",
    detail: {},
    result: { status: true, value }
  };
}

describe("NotificationDeliveryWidgetComponent", () => {
  let fixture: ComponentFixture<NotificationDeliveryWidgetComponent>;
  let component: NotificationDeliveryWidgetComponent;
  let systemMock: MockSystemService;

  const instance: WidgetInstance = {
    id: "notification-delivery-1",
    type: "notification-delivery",
    x: 0,
    y: 0,
    cols: 8,
    rows: 6
  };

  const deliveryHealth: NotificationDeliveryHealth = {
    push: [{ key: "firebase1", ok: 10, failed: 0, error: 0, total: 10 }],
    sms: [{ key: "gw1", ok: 5, failed: 2, error: 0, total: 7 }],
    email: [{ key: "smtp1", ok: 3, failed: 0, error: 1, total: 4 }],
    since_seconds: 3600
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NotificationDeliveryWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

    systemMock = TestBed.inject(SystemService) as unknown as MockSystemService;
    systemMock.getNotificationDelivery.mockReturnValue(of(makeResponse(deliveryHealth)));

    fixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", instance);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should extend the DashboardWidget base", () => {
    expect(component).toBeInstanceOf(DashboardWidget);
  });

  it("should override the static metadata", () => {
    expect(NotificationDeliveryWidgetComponent.type).toBe("notification-delivery");
    expect(NotificationDeliveryWidgetComponent.title).toBeTruthy();
    expect(NotificationDeliveryWidgetComponent.icon).toBe("notifications_active");
  });

  it("should override the static size constraints", () => {
    expect(NotificationDeliveryWidgetComponent.defaultSize).toEqual({ cols: 8, rows: 6 });
    expect(NotificationDeliveryWidgetComponent.minSize).toEqual({ cols: 6, rows: 5 });
    expect(NotificationDeliveryWidgetComponent.maxSize).toEqual({ cols: 16, rows: 12 });
  });

  it("should render the push, sms and email sections", () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain("Push");
    expect(text).toContain("SMS");
    expect(text).toContain("Email");
    expect(text).toContain("firebase1");
    expect(text).toContain("gw1");
    expect(text).toContain("smtp1");
  });

  it("should badge the error cell using the shared highlight classes", () => {
    const badges: HTMLElement[] = Array.from(
      fixture.nativeElement.querySelectorAll(".delivery-table tbody td:last-child span")
    );
    expect(badges[0].className).toBe("highlight-true");
    expect(badges[1].className).toBe("highlight-warning");
    expect(badges[2].className).toBe("highlight-false");
  });

  it("should omit a channel entry without recorded deliveries", () => {
    systemMock.getNotificationDelivery.mockReturnValue(
      of(
        makeResponse<NotificationDeliveryHealth>({
          push: [{ key: "firebase1", ok: 10, failed: 0, error: 0, total: 10 }],
          sms: [
            { key: "gw1", ok: 5, failed: 2, error: 0, total: 7 },
            { key: "gw-untested", ok: 0, failed: 0, error: 0, total: 0 }
          ],
          email: [{ key: "smtp1", ok: 3, failed: 0, error: 1, total: 4 }],
          since_seconds: 3600
        })
      )
    );

    const untestedFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    untestedFixture.componentRef.setInput("instance", instance);
    untestedFixture.detectChanges();

    const text = untestedFixture.nativeElement.textContent;
    expect(text).toContain("gw1");
    expect(text).not.toContain("gw-untested");
    untestedFixture.destroy();
  });

  it("should hide a channel's heading and table when it has no recorded deliveries", () => {
    systemMock.getNotificationDelivery.mockReturnValue(
      of(
        makeResponse<NotificationDeliveryHealth>({
          push: [{ key: "firebase1", ok: 10, failed: 0, error: 0, total: 10 }],
          sms: [{ key: "gw1", ok: 0, failed: 0, error: 0, total: 0 }],
          email: [],
          since_seconds: 3600
        })
      )
    );

    const partialFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    partialFixture.componentRef.setInput("instance", instance);
    partialFixture.detectChanges();

    const text = partialFixture.nativeElement.textContent;
    expect(text).toContain("Push");
    expect(text).not.toContain("SMS");
    expect(text).not.toContain("Email");
    partialFixture.destroy();
  });

  it("should set the state to error when a refresh fails while cached data is still present", () => {
    expect(component.state()).toBe("ready");

    systemMock.getNotificationDelivery.mockReturnValue(throwError(() => new Error("boom")));
    TestBed.inject(DashboardDataStore).refreshAll();
    fixture.detectChanges();

    expect(component.state()).toBe("error");
  });

  it("should show a single fallback message instead of any section when all channels are empty", () => {
    systemMock.getNotificationDelivery.mockReturnValue(
      of(makeResponse<NotificationDeliveryHealth>({ push: [], sms: [], email: [], since_seconds: 3600 }))
    );

    const emptyFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    emptyFixture.componentRef.setInput("instance", instance);
    emptyFixture.detectChanges();

    expect(emptyFixture.nativeElement.querySelector("table")).toBeNull();
    expect(emptyFixture.nativeElement.textContent).toContain("No notification deliveries in the last hour.");
    emptyFixture.destroy();
  });
});
