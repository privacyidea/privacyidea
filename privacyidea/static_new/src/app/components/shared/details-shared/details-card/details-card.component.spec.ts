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
import { Component, provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { DetailsCardComponent } from "./details-card.component";

@Component({
  standalone: true,
  imports: [DetailsCardComponent],
  template: `<app-details-card title="User"><span class="projected-content">content</span></app-details-card>`
})
class HostComponent {}

describe("DetailsCardComponent", () => {
  let fixture: ComponentFixture<DetailsCardComponent>;
  let component: DetailsCardComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DetailsCardComponent, HostComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    fixture = TestBed.createComponent(DetailsCardComponent);
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render the title when provided", () => {
    fixture.componentRef.setInput("title", "Status");
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector(".details-card-title")?.textContent?.trim()).toBe("Status");
  });

  it("should not render a title element when no title is set", () => {
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector(".details-card-title")).toBeNull();
  });

  it("should project content and render the title (host usage)", () => {
    const hostFixture = TestBed.createComponent(HostComponent);
    hostFixture.detectChanges();
    expect(hostFixture.nativeElement.querySelector(".details-card-title")?.textContent?.trim()).toBe("User");
    expect(hostFixture.nativeElement.querySelector(".projected-content")?.textContent).toBe("content");
  });
});
