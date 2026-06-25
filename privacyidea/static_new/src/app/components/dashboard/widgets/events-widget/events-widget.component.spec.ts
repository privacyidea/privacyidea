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
import { AuthService } from "@services/auth/auth.service";
import { EventHandler, EventService } from "@services/event/event.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockEventService } from "@testing/mock-services/mock-event-service";
import { of } from "rxjs";
import { EventsWidgetComponent } from "./events-widget.component";

function makeEventsResponse(events: { id: number; name: string; active: boolean }[]): PiResponse<EventHandler[]> {
  return {
    id: 1,
    jsonrpc: "2.0",
    signature: "",
    time: 0,
    version: "",
    versionnumber: "",
    detail: {},
    result: {
      status: true,
      value: events.map((e) => ({
        id: e.id,
        name: e.name,
        active: e.active,
        handlermodule: "",
        ordering: 0,
        position: "post",
        event: [],
        action: "",
        options: {},
        conditions: {}
      }))
    }
  };
}

describe("EventsWidgetComponent", () => {
  let fixture: ComponentFixture<EventsWidgetComponent>;
  let component: EventsWidgetComponent;
  let authMock: MockAuthService;
  let eventMock: MockEventService;

  const instance: WidgetInstance = { id: "events-1", type: "events", x: 0, y: 0, cols: 8, rows: 5 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventsWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: EventService, useClass: MockEventService }
      ]
    }).compileComponents();

    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["eventhandling_read"] });

    eventMock = TestBed.inject(EventService) as unknown as MockEventService;
    eventMock.getEventHandlers.mockReturnValue(
      of(
        makeEventsResponse([
          { id: 1, name: "SendMail", active: true },
          { id: 2, name: "SetTokenInfo", active: true },
          { id: 3, name: "OldHandler", active: false }
        ])
      )
    );

    fixture = TestBed.createComponent(EventsWidgetComponent);
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
    expect(EventsWidgetComponent.type).toBe("events");
    expect(EventsWidgetComponent.title).toBeTruthy();
    expect(EventsWidgetComponent.icon).toBe("flag");
  });

  it("should override the static size constraints", () => {
    expect(EventsWidgetComponent.defaultSize).toEqual({ cols: 6, rows: 3 });
    expect(EventsWidgetComponent.minSize).toEqual({ cols: 4, rows: 3 });
    expect(EventsWidgetComponent.maxSize).toEqual({ cols: 10, rows: 6 });
  });

  it("should render Active Events and Inactive Events labels", () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain("Active Events");
    expect(text).toContain("Inactive Events");
  });

  it("should display the correct active and inactive counts", () => {
    const cells = fixture.nativeElement.querySelectorAll("td:last-child");
    const values = Array.from(cells).map((td: Element) => td.textContent?.trim());
    expect(values).toContain("2");
    expect(values).toContain("1");
  });

  it("should render active event names as links", () => {
    const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("a"));
    const names = links.map((a) => a.textContent?.trim());
    expect(names).toContain("SendMail");
    expect(names).toContain("SetTokenInfo");
  });

  it("should render inactive event names as links", () => {
    const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("a"));
    const names = links.map((a) => a.textContent?.trim());
    expect(names).toContain("OldHandler");
  });

  it("should render nothing when eventhandling_read right is missing", () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });

    const fixture2 = TestBed.createComponent(EventsWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.nativeElement.querySelector("table")).toBeNull();
    fixture2.destroy();
  });
});
