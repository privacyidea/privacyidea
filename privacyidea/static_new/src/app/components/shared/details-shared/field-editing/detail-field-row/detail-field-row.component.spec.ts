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
import { DetailFieldRowComponent } from "./detail-field-row.component";

@Component({
  standalone: true,
  imports: [DetailFieldRowComponent],
  template: `
    <app-detail-field-row
      label="KEY-CONTENT"
      [isEditing]="editing">
      <span fieldValue>VALUE-CONTENT</span>
      <span fieldEdit>EDIT-CONTENT</span>
    </app-detail-field-row>
  `
})
class HostComponent {
  editing = false;
}

describe("DetailFieldRowComponent", () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [HostComponent] });
    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("projects the three named slots into the key/value/edit skeleton", () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector(".detail-field-key")?.textContent).toContain("KEY-CONTENT");
    expect(el.querySelector(".value-content")?.textContent).toContain("VALUE-CONTENT");
    expect(el.querySelector(".value-edit")?.textContent).toContain("EDIT-CONTENT");
  });

  it("toggles the detail-field--editing host class from the isEditing input", () => {
    const rowEl = fixture.nativeElement.querySelector("app-detail-field-row") as HTMLElement;
    expect(rowEl.classList.contains("detail-field--editing")).toBe(false);

    host.editing = true;
    fixture.detectChanges();
    expect(rowEl.classList.contains("detail-field--editing")).toBe(true);

    host.editing = false;
    fixture.detectChanges();
    expect(rowEl.classList.contains("detail-field--editing")).toBe(false);
  });
});
