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
import { TokensWidgetComponent } from "@components/dashboard/widgets/tokens-widget/tokens-widget.component";
import { WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { DashboardLayoutService } from "@services/dashboard/dashboard-layout.service";
import { SubscriptionService } from "@services/subscription/subscription.service";
import { TokenService } from "@services/token/token.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockSubscriptionService } from "@testing/mock-services/mock-subscription-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";
import { WidgetFrameComponent } from "./widget-frame.component";

describe("WidgetFrameComponent", () => {
  let fixture: ComponentFixture<WidgetFrameComponent>;
  let component: WidgetFrameComponent;
  let layoutService: DashboardLayoutService;

  const tokensInstance: WidgetInstance = { id: "w1", type: "tokens", x: 0, y: 0, cols: 6, rows: 8 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WidgetFrameComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: SubscriptionService, useClass: MockSubscriptionService }
      ]
    }).compileComponents();

    layoutService = TestBed.inject(DashboardLayoutService);
    layoutService.editMode.set(false);

    fixture = TestBed.createComponent(WidgetFrameComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", tokensInstance);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should resolve the widget type for the instance type", () => {
    expect(component['widgetType']()?.type).toBe("tokens");
  });

  it("should resolve the component to render", () => {
    expect(component['component']()).toBe(TokensWidgetComponent);
  });

  it("should pass the instance through to the outlet inputs", () => {
    expect(component['outletInputs']()).toEqual({ instance: tokensInstance });
  });

  it("should render the widget title", () => {
    expect(fixture.nativeElement.querySelector(".widget-title").textContent).toContain("Tokens");
  });

  it("should hide the remove button in view mode", () => {
    expect(fixture.nativeElement.querySelector(".widget-remove")).toBeNull();
  });

  it("should show the remove button in edit mode", () => {
    layoutService.editMode.set(true);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector(".widget-remove")).not.toBeNull();
  });

  it("should remove the widget from the layout when remove is triggered", () => {
    const removeSpy = jest.spyOn(layoutService, "removeWidget");
    component['remove']();
    expect(removeSpy).toHaveBeenCalledWith("w1");
  });

  it("should remove the widget when the remove button is clicked in edit mode", () => {
    const removeSpy = jest.spyOn(layoutService, "removeWidget");
    layoutService.editMode.set(true);
    fixture.detectChanges();

    fixture.nativeElement.querySelector(".widget-remove").click();

    expect(removeSpy).toHaveBeenCalledWith("w1");
  });

  describe("pinned widget", () => {
    const subscriptionsInstance: WidgetInstance = { id: "s1", type: "subscriptions", x: 16, y: 0, cols: 8, rows: 5 };

    beforeEach(() => {
      fixture.componentRef.setInput("instance", subscriptionsInstance);
      layoutService.editMode.set(true);
      fixture.detectChanges();
    });

    it("should report the widget type as pinned", () => {
      expect(component['pinned']()).toBe(true);
    });

    it("should not offer a remove button in edit mode", () => {
      expect(fixture.nativeElement.querySelector(".widget-remove")).toBeNull();
    });

    it("should not mark the header as draggable in edit mode", () => {
      expect(fixture.nativeElement.querySelector(".widget-header.draggable")).toBeNull();
    });
  });
});
