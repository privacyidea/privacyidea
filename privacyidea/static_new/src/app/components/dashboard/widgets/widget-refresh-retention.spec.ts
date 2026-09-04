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
import { TokenTypesWidgetComponent } from "@components/dashboard/widgets/token-types-widget/token-types-widget.component";
import { TokensWidgetComponent } from "@components/dashboard/widgets/tokens-widget/tokens-widget.component";
import { WidgetFrameComponent } from "@components/dashboard/widget-frame/widget-frame.component";
import { WidgetInstance } from "@models/dashboard";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { TokenCount, TokenService } from "@services/token/token.service";
import { MockAuditService } from "@testing/mock-services/mock-audit-service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockContentService } from "@testing/mock-services/mock-content-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { of, throwError } from "rxjs";

function makeInstance(type: WidgetInstance["type"]): WidgetInstance {
  return { id: type + "-1", type, x: 0, y: 0, cols: 6, rows: 5 };
}

describe("widget data retention across a failed refresh", () => {
  let store: DashboardDataStore;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokensWidgetComponent, TokenTypesWidgetComponent, WidgetFrameComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: AuditService, useClass: MockAuditService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService }
      ]
    }).compileComponents();

    (TestBed.inject(AuthService) as unknown as MockAuthService).actionAllowed.mockReturnValue(true);
    store = TestBed.inject(DashboardDataStore);
  });

  describe("TokensWidgetComponent", () => {
    let fixture: ComponentFixture<TokensWidgetComponent>;
    let tokenMock: MockTokenService;

    beforeEach(() => {
      tokenMock = TestBed.inject(TokenService) as unknown as MockTokenService;
      tokenMock.getTokenCount.mockImplementation(() => of(MockPiResponse.fromValue<TokenCount>({ count: 12 })));

      fixture = TestBed.createComponent(TokensWidgetComponent);
      fixture.componentRef.setInput("instance", makeInstance("tokens"));
      fixture.detectChanges();
    });

    afterEach(() => fixture.destroy());

    it("keeps the state ready and the loaded counts when a refresh fails", () => {
      expect(fixture.componentInstance.counts().total).toBe(12);

      tokenMock.getTokenCount.mockImplementation(() => throwError(() => new Error("boom")));
      store.refreshAll();
      fixture.detectChanges();

      expect(fixture.componentInstance.state()).toBe("ready");
      expect(fixture.componentInstance.refreshFailed()).toBe(true);
      expect(fixture.componentInstance.counts().total).toBe(12);
    });

    it("keeps the loaded counts when the widget's own refresh button fails", () => {
      expect(fixture.componentInstance.counts().total).toBe(12);

      tokenMock.getTokenCount.mockImplementation(() => throwError(() => new Error("boom")));
      fixture.componentInstance.reload();
      fixture.detectChanges();

      expect(fixture.componentInstance.state()).toBe("ready");
      expect(fixture.componentInstance.refreshFailed()).toBe(true);
      expect(fixture.componentInstance.counts().total).toBe(12);
      expect(fixture.nativeElement.textContent).not.toContain("Could not load data.");
    });

    it("still reports error when the very first load fails", () => {
      store.invalidate();
      tokenMock.getTokenCount.mockImplementation(() => throwError(() => new Error("boom")));

      const failed = TestBed.createComponent(TokensWidgetComponent);
      failed.componentRef.setInput("instance", makeInstance("tokens"));
      failed.detectChanges();

      expect(failed.componentInstance.state()).toBe("error");
      failed.destroy();
    });
  });

  describe("TokenTypesWidgetComponent", () => {
    it("still reports error when every token type failed to load", () => {
      const tokenMock = TestBed.inject(TokenService) as unknown as MockTokenService;
      tokenMock.getTokenCount.mockImplementation(() => throwError(() => new Error("boom")));

      const fixture = TestBed.createComponent(TokenTypesWidgetComponent);
      fixture.componentRef.setInput("instance", makeInstance("token-types"));
      fixture.detectChanges();

      expect(fixture.componentInstance.allTypesFailed()).toBe(true);
      expect(fixture.componentInstance.state()).toBe("error");
      fixture.destroy();
    });
  });

  describe("WidgetFrameComponent", () => {
    it("marks the widget as stale instead of blanking it when a refresh fails", () => {
      const tokenMock = TestBed.inject(TokenService) as unknown as MockTokenService;
      tokenMock.getTokenCount.mockImplementation(() => of(MockPiResponse.fromValue<TokenCount>({ count: 12 })));

      const fixture = TestBed.createComponent(WidgetFrameComponent);
      fixture.componentRef.setInput("instance", makeInstance("tokens"));
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector(".widget-stale")).toBeNull();

      tokenMock.getTokenCount.mockImplementation(() => throwError(() => new Error("boom")));
      store.refreshAll();
      fixture.detectChanges();

      const body = fixture.nativeElement.querySelector(".widget-body") as HTMLElement;
      expect(fixture.nativeElement.querySelector(".widget-stale")).not.toBeNull();
      expect(body.textContent).toContain("12");
      expect(body.textContent).not.toContain("Could not load data.");
      fixture.destroy();
    });
  });
});
