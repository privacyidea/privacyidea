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
import { signal, WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { applyEach, FieldTree, form } from "@angular/forms/signals";
import { By } from "@angular/platform-browser";
import { AuthService } from "@services/auth/auth.service";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessStageAction,
  ConditionalAccessTarget
} from "@services/conditional-access/conditional-access-policy.service";
import { SmtpService } from "@services/smtp/smtp.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockConditionalAccessPolicyService } from "@testing/mock-services/mock-conditional-access-policy-service";
import { MockSmtpService } from "@testing/mock-services/mock-smtp-service";
import { ConditionalAccessActionItemComponent } from "./action-item/conditional-access-action-item.component";
import { ConditionalAccessActionsListComponent } from "./conditional-access-actions-list.component";

describe("ConditionalAccessActionsListComponent", () => {
  let component: ConditionalAccessActionsListComponent;
  let fixture: ComponentFixture<ConditionalAccessActionsListComponent>;
  let model: WritableSignal<{ actions: ConditionalAccessStageAction[] }>;
  let actionFields: FieldTree<ConditionalAccessStageAction[]>;
  let policyServiceMock: MockConditionalAccessPolicyService;

  const actions: ConditionalAccessStageAction[] = [
    { action_type: "LOCK_USER", action_value: 600 },
    { action_type: "EMAIL_ADMIN", action_value: null }
  ];
  const items = () =>
    Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll("app-conditional-access-action-item"));
  const withActions = (list: ConditionalAccessStageAction[]) => {
    model.set({ actions: list.map((action) => ({ ...action })) });
    fixture.detectChanges();
  };
  const withTarget = (target: ConditionalAccessTarget) => fixture.componentRef.setInput("target", target);

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessActionsListComponent],
      providers: [
        { provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SmtpService, useClass: MockSmtpService }
      ]
    }).compileComponents();

    policyServiceMock = TestBed.inject(ConditionalAccessPolicyService) as unknown as MockConditionalAccessPolicyService;
    model = signal({ actions: actions.map((action) => ({ ...action })) });
    actionFields = TestBed.runInInjectionContext(() =>
      form(model, (p) => applyEach(p.actions, () => undefined))
    ).actions;
    fixture = TestBed.createComponent(ConditionalAccessActionsListComponent);
    fixture.componentRef.setInput("actions", actionFields);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render one item per action", () => {
    expect(items()).toHaveLength(2);
    expect(fixture.nativeElement.querySelector(".ca-actions-list-empty")).toBeNull();
  });

  // An item finds its own entry among the stage's actions by its place, so its own type stays selectable in its picker.
  it("should tell every item its place in the stage", () => {
    const indexes = fixture.debugElement
      .queryAll(By.directive(ConditionalAccessActionItemComponent))
      .map((item) => (item.componentInstance as ConditionalAccessActionItemComponent).actionIndex());
    expect(indexes).toEqual([0, 1]);
  });

  it("should say so when there are no actions", () => {
    withActions([]);
    expect(items()).toHaveLength(0);
    expect(fixture.nativeElement.querySelector(".ca-actions-list-empty")).toBeTruthy();
  });

  it("should append an action on add", () => {
    component.onAddAction();
    fixture.detectChanges();
    // EMAIL_ADMIN is the fallback once the target's allowed/unavailable types are both still unknown.
    expect(model().actions).toHaveLength(3);
    expect(model().actions[2]).toMatchObject({ action_type: "EMAIL_ADMIN", action_value: null });
    expect(items()).toHaveLength(3);
  });

  it("should add an action from the button", () => {
    (fixture.nativeElement.querySelector(".ca-actions-list ~ .ca-add-button-row button") as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(items()).toHaveLength(3);
  });

  it("should default the new action to the first action allowed for the target", () => {
    policyServiceMock.actionsByTarget.set({
      user: ["LOCK_USER", "DENY"],
      source_ip: ["BLOCK_IP", "DENY"]
    });
    withTarget("source_ip");

    component.onAddAction();
    expect(model().actions[2]).toMatchObject({ action_type: "BLOCK_IP", action_value: null });
  });

  // A singleton action already on the stage - and anything mutually exclusive with one - cannot be added
  // twice, so offering it would only produce an action the admin has to change straight away.
  it("should skip an action type the stage cannot take again", () => {
    policyServiceMock.actionsByTarget.set({
      user: ["LOCK_USER", "PERMANENT_LOCK_USER", "EMAIL_ADMIN", "DENY"],
      source_ip: ["BLOCK_IP", "DENY"]
    });
    policyServiceMock.unavailableActionTypes.mockReturnValue(new Set(["LOCK_USER", "PERMANENT_LOCK_USER"]));
    withActions([{ action_type: "LOCK_USER", action_value: null }]);

    component.onAddAction();
    // LOCK_USER is taken and PERMANENT_LOCK_USER contradicts it, so the first free type wins.
    expect(model().actions.map((action) => action.action_type)).toEqual(["LOCK_USER", "EMAIL_ADMIN"]);
  });

  it("should drop the action at the index on remove", () => {
    component.onRemoveAction(0);
    expect(model().actions).toMatchObject([{ action_type: "EMAIL_ADMIN", action_value: null }]);
  });

  it("should keep the item of the action that stays when another one is removed", () => {
    // Items follow their action rather than their position, so the one that stays is not rebound to another action.
    const [, second] = items();
    (items()[0].querySelector("button[aria-label='Remove action']") as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(items()).toHaveLength(1);
    expect(items()[0]).toBe(second);
  });

  it("should keep the item of an action that is edited", () => {
    // An edit rewrites the action in the form model; the item stays bound to its field, so its open panel survives.
    const [first] = items();
    actionFields[0]().value.update((action) => ({ ...action, action_value: 900 }));
    fixture.detectChanges();
    expect(items()[0]).toBe(first);
    expect(model().actions[0].action_value).toBe(900);
  });

  describe("redundant restrictions", () => {
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
