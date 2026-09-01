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
import { AuthService } from "@services/auth/auth.service";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessActionType,
  ConditionalAccessStageAction,
  ConditionalAccessTarget
} from "@services/conditional-access/conditional-access-policy.service";
import { SmtpServer, SmtpService } from "@services/smtp/smtp.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockConditionalAccessPolicyService } from "@testing/mock-services/mock-conditional-access-policy-service";
import { MockSmtpService } from "@testing/mock-services/mock-smtp-service";
import { ConditionalAccessActionItemComponent } from "./conditional-access-action-item.component";

describe("ConditionalAccessActionItemComponent", () => {
  let component: ConditionalAccessActionItemComponent;
  let fixture: ComponentFixture<ConditionalAccessActionItemComponent>;
  let authService: MockAuthService;
  let smtpService: MockSmtpService;

  function setAction(action: ConditionalAccessStageAction): void {
    fixture.componentRef.setInput("action", action);
    fixture.detectChanges();
  }

  function setRights(rights: string[]): void {
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights });
    fixture.detectChanges();
  }

  function smtpServer(identifier: string): SmtpServer {
    return {
      identifier,
      server: "mail.example.com",
      port: 25,
      timeout: 120,
      sender: "",
      tls: false,
      enqueue_job: false,
      smime: false,
      dont_send_on_error: true
    };
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessActionItemComponent],
      providers: [
        { provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SmtpService, useClass: MockSmtpService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionalAccessActionItemComponent);
    component = fixture.componentInstance;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    smtpService = TestBed.inject(SmtpService) as unknown as MockSmtpService;
    setAction({ action_type: "LOCK_USER", action_value: 600 });
    // The rights of a default install, where no admin policy narrows them.
    setRights(["smtpserver_read"]);
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should describe every action type", () => {
    for (const type of ["LOCK_USER", "PERMANENT_LOCK_USER", "BLOCK_IP", "DENY", "EMAIL_USER"] as const) {
      setAction({ action_type: type, action_value: null });
      expect(component.actionDescription().length).toBeGreaterThan(0);
    }
  });

  it("should classify the value mode from the action type", () => {
    setAction({ action_type: "LOCK_USER", action_value: 600 });
    expect(component.valueMode()).toBe("duration");
    setAction({ action_type: "EMAIL_ADMIN", action_value: {} });
    expect(component.valueMode()).toBe("email");
    setAction({ action_type: "DENY", action_value: null });
    expect(component.valueMode()).toBe("none");
  });

  describe("target compatibility", () => {
    let policyServiceMock: MockConditionalAccessPolicyService;

    beforeEach(() => {
      policyServiceMock = TestBed.inject(
        ConditionalAccessPolicyService
      ) as unknown as MockConditionalAccessPolicyService;
      policyServiceMock.actionsByTarget.set({
        user: ["LOCK_USER", "PERMANENT_LOCK_USER", "EMAIL_ADMIN", "EMAIL_USER", "DENY"],
        source_ip: ["BLOCK_IP", "PERMANENT_BLOCK_IP", "EMAIL_ADMIN", "DENY"]
      });
    });

    it("flags an action that is not allowed for the current target", () => {
      fixture.componentRef.setInput("target", "source_ip");
      setAction({ action_type: "LOCK_USER", action_value: 600 });
      expect(component.isActionAllowedForTarget()).toBe(false);
      // the stale type stays selectable so the user can change it
      expect(component.allowedActionTypes()).toContain("LOCK_USER");
    });

    it("accepts an action that is allowed for the current target", () => {
      fixture.componentRef.setInput("target", "source_ip");
      setAction({ action_type: "BLOCK_IP", action_value: 600 });
      expect(component.isActionAllowedForTarget()).toBe(true);
    });

    it("does not flag while the allowed list is still empty", () => {
      policyServiceMock.actionsByTarget.set({} as Record<ConditionalAccessTarget, ConditionalAccessActionType[]>);
      policyServiceMock.actionTypes.set([]);
      fixture.componentRef.setInput("target", "source_ip");
      setAction({ action_type: "LOCK_USER", action_value: 600 });
      expect(component.isActionAllowedForTarget()).toBe(true);
    });
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

    it("should convert the entered value to seconds using the selected unit", () => {
      setAction({ action_type: "LOCK_USER", action_value: null });
      const spy = jest.spyOn(component.updateAction, "emit");
      component.durationUnit.set("minutes");
      component.onDurationInput("5");
      expect(spy).toHaveBeenCalledWith({ action_value: 300 });
    });

    it("should display the stored seconds in the selected unit", () => {
      setAction({ action_type: "LOCK_USER", action_value: 3600 });
      component.durationUnit.set("hours");
      expect(component.durationValue()).toBe("1");
    });

    it("should keep the entered number and re-scale to seconds on unit change", () => {
      setAction({ action_type: "LOCK_USER", action_value: 120 });
      const spy = jest.spyOn(component.updateAction, "emit");
      component.onDurationUnitChange("minutes");
      expect(component.durationUnit()).toBe("minutes");
      // "120" kept and re-interpreted as 120 minutes = 7200s.
      expect(spy).toHaveBeenCalledWith({ action_value: 7200 });
    });

    it("should not emit on unit change when there is no value", () => {
      setAction({ action_type: "LOCK_USER", action_value: null });
      const spy = jest.spyOn(component.updateAction, "emit");
      component.onDurationUnitChange("hours");
      expect(spy).not.toHaveBeenCalled();
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

    describe("SMTP server", () => {
      it("offers the configured identifiers as a select", () => {
        smtpService.smtpServers.set([smtpServer("primary"), smtpServer("backup")]);
        setAction({ action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "backup" } });
        expect(component.emailFields().find((field) => field.key === "smtp_identifier")?.kind).toBe("smtp");
        expect(component.smtpOptions()).toEqual(["primary", "backup"]);
        expect(component.staleSmtpIdentifier()).toBe("");
      });

      it("keeps and flags an identifier that is no longer configured", () => {
        smtpService.smtpServers.set([smtpServer("primary")]);
        setAction({ action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "retired" } });
        // Listed, or the select would show a blank trigger for the value the action carries.
        expect(component.smtpOptions()).toEqual(["primary", "retired"]);
        expect(component.staleSmtpIdentifier()).toBe("retired");
      });

      it("flags nothing while no server has been listed yet", () => {
        setAction({ action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "primary" } });
        expect(component.smtpOptions()).toEqual(["primary"]);
        expect(component.staleSmtpIdentifier()).toBe("");
      });

      it("falls back to a plain input with an explaining hint without smtpserver_read", () => {
        setAction({ action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "primary" } });
        setRights([]);
        const field = component.emailFields().find((each) => each.key === "smtp_identifier");
        expect(field?.kind).toBe("text");
        expect(field?.hint).toContain("smtpserver_read");
        // Flagged in the error colour: it reports a missing right, not a description of the field.
        expect(field?.hintWarn).toBe(true);
      });
    });
  });

  describe("email actions without smtpserver_read", () => {
    beforeEach(() => {
      const policyServiceMock = TestBed.inject(
        ConditionalAccessPolicyService
      ) as unknown as MockConditionalAccessPolicyService;
      policyServiceMock.actionsByTarget.set({
        user: ["LOCK_USER", "PERMANENT_LOCK_USER", "EMAIL_ADMIN", "EMAIL_USER", "DENY"],
        source_ip: ["BLOCK_IP", "PERMANENT_BLOCK_IP", "EMAIL_ADMIN", "DENY"]
      });
      setRights([]);
    });

    it("still offers them, only without the server list", () => {
      setAction({ action_type: "LOCK_USER", action_value: 600 });
      expect(component.smtpServersListable()).toBe(false);
      expect(component.allowedActionTypes()).toContain("EMAIL_ADMIN");
      expect(component.allowedActionTypes()).toContain("EMAIL_USER");
      expect(component.allowedActionTypes()).toContain("LOCK_USER");
    });

    it("keeps one the policy already carries valid for its target", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "primary" } });
      expect(component.allowedActionTypes()).toContain("EMAIL_ADMIN");
      // The action is still valid for a user-targeted policy: it is the SMTP config that is out of reach, not the
      // action type, so nothing is flagged as target-incompatible.
      expect(component.isActionAllowedForTarget()).toBe(true);
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

  describe("retrigger", () => {
    it("should emit updateAction when the checkbox toggles", () => {
      const spy = jest.spyOn(component.updateAction, "emit");
      component.onRetriggerChange(true);
      expect(spy).toHaveBeenCalledWith({ retrigger_above_threshold: true });
      component.onRetriggerChange(false);
      expect(spy).toHaveBeenCalledWith({ retrigger_above_threshold: false });
    });

    it("should default the checkbox by action type when unset", () => {
      // LOCK_USER defaults to fire-once (unchecked).
      setAction({ action_type: "LOCK_USER", action_value: 600 });
      expect(component.retriggerChecked()).toBe(false);
      // DENY defaults to re-trigger (checked).
      setAction({ action_type: "DENY", action_value: null });
      expect(component.retriggerChecked()).toBe(true);
    });

    it("should honor an explicit value over the action-type default", () => {
      setAction({ action_type: "DENY", action_value: null, retrigger_above_threshold: false });
      expect(component.retriggerChecked()).toBe(false);
      setAction({ action_type: "LOCK_USER", action_value: 600, retrigger_above_threshold: true });
      expect(component.retriggerChecked()).toBe(true);
    });
  });
});
