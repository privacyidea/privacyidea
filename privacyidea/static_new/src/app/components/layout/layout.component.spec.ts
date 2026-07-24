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

import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { RouterOutlet } from "@angular/router";
import { MatProgressBar } from "@angular/material/progress-bar";
import { DebugNoticeComponent } from "@components/layout/debug-notice/debug-notice.component";
import { LayoutComponent } from "@components/layout/layout.component";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { LoadingService } from "@services/loading/loading-service";
import { MockAuthService, MockContentService } from "@testing/mock-services";

@Component({ selector: "app-navigation", template: "", standalone: true })
class NavigationStubComponent {}

@Component({ selector: "app-navigation-self-service", template: "", standalone: true })
class NavigationSelfServiceStubComponent {}

@Component({ selector: "app-navigation-self-service-wizard", template: "", standalone: true })
class NavigationSelfServiceWizardStubComponent {}

class MockLoadingService {
  addListener = jest.fn();
  removeListener = jest.fn();
  isLoading = jest.fn().mockReturnValue(false);
  getLoadingUrls = jest.fn().mockReturnValue([]);
}

describe("LayoutComponent", () => {
  let component: LayoutComponent;
  let fixture: ComponentFixture<LayoutComponent>;

  beforeAll(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn()
      })
    });
  });

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [LayoutComponent],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: LoadingService, useClass: MockLoadingService }
      ]
    })
      .overrideComponent(LayoutComponent, {
        set: {
          imports: [
            RouterOutlet,
            MatProgressBar,
            NavigationStubComponent,
            NavigationSelfServiceStubComponent,
            NavigationSelfServiceWizardStubComponent,
            DebugNoticeComponent
          ]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(LayoutComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render router-outlet in the DOM", () => {
    fixture.detectChanges();

    const layoutElement = fixture.nativeElement.querySelector(".layout");
    expect(layoutElement).toBeTruthy();

    const main = fixture.nativeElement.querySelector('main[aria-label="Main Router Outlet"]');
    expect(main).toBeTruthy();
  });
});
