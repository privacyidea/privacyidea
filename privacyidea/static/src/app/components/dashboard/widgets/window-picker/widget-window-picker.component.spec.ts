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
import { METRICS_WINDOWS } from "@components/dashboard/widgets/metrics-window";
import { WidgetWindowPickerComponent } from "./widget-window-picker.component";

describe("WidgetWindowPickerComponent", () => {
  let fixture: ComponentFixture<WidgetWindowPickerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WidgetWindowPickerComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    fixture = TestBed.createComponent(WidgetWindowPickerComponent);
    fixture.componentRef.setInput("choices", METRICS_WINDOWS);
    fixture.componentRef.setInput("selected", METRICS_WINDOWS[0]);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it("should name the selected window on the trigger, so the span is legible without opening the menu", () => {
    const label = fixture.nativeElement.querySelector(".window-label") as HTMLElement;
    expect(label.textContent?.trim()).toBe(METRICS_WINDOWS[0].label);
  });

  it("should follow the selection it is given", () => {
    fixture.componentRef.setInput("selected", METRICS_WINDOWS[2]);
    fixture.detectChanges();

    const label = fixture.nativeElement.querySelector(".window-label") as HTMLElement;
    expect(label.textContent?.trim()).toBe(METRICS_WINDOWS[2].label);
  });
});
