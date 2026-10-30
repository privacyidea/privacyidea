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
import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { form } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { By } from "@angular/platform-browser";
import { touchAll } from "@utils/form-state.utils";
import {
  ContainerRegistrationConfigComponent,
  ContainerRegistrationModel,
  DEFAULT_PASSPHRASE_PROMPT,
  emptyRegistration,
  PASSPHRASE_MISMATCH,
  registrationRules
} from "./container-registration-config.component";

@Component({
  imports: [ContainerRegistrationConfigComponent],
  template: `<app-container-registration-config [registration]="registrationForm" />`
})
class HostComponent {
  model = signal<ContainerRegistrationModel>(emptyRegistration());
  hasOwner = signal(true);
  active = signal(true);
  registrationForm = form(this.model, (f) =>
    registrationRules(f, { value: this.model, hasOwner: this.hasOwner, active: this.active })
  );
}

describe("ContainerRegistrationConfigComponent", () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const set = async (values: Partial<ContainerRegistrationModel>) => {
    host.model.update((model) => ({ ...model, ...values }));
    await flush();
  };
  const kinds = (field: { errors: () => { kind: string }[] }) => field.errors().map((error) => error.kind);
  const textarea = () => fixture.nativeElement.querySelector("textarea") as HTMLTextAreaElement;
  const inputs = () =>
    fixture.debugElement.queryAll(By.css("input[matinput]")).map((d) => d.nativeElement as HTMLInputElement);
  const checkbox = () => fixture.nativeElement.querySelector("mat-checkbox input") as HTMLInputElement;
  const errorTexts = () =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map((e) => (e as HTMLElement).textContent?.trim());

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    await flush();
  });

  it("should create", () => {
    expect(fixture.debugElement.query(By.directive(ContainerRegistrationConfigComponent))).toBeTruthy();
  });

  describe("user store checkbox", () => {
    it("is disabled when the container has no owner", async () => {
      host.hasOwner.set(false);
      await flush();
      expect(fixture.debugElement.query(By.directive(MatCheckbox)).componentInstance.disabled).toBe(true);
      expect(host.registrationForm.store().disabled()).toBe(true);
    });

    it("is enabled when the container has an owner", () => {
      expect(fixture.debugElement.query(By.directive(MatCheckbox)).componentInstance.disabled).toBe(false);
    });

    it("clears the response and repeat and sets the default prompt when it is checked", async () => {
      await set({ response: "secret", repeat: "secret" });
      checkbox().click();
      await flush();
      expect(host.model()).toEqual({
        prompt: DEFAULT_PASSPHRASE_PROMPT,
        response: "",
        repeat: "",
        store: true
      });
      expect(host.registrationForm.store().dirty()).toBe(true);
    });

    it("keeps a prompt that is already set when it is checked", async () => {
      await set({ prompt: "Custom prompt" });
      checkbox().click();
      await flush();
      expect(host.model().prompt).toBe("Custom prompt");
      expect(host.model().store).toBe(true);
    });

    it("keeps the entered values when it is unchecked", async () => {
      await set({ prompt: "Prompt", response: "Response", repeat: "Response", store: true });
      checkbox().click();
      await flush();
      expect(host.model()).toEqual({ prompt: "Prompt", response: "Response", repeat: "Response", store: false });
    });

    it("disables the response, the repeat and their visibility buttons", async () => {
      await set({ store: true });
      expect(inputs().map((i) => i.disabled)).toEqual([true, true]);
      expect(textarea().disabled).toBe(false);
      const buttons = Array.from(fixture.nativeElement.querySelectorAll("button")) as HTMLButtonElement[];
      expect(buttons.map((b) => b.disabled)).toEqual([true, true]);
    });

    it("enables the response and the repeat when it is unchecked", () => {
      expect(inputs().map((i) => i.disabled)).toEqual([false, false]);
    });
  });

  describe("input", () => {
    it("writes typed text to the model and marks the fields dirty", async () => {
      textarea().value = "Enter passphrase";
      textarea().dispatchEvent(new Event("input"));
      inputs()[0].value = "foo";
      inputs()[0].dispatchEvent(new Event("input"));
      inputs()[1].value = "bar";
      inputs()[1].dispatchEvent(new Event("input"));
      await flush();
      expect(host.model()).toEqual({ prompt: "Enter passphrase", response: "foo", repeat: "bar", store: false });
      expect(host.registrationForm.response().dirty()).toBe(true);
    });

    it("toggles the visibility of the response", async () => {
      const [toggle] = Array.from(fixture.nativeElement.querySelectorAll("button")) as HTMLButtonElement[];
      expect(inputs()[0].type).toBe("password");
      toggle.click();
      await flush();
      expect(inputs()[0].type).toBe("text");
      expect(inputs()[1].type).toBe("password");
    });

    it("toggles the visibility of the repeat", async () => {
      const toggle = (Array.from(fixture.nativeElement.querySelectorAll("button")) as HTMLButtonElement[])[1];
      expect(inputs()[1].type).toBe("password");
      toggle.click();
      await flush();
      expect(inputs()[1].type).toBe("text");
      expect(inputs()[0].type).toBe("password");
    });
  });

  describe("validation", () => {
    it("is valid when nothing is set", () => {
      expect(host.registrationForm().valid()).toBe(true);
    });

    it("is valid when the user store is used", async () => {
      await set({ store: true, prompt: DEFAULT_PASSPHRASE_PROMPT });
      expect(host.registrationForm().valid()).toBe(true);
    });

    it("is valid for a prompt with matching responses", async () => {
      await set({ prompt: "Enter passphrase", response: "foo", repeat: "foo" });
      expect(host.registrationForm().valid()).toBe(true);
    });

    it("requires a response for a prompt", async () => {
      await set({ prompt: "Enter passphrase" });
      expect(kinds(host.registrationForm.response())).toEqual(["required"]);
      expect(host.registrationForm().valid()).toBe(false);
    });

    it("rejects a response without a repeat and a repeat without a response", async () => {
      await set({ prompt: "Enter passphrase", response: "secret" });
      expect(kinds(host.registrationForm.repeat())).toEqual([PASSPHRASE_MISMATCH]);
      expect(host.registrationForm().valid()).toBe(false);
      await set({ response: "", repeat: "secret" });
      expect(kinds(host.registrationForm.response())).toEqual(["required"]);
      expect(kinds(host.registrationForm.repeat())).toEqual([PASSPHRASE_MISMATCH]);
      expect(host.registrationForm().valid()).toBe(false);
    });

    it("rejects responses that differ", async () => {
      await set({ prompt: "Enter passphrase", response: "foo", repeat: "bar" });
      expect(kinds(host.registrationForm.repeat())).toEqual([PASSPHRASE_MISMATCH]);
      expect(host.registrationForm().valid()).toBe(false);
    });

    it("requires a prompt for a response", async () => {
      await set({ response: "foo", repeat: "foo" });
      expect(kinds(host.registrationForm.prompt())).toEqual(["required"]);
      expect(host.registrationForm().valid()).toBe(false);
    });

    it("requires a prompt for a repeat", async () => {
      await set({ repeat: "foo" });
      expect(kinds(host.registrationForm.prompt())).toEqual(["required"]);
      expect(host.registrationForm().valid()).toBe(false);
    });

    it("applies no rule while inactive", async () => {
      host.active.set(false);
      await set({ response: "foo", repeat: "bar" });
      expect(host.registrationForm().valid()).toBe(true);
    });

    it("shows the errors of the touched fields", async () => {
      await set({ prompt: "Enter passphrase", response: "foo", repeat: "bar" });
      expect(errorTexts()).toEqual([]);
      await touchAll(host.registrationForm);
      await flush();
      expect(errorTexts()).toEqual(["Passphrases do not match."]);
      await set({ response: "", repeat: "" });
      await touchAll(host.registrationForm);
      await flush();
      expect(errorTexts()).toEqual(["Passphrase response is required."]);
      await set({ prompt: "", response: "foo", repeat: "foo" });
      await touchAll(host.registrationForm);
      await flush();
      expect(errorTexts()).toEqual(["Passphrase prompt is required."]);
    });
  });
});
