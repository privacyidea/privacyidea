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
import { LockoutStageAction } from "@services/conditional-access/conditional-access-policy.service";
import { ConditionalAccessActionItemComponent } from "./conditional-access-action-item.component";

describe("ConditionalAccessActionItemComponent", () => {
  let component: ConditionalAccessActionItemComponent;
  let fixture: ComponentFixture<ConditionalAccessActionItemComponent>;

  const action: LockoutStageAction = { action_type: "LOCK_USER", action_value: { lock_duration_seconds: 600 } };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessActionItemComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionalAccessActionItemComponent);
    fixture.componentRef.setInput("action", action);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should format the initial action_value as pretty JSON", () => {
    expect(component.actionValueText()).toBe(JSON.stringify(action.action_value, null, 2));
  });

  it("should emit updateAction on action type change", () => {
    const spy = jest.spyOn(component.updateAction, "emit");
    component.onActionTypeChange("PERMANENT_LOCK_USER");
    expect(spy).toHaveBeenCalledWith({ action_type: "PERMANENT_LOCK_USER" });
  });

  it("should emit the parsed value for valid JSON input", () => {
    const spy = jest.spyOn(component.updateAction, "emit");
    component.onActionValueInput('{"lock_duration_seconds": 30}');
    expect(spy).toHaveBeenCalledWith({ action_value: { lock_duration_seconds: 30 } });
    expect(component.jsonError()).toBeNull();
  });

  it("should emit null action_value for empty input", () => {
    const spy = jest.spyOn(component.updateAction, "emit");
    component.onActionValueInput("");
    expect(spy).toHaveBeenCalledWith({ action_value: null });
  });

  it("should surface a JSON error and not emit for invalid input", () => {
    const spy = jest.spyOn(component.updateAction, "emit");
    component.onActionValueInput("{not json");
    expect(spy).not.toHaveBeenCalled();
    expect(component.jsonError()).not.toBeNull();
  });

  it("should emit removeAction", () => {
    const spy = jest.spyOn(component.removeAction, "emit");
    component.onRemoveAction();
    expect(spy).toHaveBeenCalled();
  });
});
