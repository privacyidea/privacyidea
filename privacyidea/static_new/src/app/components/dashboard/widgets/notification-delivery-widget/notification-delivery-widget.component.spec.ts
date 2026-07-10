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
import { SmsGateway, SmsGatewayService } from "@services/sms-gateway/sms-gateway.service";
import { SmtpServers, SmtpService } from "@services/smtp/smtp.service";
import { NotificationDeliveryHealth, SystemService } from "@services/system/system.service";
import { MockSmsGatewayService } from "@testing/mock-services/mock-sms-gateway-service";
import { MockSmtpService } from "@testing/mock-services/mock-smtp-service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { of } from "rxjs";
import { NotificationDeliveryWidgetComponent } from "./notification-delivery-widget.component";

const FIREBASE_PROVIDER_MODULE = "privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider";

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

function makeGateway(name: string, providermodule: string): SmsGateway {
  return { name, providermodule, options: {}, headers: {} };
}

describe("NotificationDeliveryWidgetComponent", () => {
  let fixture: ComponentFixture<NotificationDeliveryWidgetComponent>;
  let component: NotificationDeliveryWidgetComponent;
  let systemMock: MockSystemService;
  let smsGatewayMock: MockSmsGatewayService;
  let smtpMock: MockSmtpService;

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
        { provide: SystemService, useClass: MockSystemService },
        { provide: SmsGatewayService, useClass: MockSmsGatewayService },
        { provide: SmtpService, useClass: MockSmtpService }
      ]
    }).compileComponents();

    systemMock = TestBed.inject(SystemService) as unknown as MockSystemService;
    systemMock.getNotificationDelivery.mockReturnValue(of(makeResponse(deliveryHealth)));

    smsGatewayMock = TestBed.inject(SmsGatewayService) as unknown as MockSmsGatewayService;
    smsGatewayMock.listSmsGateways.mockReturnValue(
      of(
        makeResponse<SmsGateway[]>([
          makeGateway("firebase1", FIREBASE_PROVIDER_MODULE),
          makeGateway("gw1", "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider")
        ])
      )
    );

    smtpMock = TestBed.inject(SmtpService) as unknown as MockSmtpService;
    smtpMock.listSmtpServers.mockReturnValue(
      of(makeResponse<SmtpServers>({ smtp1: { identifier: "smtp1" } as SmtpServers[string] }))
    );

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

  it("should include a configured gateway with no recorded deliveries as a zero-count row", () => {
    smsGatewayMock.listSmsGateways.mockReturnValue(
      of(
        makeResponse<SmsGateway[]>([
          makeGateway("firebase1", FIREBASE_PROVIDER_MODULE),
          makeGateway("gw1", "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"),
          makeGateway("gw-untested", "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider")
        ])
      )
    );

    const untestedFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    untestedFixture.componentRef.setInput("instance", instance);
    untestedFixture.detectChanges();

    const text = untestedFixture.nativeElement.textContent;
    expect(text).toContain("gw-untested");
    const badges: HTMLElement[] = Array.from(
      untestedFixture.nativeElement.querySelectorAll(".delivery-table tbody tr")
    );
    const untestedRow = badges.find((row) => row.textContent?.includes("gw-untested"));
    expect(untestedRow?.querySelector("td:last-child span")?.className).toBe("highlight-disabled");
    untestedFixture.destroy();
  });

  it("should hide a channel's heading and table when it has neither configured gateways nor recorded deliveries", () => {
    systemMock.getNotificationDelivery.mockReturnValue(
      of(
        makeResponse<NotificationDeliveryHealth>({
          push: [{ key: "firebase1", ok: 10, failed: 0, error: 0, total: 10 }],
          sms: [],
          email: [],
          since_seconds: 3600
        })
      )
    );
    smsGatewayMock.listSmsGateways.mockReturnValue(
      of(makeResponse<SmsGateway[]>([makeGateway("firebase1", FIREBASE_PROVIDER_MODULE)]))
    );
    smtpMock.listSmtpServers.mockReturnValue(of(makeResponse<SmtpServers>({})));

    const partialFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    partialFixture.componentRef.setInput("instance", instance);
    partialFixture.detectChanges();

    const text = partialFixture.nativeElement.textContent;
    expect(text).toContain("Push");
    expect(text).not.toContain("SMS");
    expect(text).not.toContain("Email");
    partialFixture.destroy();
  });

  it("should show a single fallback message instead of any section when all channels are empty", () => {
    systemMock.getNotificationDelivery.mockReturnValue(
      of(makeResponse<NotificationDeliveryHealth>({ push: [], sms: [], email: [], since_seconds: 3600 }))
    );
    smsGatewayMock.listSmsGateways.mockReturnValue(of(makeResponse<SmsGateway[]>([])));
    smtpMock.listSmtpServers.mockReturnValue(of(makeResponse<SmtpServers>({})));

    const emptyFixture = TestBed.createComponent(NotificationDeliveryWidgetComponent);
    emptyFixture.componentRef.setInput("instance", instance);
    emptyFixture.detectChanges();

    expect(emptyFixture.nativeElement.querySelector("table")).toBeNull();
    expect(emptyFixture.nativeElement.textContent).toContain("No deliveries in this window.");
    emptyFixture.destroy();
  });
});
