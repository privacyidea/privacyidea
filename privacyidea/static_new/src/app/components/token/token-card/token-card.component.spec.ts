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
import { Component, signal } from "@angular/core";
import { TokenCardComponent } from "./token-card.component";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { NoopAnimationsModule, provideNoopAnimations } from "@angular/platform-browser/animations";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MatTabChangeEvent } from "@angular/material/tabs";
import { provideRouter } from "@angular/router";

@Component({ standalone: true, template: "" })
class DummyComponent {
}

describe("TokenCardComponent", () => {
  let component: TokenCardComponent;
  let fixture: ComponentFixture<TokenCardComponent>;
  const mockEvent = (index: number): MatTabChangeEvent => ({
    index,
    tab: {} as any
  });

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenCardComponent, NoopAnimationsModule, DummyComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        provideRouter([
          {
            path: "tokens",
            component: DummyComponent,
            children: [{ path: "containers", component: DummyComponent }]
          }
        ])
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenCardComponent);
    component = fixture.componentInstance;
    component.selectedTabIndex = signal(0);
    component.tokenSerial = signal("Mock serial");
    component.containerSerial = signal("Mock container");
    component.states = signal([]);

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("onTabChange()", () => {
    it("should do nothing except reset `isProgrammaticChange` when it is true", () => {
      component.isProgrammaticTabChange.set(true);
      component.selectedTabIndex.set(1);
      component.containerSerial.set("Mock serial");
      component.tokenSerial.set("Mock serial");

      component.onTabChange(mockEvent(1));

      expect(component.selectedTabIndex()).toBe(1);
      expect(component.containerSerial()).toBe("Mock serial");
      expect(component.tokenSerial()).toBe("Mock serial");
    });
  });
});
