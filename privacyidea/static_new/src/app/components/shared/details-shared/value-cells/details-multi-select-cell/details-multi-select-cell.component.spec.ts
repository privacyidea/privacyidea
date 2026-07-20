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
import { OverlayContainer } from "@angular/cdk/overlay";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatSelect, MatSelectChange } from "@angular/material/select";
import { DetailsMultiSelectCellComponent } from "./details-multi-select-cell.component";

describe("DetailsMultiSelectCellComponent", () => {
  let fixture: ComponentFixture<DetailsMultiSelectCellComponent>;
  let component: DetailsMultiSelectCellComponent;
  let overlayContainerElement: HTMLElement;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [DetailsMultiSelectCellComponent] });
    overlayContainerElement = TestBed.inject(OverlayContainer).getContainerElement();
    fixture = TestBed.createComponent(DetailsMultiSelectCellComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("selectLabel", "Select Realms");
    fixture.componentRef.setInput("options", [
      { value: "realm1", label: "realm1" },
      { value: "realm2", label: "realm2", disabled: true }
    ]);
    fixture.componentRef.setInput("selected", ["realm1"]);
    fixture.detectChanges();
  });

  it("renders one mat-option per option, disabled where requested", () => {
    fixture.nativeElement.querySelector(".mat-mdc-select-trigger").click();
    fixture.detectChanges();

    const options = overlayContainerElement.querySelectorAll(".mat-mdc-option");

    expect(options.length).toBe(2);
    expect(options[0].classList.contains("mdc-list-item--disabled")).toBe(false);
    expect(options[1].classList.contains("mdc-list-item--disabled")).toBe(true);
  });

  it("emits selectionChange with the new values", () => {
    const emitted: string[][] = [];
    component.selectionChange.subscribe((value) => emitted.push(value));

    const matSelect: MatSelect = fixture.debugElement.query(
      (el) => el.componentInstance instanceof MatSelect
    ).componentInstance;
    matSelect.selectionChange.emit({ value: ["realm1", "realm2"] } as MatSelectChange);

    expect(emitted).toContainEqual(["realm1", "realm2"]);
  });
});
