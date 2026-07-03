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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { EditableField } from "@components/shared/details-shared/field-editing/editable-field";
import { DetailFieldComponent } from "./detail-field.component";
import { DetailsEditRegistry } from "../field-editing/details-edit-registry.service";

interface DetailFieldInternals {
  field: EditableField;
}

describe("DetailFieldComponent", () => {
  let fixture: ComponentFixture<DetailFieldComponent>;
  let component: DetailFieldComponent;
  let internals: DetailFieldInternals;
  let registry: DetailsEditRegistry;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [DetailFieldComponent],
      providers: [DetailsEditRegistry]
    });
    fixture = TestBed.createComponent(DetailFieldComponent);
    component = fixture.componentInstance;
    internals = component as unknown as DetailFieldInternals;
    registry = TestBed.inject(DetailsEditRegistry);
    fixture.componentRef.setInput("label", "Max Count");
    fixture.componentRef.setInput("editable", true);
    fixture.componentRef.setInput("editValue", "15");
    fixture.detectChanges();
  });

  it("registers with the registry and starts not editing", () => {
    expect(internals.field.isEditing()).toBe(false);
    expect(registry.anyEditing()).toBe(false);
  });

  it("toggle loads the edit buffer and flips registry aggregation", () => {
    internals.field.toggle();
    expect(internals.field.isEditing()).toBe(true);
    expect(component.draft()).toBe("15");
    expect(registry.anyEditing()).toBe(true);
  });

  it("commit persists the draft via the save callback and exits editing", () => {
    const saveSpy = jest.fn();
    fixture.componentRef.setInput("save", saveSpy);

    internals.field.toggle();
    component.draft.set("20");
    internals.field.commit();

    expect(saveSpy).toHaveBeenCalledWith("20");
    expect(internals.field.isEditing()).toBe(false);
  });

  it("registry.saveAll drives the field's save while editing", async () => {
    const saveSpy = jest.fn();
    fixture.componentRef.setInput("save", saveSpy);

    internals.field.toggle();
    component.draft.set("99");
    await registry.saveAll();

    expect(saveSpy).toHaveBeenCalledWith("99");
    expect(internals.field.isEditing()).toBe(false);
  });

  it("cancel exits editing without saving", () => {
    const saveSpy = jest.fn();
    fixture.componentRef.setInput("save", saveSpy);

    internals.field.toggle();
    internals.field.cancel();

    expect(internals.field.isEditing()).toBe(false);
    expect(saveSpy).not.toHaveBeenCalled();
  });

  it("unregisters on destroy", () => {
    internals.field.toggle();
    expect(registry.anyEditing()).toBe(true);

    fixture.destroy();

    expect(registry.anyEditing()).toBe(false);
  });
});
