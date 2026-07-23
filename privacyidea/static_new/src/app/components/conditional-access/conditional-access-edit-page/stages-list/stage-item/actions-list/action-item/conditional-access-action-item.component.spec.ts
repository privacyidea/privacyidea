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
import { ConditionalAccessActionItemComponent } from "./conditional-access-action-item.component";

describe("ConditionalAccessActionItemComponent", () => {
  let component: ConditionalAccessActionItemComponent;
  let fixture: ComponentFixture<ConditionalAccessActionItemComponent>;

  function setAction(action: LockoutStageAction): void {
    fixture.componentRef.setInput("action", action);
    fixture.detectChanges();
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessActionItemComponent],
      providers: [{ provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService }]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionalAccessActionItemComponent);
    component = fixture.componentInstance;
    setAction({ action_type: "LOCK_USER", action_value: 600 });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should describe every action type", () => {
    for (const type of ["LOCK_USER", "PERMANENT_LOCK_USER", "BLOCK_IP", "ALLOW", "DENY", "EMAIL_USER"] as const) {
      setAction({ action_type: type, action_value: null });
      expect(component.actionDescription().length).toBeGreaterThan(0);
    }
  });

  it("should classify the value mode from the action type", () => {
    setAction({ action_type: "LOCK_USER", action_value: 600 });
    expect(component.valueMode()).toBe("duration");
    setAction({ action_type: "EMAIL_ADMIN", action_value: {} });
    expect(component.valueMode()).toBe("email");
    setAction({ action_type: "ALLOW", action_value: null });
    expect(component.valueMode()).toBe("none");
  });

  describe("duration", () => {
    it("should read a plain-number duration", () => {
      setAction({ action_type: "LOCK_USER", action_value: 600 });
      expect(component.durationValue()).toBe("600");
    });

    it("should read a nested duration_seconds", () => {
      setAction({ action_type: "LOCK_USER", action_value: { duration_seconds: 30 } });
      expect(component.durationValue()).toBe("30");
    });

    it("should emit the parsed integer on input and null when cleared", () => {
      const spy = jest.spyOn(component.updateAction, "emit");
      component.onDurationInput("45");
      expect(spy).toHaveBeenCalledWith({ action_value: 45 });
      component.onDurationInput("");
      expect(spy).toHaveBeenCalledWith({ action_value: null });
    });
  });

  describe("email", () => {
    it("should include recipient_group only for EMAIL_ADMIN", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: {} });
      expect(component.emailFields().map((f) => f.key)).toContain("recipient_group");
      setAction({ action_type: "EMAIL_USER", action_value: {} });
      expect(component.emailFields().map((f) => f.key)).not.toContain("recipient_group");
    });

    it("should default the mimetype to plain when unset", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: {} });
      expect(component.emailFieldValue("mimetype")).toBe("plain");
      expect(component.emailFieldValue("subject")).toBe("");
    });

    it("should merge a field into the value object", () => {
      const spy = jest.spyOn(component.updateAction, "emit");
      setAction({ action_type: "EMAIL_ADMIN", action_value: { subject: "Hi" } });
      component.onEmailFieldInput("body", "Hello {user}");
      expect(spy).toHaveBeenCalledWith({ action_value: { subject: "Hi", body: "Hello {user}" } });
    });

    it("should drop an emptied non-mimetype field", () => {
      const spy = jest.spyOn(component.updateAction, "emit");
      setAction({ action_type: "EMAIL_ADMIN", action_value: { subject: "Hi", body: "x" } });
      component.onEmailFieldInput("body", "");
      expect(spy).toHaveBeenCalledWith({ action_value: { subject: "Hi" } });
    });
  });

  it("should reset the value when the type changes to another mode", () => {
    const spy = jest.spyOn(component.updateAction, "emit");
    setAction({ action_type: "EMAIL_ADMIN", action_value: { subject: "Hi" } });
    component.onActionTypeChange("LOCK_USER");
    expect(spy).toHaveBeenCalledWith({ action_type: "LOCK_USER", action_value: null });
  });

  it("should keep the value when the type stays in the same mode", () => {
    const spy = jest.spyOn(component.updateAction, "emit");
    setAction({ action_type: "LOCK_USER", action_value: 600 });
    component.onActionTypeChange("BLOCK_IP");
    expect(spy).toHaveBeenCalledWith({ action_type: "BLOCK_IP" });
  });

  it("should emit removeAction", () => {
    const spy = jest.spyOn(component.removeAction, "emit");
    component.onRemoveAction();
    expect(spy).toHaveBeenCalled();
  });
});
