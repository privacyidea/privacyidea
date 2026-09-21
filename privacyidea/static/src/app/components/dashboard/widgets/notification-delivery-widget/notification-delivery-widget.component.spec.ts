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
import { getDebugNode, provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { WidgetHeaderPickerComponent } from "@components/dashboard/widgets/header-picker/widget-header-picker.component";
import { provideRouter } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { UserSettingsService } from "@services/user-settings/user-settings.service";
import { DashboardLayoutService } from "@services/dashboard/dashboard-layout.service";
import { NotificationDeliveryHealth, SystemService } from "@services/system/system.service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { MockUserSettingsService } from "@testing/mock-services/mock-user-settings-service";
import { of, Subject, throwError } from "rxjs";
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
        // The widget keeps its window in the stored dashboard layout, so the layout service - and with it the
        // user settings document - is built as soon as the widget is. Mocked, or the settings request goes out
        // over the wire.
        { provide: UserSettingsService, useClass: MockUserSettingsService },
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

  it("should keep the cached data and flag the failure when a refresh fails", () => {
    expect(component.state()).toBe("ready");

    systemMock.getNotificationDelivery.mockReturnValue(throwError(() => new Error("boom")));
    TestBed.inject(DashboardDataStore).refreshAll();
    fixture.detectChanges();

    expect(component.state()).toBe("ready");
    expect(component.refreshFailed()).toBe(true);
    expect(component.sections().push.length).toBeGreaterThan(0);
  });

  it("should set the state to error when the first request fails", () => {
    systemMock.getNotificationDelivery.mockReturnValue(throwError(() => new Error("boom")));
    TestBed.inject(DashboardDataStore).invalidate();

    const failedFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    failedFixture.componentRef.setInput("instance", instance);
    failedFixture.detectChanges();

    expect(failedFixture.componentInstance.state()).toBe("error");
    failedFixture.destroy();
  });

  it("should show a single fallback message instead of any section when all channels are empty", () => {
    systemMock.getNotificationDelivery.mockReturnValue(
      of(makeResponse<NotificationDeliveryHealth>({ push: [], sms: [], email: [], since_seconds: 3600 }))
    );

    const emptyFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    emptyFixture.componentRef.setInput("instance", instance);
    emptyFixture.detectChanges();

    expect(emptyFixture.nativeElement.querySelector("table")).toBeNull();
    expect(emptyFixture.nativeElement.textContent).toContain("No notification deliveries in the selected time window.");
    emptyFixture.destroy();
  });

  it("should sort each channel through its own TableSort column accessors", () => {
    systemMock.getNotificationDelivery.mockReturnValue(
      of(
        makeResponse<NotificationDeliveryHealth>({
          push: [
            { key: "fcm-b", ok: 1, failed: 0, error: 0, total: 5 },
            { key: "fcm-a", ok: 4, failed: 0, error: 0, total: 4 }
          ],
          sms: [
            { key: "gw-b", ok: 2, failed: 1, error: 0, total: 9 },
            { key: "gw-a", ok: 6, failed: 0, error: 0, total: 6 }
          ],
          email: [
            { key: "smtp-b", ok: 1, failed: 2, error: 1, total: 8 },
            { key: "smtp-a", ok: 7, failed: 0, error: 0, total: 7 }
          ],
          since_seconds: 3600
        })
      )
    );
    TestBed.inject(DashboardDataStore).invalidate();

    const sortFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    sortFixture.componentRef.setInput("instance", instance);
    sortFixture.detectChanges();
    const sortComponent = sortFixture.componentInstance;

    sortComponent.pushSort.toggle("key");
    expect(sortComponent.pushRows().map((row) => row.key)).toEqual(["fcm-a", "fcm-b"]);

    sortComponent.smsSort.toggle("ok");
    expect(sortComponent.smsRows().map((row) => row.ok)).toEqual([2, 6]);

    sortComponent.emailSort.toggle("failed");
    expect(sortComponent.emailRows().map((row) => row.failed)).toEqual([0, 2]);

    sortComponent.pushSort.toggle("error");
    expect(sortComponent.pushRows().length).toBe(2);
    sortFixture.destroy();
  });

  it("should set the state to loading while the request is still in flight", () => {
    const pending = new Subject<PiResponse<NotificationDeliveryHealth>>();
    systemMock.getNotificationDelivery.mockReturnValue(pending.asObservable());
    TestBed.inject(DashboardDataStore).invalidate();

    const loadingFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    loadingFixture.componentRef.setInput("instance", instance);
    loadingFixture.detectChanges();

    expect(loadingFixture.componentInstance.state()).toBe("loading");
    loadingFixture.destroy();
  });

  it("should invalidate the cache and reload on reload()", () => {
    systemMock.getNotificationDelivery.mockClear();

    component.reload();

    expect(systemMock.getNotificationDelivery).toHaveBeenCalledTimes(1);
  });

  it("should stay in the loading state until the data ref is initialised", () => {
    const uninitFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    uninitFixture.componentRef.setInput("instance", instance);
    // No change detection: the effect that starts the first fetch has not run, so the widget holds no data ref yet.

    expect(uninitFixture.componentInstance.state()).toBe("loading");
    uninitFixture.destroy();
  });

  it("should ask for the last hour when no window has been stored", () => {
    expect(component.selectedTimeWindow().id).toBe("1h");
    expect(systemMock.getNotificationDelivery).toHaveBeenCalledWith(3600);
  });

  it("should open on the window stored in the widget options", () => {
    systemMock.getNotificationDelivery.mockClear();
    TestBed.inject(DashboardDataStore).invalidate();

    const storedFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    storedFixture.componentRef.setInput("instance", { ...instance, options: { range: "24h" } });
    storedFixture.detectChanges();

    expect(storedFixture.componentInstance.selectedTimeWindow().id).toBe("24h");
    expect(systemMock.getNotificationDelivery).toHaveBeenCalledWith(86400);
    storedFixture.destroy();
  });

  it("should refetch for the picked window and write it to the widget options", () => {
    const layoutService = TestBed.inject(DashboardLayoutService);
    const setOptions = jest.spyOn(layoutService, "setWidgetOptions");
    systemMock.getNotificationDelivery.mockClear();

    component.selectTimeWindow("6h");
    fixture.detectChanges();

    expect(component.selectedTimeWindow().id).toBe("6h");
    expect(systemMock.getNotificationDelivery).toHaveBeenCalledWith(21600);
    expect(setOptions).toHaveBeenCalledWith(instance.id, { range: "6h" });
    setOptions.mockRestore();
  });

  it("should drop the store entry of the window it leaves, so a refresh stops fetching it", () => {
    const store = TestBed.inject(DashboardDataStore);
    expect(store.peek("dashboard:notification-delivery:1h")).not.toBeNull();

    component.selectTimeWindow("24h");
    fixture.detectChanges();

    expect(store.peek("dashboard:notification-delivery:1h")).toBeNull();
    expect(store.peek("dashboard:notification-delivery:24h")).not.toBeNull();
  });

  it("should wire the header picker to its time window", () => {
    const view = component.headerActions()!.createEmbeddedView(null);
    view.detectChanges();
    const pickerNode = view.rootNodes.find((node: Node) => node.nodeType === Node.ELEMENT_NODE);
    const picker = getDebugNode(pickerNode)!.componentInstance as WidgetHeaderPickerComponent;

    expect(picker.selected()).toBe(component.selectedTimeWindow());
    expect(picker.tooltip()).toBe("Choose the time window");
    expect(picker.icon()).toBe("schedule");

    picker.picked.emit("24h");
    fixture.detectChanges();

    expect(component.selectedTimeWindow().id).toBe("24h");
    view.destroy();
  });
});
