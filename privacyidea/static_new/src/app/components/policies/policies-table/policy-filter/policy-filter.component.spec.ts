/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PolicyFilterComponent } from "./policy-filter.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { FilterValueGeneric } from "src/app/core/models/filter_value_generic/filter-value-generic";
import { PolicyDetail } from "src/app/services/policies/policies.service";
import { Component, output, Input } from "@angular/core";

@Component({ selector: "app-clearable-input", standalone: true, template: "<ng-content></ng-content>" })
class MockClearableInput {
  onClick = output<void>();
  @Input() showClearButton = false;
}

describe("PolicyFilterComponent", () => {
  let component: PolicyFilterComponent;
  let fixture: ComponentFixture<PolicyFilterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyFilterComponent, NoopAnimationsModule]
    })
      .overrideComponent(PolicyFilterComponent, {
        set: { imports: [MockClearableInput] }
      })
      .compileComponents();

    fixture = TestBed.createComponent(PolicyFilterComponent);
    component = fixture.componentInstance;
    component.initialFilter = new FilterValueGeneric<PolicyDetail>({ availableFilters: [] });
    fixture.detectChanges();
  });

  it("should update state only if rawValue differs", () => {
    const filter = new FilterValueGeneric<PolicyDetail>({ availableFilters: [] }).setByString("test:1");
    const setSpy = jest.spyOn(component.filter, "set");

    // First call: updates
    component.updateFilterManually(filter);
    expect(setSpy).toHaveBeenCalledTimes(1);

    // Second call with same rawValue: ignored
    component.updateFilterManually(filter);
    expect(setSpy).toHaveBeenCalledTimes(1);
  });
});
