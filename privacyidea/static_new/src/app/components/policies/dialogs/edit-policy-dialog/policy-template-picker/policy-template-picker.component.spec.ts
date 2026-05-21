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
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { PolicyTemplatesService } from "@services/policy-templates/policy-templates.service";
import { MockPolicyTemplatesService } from "@testing/mock-services/mock-policy-templates-service";
import { PolicyTemplatePickerComponent } from "./policy-template-picker.component";

describe("PolicyTemplatePickerComponent", () => {
  let fixture: ComponentFixture<PolicyTemplatePickerComponent>;
  let component: PolicyTemplatePickerComponent;
  let templatesMock: MockPolicyTemplatesService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyTemplatePickerComponent],
      providers: [
        { provide: PolicyTemplatesService, useClass: MockPolicyTemplatesService },
        provideNoopAnimations()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyTemplatePickerComponent);
    component = fixture.componentInstance;
    templatesMock = TestBed.inject(PolicyTemplatesService) as unknown as MockPolicyTemplatesService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("starts collapsed", () => {
    expect(component.isExpanded()).toBe(false);
  });

  it("exposes the available templates as a list", () => {
    templatesMock.setIndex({
      webui1: "Users authenticate against privacyIDEA.",
      helpdesk: "A helpdesk user."
    });
    expect(component.templates()).toEqual([
      { name: "webui1", description: "Users authenticate against privacyIDEA." },
      { name: "helpdesk", description: "A helpdesk user." }
    ]);
  });

  it("emits a Partial<PolicyDetail> built from the selected template and collapses the panel", () => {
    templatesMock.setTemplate({
      name: "webui1",
      scope: "webui",
      action: { login_mode: "privacyIDEA", logout_time: "240" }
    });
    fixture.componentRef.setInput("currentPriority", 7);
    component.isExpanded.set(true);
    const emitSpy = jest.spyOn(component.templateApplied, "emit");

    component.selectTemplate("webui1");

    expect(emitSpy).toHaveBeenCalledWith({
      name: "webui1",
      scope: "webui",
      action: { login_mode: "privacyIDEA", logout_time: "240" },
      priority: 7
    });
    expect(component.isExpanded()).toBe(false);
  });

  it("falls back to priority 1 when the current priority is 0", () => {
    templatesMock.setTemplate({ name: "tpl", scope: "admin" });
    fixture.componentRef.setInput("currentPriority", 0);
    const emitSpy = jest.spyOn(component.templateApplied, "emit");

    component.selectTemplate("tpl");

    expect(emitSpy).toHaveBeenCalledWith(expect.objectContaining({ priority: 1 }));
  });

  it("passes optional template fields through unchanged", () => {
    templatesMock.setTemplate({
      name: "complex",
      scope: "admin",
      realm: ["realm1"],
      resolver: ["resolverA"],
      adminrealm: ["adminrealm1"],
      conditions: [["userinfo", "memberOf", "equals", "admins", true, "raise_error"]],
      user_agents: ["PAM"]
    });
    const emitSpy = jest.spyOn(component.templateApplied, "emit");

    component.selectTemplate("complex");

    expect(emitSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        realm: ["realm1"],
        resolver: ["resolverA"],
        adminrealm: ["adminrealm1"],
        conditions: [["userinfo", "memberOf", "equals", "admins", true, "raise_error"]],
        user_agents: ["PAM"]
      })
    );
  });

  it("does not emit and stays expanded when the template is unknown", () => {
    const emitSpy = jest.spyOn(component.templateApplied, "emit");
    component.isExpanded.set(true);

    component.selectTemplate("missing");

    expect(emitSpy).not.toHaveBeenCalled();
    expect(component.isExpanded()).toBe(true);
  });
});
