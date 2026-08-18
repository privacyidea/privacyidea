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

  describe("redundant restrictions", () => {
    const withActions = (list: LockoutStageAction[]) => {
      fixture.componentRef.setInput("actions", list);
      fixture.detectChanges();
    };

    it("should flag a timed restriction that sits next to a permanent one", () => {
      // The permanent lock wins the row whichever order they run in, so the timed action changes nothing.
      withActions([
        { action_type: "LOCK_USER", action_value: 600 },
        { action_type: "PERMANENT_LOCK_USER", action_value: null }
      ]);
      expect(component.redundantRestrictionPairs()).toEqual([["LOCK_USER", "PERMANENT_LOCK_USER"]]);

      withActions([
        { action_type: "BLOCK_IP", action_value: 600 },
        { action_type: "PERMANENT_BLOCK_IP", action_value: null }
      ]);
      // Both ends are reported, so the warning can name the action that is doing nothing.
      expect(component.redundantRestrictionPairs()).toEqual([["BLOCK_IP", "PERMANENT_BLOCK_IP"]]);
    });

    it("should not flag a stage that carries only one kind of restriction", () => {
      withActions([{ action_type: "LOCK_USER", action_value: 600 }]);
      expect(component.redundantRestrictionPairs()).toEqual([]);

      withActions([{ action_type: "PERMANENT_BLOCK_IP", action_value: null }]);
      expect(component.redundantRestrictionPairs()).toEqual([]);
    });

    it("should not flag a timed and a permanent action that restrict different subjects", () => {
      // The server confines a stage's actions to one target, so this cannot be saved today - but the pairing
      // is checked per subject so that it stays correct if a stage is ever allowed to mix them. A user lock
      // and an IP block are separate rows: neither overrides the other.
      withActions([
        { action_type: "LOCK_USER", action_value: 600 },
        { action_type: "PERMANENT_BLOCK_IP", action_value: null }
      ]);
      expect(component.redundantRestrictionPairs()).toEqual([]);
    });

    it("should name both actions in the rendered warning", () => {
      // The point of the warning is telling the admin which two of their actions conflict, so the text has to
      // carry the names - a stage with several actions gives them nothing to go on otherwise.
      withActions([
        { action_type: "LOCK_USER", action_value: 600 },
        { action_type: "EMAIL_ADMIN", action_value: null },
        { action_type: "PERMANENT_LOCK_USER", action_value: null }
      ]);
      const warning = fixture.nativeElement.querySelector(".ca-actions-list-warning");
      expect(warning).toBeTruthy();
      expect(warning.textContent).toContain("LOCK_USER");
      expect(warning.textContent).toContain("PERMANENT_LOCK_USER");
    });
  });
});
