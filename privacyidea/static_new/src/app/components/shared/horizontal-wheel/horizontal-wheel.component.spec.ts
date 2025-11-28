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
import { ComponentFixture, TestBed, fakeAsync, tick } from "@angular/core/testing";
import { HorizontalWheelComponent } from "./horizontal-wheel.component";
import { CommonModule } from "@angular/common";
import { Component, ViewChild, signal } from "@angular/core";

@Component({
  template: `<app-horizontal-wheel
    [values]="values"
    (onSelect)="onSelect($event)"></app-horizontal-wheel>`,
  standalone: true,
  imports: [CommonModule, HorizontalWheelComponent]
})
class TestHostComponent {
  values = signal(["A", "B", "C"]);
  selected: string | null = null;
  onSelect(val: string) {
    this.selected = val;
  }
  @ViewChild(HorizontalWheelComponent) wheel!: HorizontalWheelComponent;
}

describe("HorizontalWheelComponent", () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let host: TestHostComponent;
  let component: HorizontalWheelComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    host = fixture.componentInstance;
    fixture.detectChanges();
    component = host.wheel;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should handle mouse move when dragging", () => {
    component.isDragging = true;
    (component as any).containerElement = { scrollLeft: 50, offsetWidth: 200, style: {} };
    component.startX = 100;
    component.scrollLeft = 50;
    const fakeEvent = { preventDefault: () => {}, pageX: 120 } as any as MouseEvent;

    component.onMouseMove(fakeEvent);

    expect((component as any).containerElement.scrollLeft).toBe(30);
  });
});
