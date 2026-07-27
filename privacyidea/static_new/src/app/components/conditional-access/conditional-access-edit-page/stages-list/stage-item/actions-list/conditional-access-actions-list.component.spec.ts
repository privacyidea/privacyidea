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
  LockoutStageAction
} from "@services/conditional-access/conditional-access-policy.service";
import { MockConditionalAccessPolicyService } from "@testing/mock-services/mock-conditional-access-policy-service";
import { ConditionalAccessActionsListComponent } from "./conditional-access-actions-list.component";

describe("ConditionalAccessActionsListComponent", () => {
  let component: ConditionalAccessActionsListComponent;
  let fixture: ComponentFixture<ConditionalAccessActionsListComponent>;

  const actions: LockoutStageAction[] = [
    { action_type: "LOCK_USER", action_value: { lock_duration_seconds: 600 } },
    { action_type: "EMAIL_ADMIN", action_value: null }
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessActionsListComponent],
      providers: [{ provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService }]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionalAccessActionsListComponent);
    fixture.componentRef.setInput("actions", actions);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit a new array with an appended action on add", () => {
    const spy = jest.spyOn(component.actionsChange, "emit");
    component.onAddAction();
    expect(spy).toHaveBeenCalledWith([...actions, { action_type: "LOCK_USER", action_value: null }]);
  });

  it("should default the new action to the first action allowed for the target", () => {
    const policyServiceMock = TestBed.inject(
      ConditionalAccessPolicyService
    ) as unknown as MockConditionalAccessPolicyService;
    policyServiceMock.actionsByTarget.set({
      user: ["LOCK_USER", "ALLOW", "DENY"],
      source_ip: ["BLOCK_IP", "ALLOW", "DENY"]
    });
    fixture.componentRef.setInput("target", "source_ip");

    const spy = jest.spyOn(component.actionsChange, "emit");
    component.onAddAction();
    expect(spy).toHaveBeenCalledWith([...actions, { action_type: "BLOCK_IP", action_value: null }]);
  });

  it("should emit a merged action on update by index", () => {
    const spy = jest.spyOn(component.actionsChange, "emit");
    component.onUpdateAction(1, { action_type: "EMAIL_USER" });
    expect(spy).toHaveBeenCalledWith([actions[0], { action_type: "EMAIL_USER", action_value: null }]);
  });

  it("should emit the array without the removed index", () => {
    const spy = jest.spyOn(component.actionsChange, "emit");
    component.onRemoveAction(0);
    expect(spy).toHaveBeenCalledWith([actions[1]]);
  });
});
