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
import {
  ConditionalAccessPolicyService,
  LockoutPolicyStage
} from "@services/conditional-access/conditional-access-policy.service";
import { MockConditionalAccessPolicyService } from "@testing/mock-services/mock-conditional-access-policy-service";
import { ConditionalAccessStageItemComponent } from "./conditional-access-stage-item.component";

describe("ConditionalAccessStageItemComponent", () => {
  let component: ConditionalAccessStageItemComponent;
  let fixture: ComponentFixture<ConditionalAccessStageItemComponent>;

  const stage: LockoutPolicyStage = {
    failure_threshold: 5,
    priority: 1,
    actions: [{ action_type: "LOCK_USER", action_value: { lock_duration_seconds: 600 } }]
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessStageItemComponent],
      providers: [{ provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService }]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionalAccessStageItemComponent);
    fixture.componentRef.setInput("stage", stage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit updateStage for a valid failure_threshold", () => {
    const spy = jest.spyOn(component.updateStage, "emit");
    component.onFailureThresholdInput("10");
    expect(spy).toHaveBeenCalledWith({ failure_threshold: 10 });
  });

  it("should not emit for an invalid failure_threshold", () => {
    const spy = jest.spyOn(component.updateStage, "emit");
    component.onFailureThresholdInput("0");
    expect(spy).not.toHaveBeenCalled();
    component.onFailureThresholdInput("abc");
    expect(spy).not.toHaveBeenCalled();
  });

  it("should emit updateStage when actions change", () => {
    const spy = jest.spyOn(component.updateStage, "emit");
    component.onActionsChange([]);
    expect(spy).toHaveBeenCalledWith({ actions: [] });
  });

  it("should emit removeStage", () => {
    const spy = jest.spyOn(component.removeStage, "emit");
    component.onRemoveStage();
    expect(spy).toHaveBeenCalled();
  });

  it("should emit a trimmed name, or null when blank", () => {
    const spy = jest.spyOn(component.updateStage, "emit");
    component.onNameInput("  Warn user  ");
    expect(spy).toHaveBeenCalledWith({ name: "Warn user" });
    component.onNameInput("   ");
    expect(spy).toHaveBeenCalledWith({ name: null });
  });

  it("should toggle name editing", () => {
    expect(component.editingName()).toBe(false);
    component.startEditingName();
    expect(component.editingName()).toBe(true);
    component.stopEditingName();
    expect(component.editingName()).toBe(false);
  });
});
