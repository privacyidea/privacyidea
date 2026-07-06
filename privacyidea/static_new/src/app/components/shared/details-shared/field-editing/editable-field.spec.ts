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
import { DetailsEditRegistry } from "./details-edit-registry.service";
import { EditableField, EditableFieldOptions, injectEditableField } from "./editable-field";

let currentOptions: EditableFieldOptions;

@Component({ standalone: true, template: "" })
class HostComponent {
  readonly field = injectEditableField(currentOptions);
}

describe("injectEditableField", () => {
  let registry: DetailsEditRegistry;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [DetailsEditRegistry]
    });
    registry = TestBed.inject(DetailsEditRegistry);
  });

  function createField(options: EditableFieldOptions): {
    fixture: ComponentFixture<HostComponent>;
    field: EditableField;
  } {
    currentOptions = options;
    const fixture = TestBed.createComponent(HostComponent);
    return { fixture, field: fixture.componentInstance.field };
  }

  it("registers with the registry on creation and starts not editing", () => {
    const { field } = createField({ onCommit: async () => undefined });
    expect(field.isEditing()).toBe(false);
    expect(registry.anyEditing()).toBe(false);

    field.toggle();
    expect(field.isEditing()).toBe(true);
    expect(registry.anyEditing()).toBe(true);
  });

  it("unregisters from the registry on destroy", () => {
    const { fixture, field } = createField({ onCommit: async () => undefined });
    field.toggle();
    expect(registry.anyEditing()).toBe(true);

    fixture.destroy();
    expect(registry.anyEditing()).toBe(false);
  });

  it("runs onOpen only when entering edit mode", () => {
    const onOpen = jest.fn();
    const { field } = createField({ onOpen, onCommit: async () => undefined });

    field.toggle();
    expect(onOpen).toHaveBeenCalledTimes(1);

    field.toggle();
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("keeps edit mode open when onCommit returns false", async () => {
    const { field } = createField({ onCommit: async () => false });
    field.toggle();

    await field.commit();
    expect(field.isEditing()).toBe(true);
  });

  it("closes edit mode when onCommit returns void", async () => {
    const onCommit = jest.fn(async () => undefined);
    const { field } = createField({ onCommit });
    field.toggle();

    await field.commit();
    expect(onCommit).toHaveBeenCalledTimes(1);
    expect(field.isEditing()).toBe(false);
  });

  it("closes edit mode when onCommit returns true", async () => {
    const { field } = createField({ onCommit: async () => true });
    field.toggle();

    await field.commit();
    expect(field.isEditing()).toBe(false);
  });

  it("keeps edit mode open when onCommit resolves to false", async () => {
    const { field } = createField({ onCommit: () => Promise.resolve(false) });
    field.toggle();

    field.commit();
    await Promise.resolve();
    expect(field.isEditing()).toBe(true);
  });

  it("closes edit mode when onCommit resolves to void", async () => {
    const { field } = createField({ onCommit: () => Promise.resolve() });
    field.toggle();

    field.commit();
    await Promise.resolve();
    expect(field.isEditing()).toBe(false);
  });

  it("cancel always closes edit mode and calls onCancel", () => {
    const onCancel = jest.fn();
    const { field } = createField({ onCancel, onCommit: async () => undefined });
    field.toggle();

    field.cancel();
    expect(field.isEditing()).toBe(false);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
