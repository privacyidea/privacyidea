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
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { provideRouter } from "@angular/router";
import { EmailConfigComponent } from "@components/configuration/token-type-config/token-types/email-config/email-config.component";
import { EMAIL_SMTP_SERVER_KEY, EMAIL_VALIDITY_TIME_KEY } from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";

const mockSmtpServers = ["server1", "server2", "server3"];

describe("EmailConfigComponent", () => {
  let fixture: ComponentFixture<EmailConfigComponent>;
  let component: EmailConfigComponent;
  let configForm: ReturnType<typeof createTokenTypeConfigForm>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const textInput = () =>
    fixture.nativeElement
      .querySelector("mat-hint.red")!
      .closest("mat-form-field")!
      .querySelector("input") as HTMLInputElement;
  const numberInput = () => fixture.nativeElement.querySelector("input[type=number]") as HTMLInputElement;
  const typeNumber = async (value: string) => {
    numberInput().value = value;
    numberInput().dispatchEvent(new Event("input"));
    await flush();
  };

  const create = async (config: Record<string, string> = {}, listable = true) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(EmailConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    fixture.componentRef.setInput("smtpServers", mockSmtpServers);
    fixture.componentRef.setInput("smtpServersListable", listable);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmailConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
  });

  afterEach(() => {
    document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
  });

  it("should create", async () => {
    await create();
    expect(component).toBeTruthy();
  });

  describe("when the entries can be listed", () => {
    it("should offer them in a select", async () => {
      await create();
      const element: HTMLElement = fixture.nativeElement;
      expect(element.querySelector("mat-select")).not.toBeNull();
      expect(element.querySelector("mat-hint")?.textContent).toContain("Select a predefined");
      expect(element.textContent).not.toContain("smtpserver_read");
    });

    it("writes the picked entry to the form", async () => {
      await create();
      const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
      select.open();
      await flush();

      (document.querySelectorAll("mat-option")[1] as HTMLElement).click();
      await flush();

      expect(configForm.model().values[EMAIL_SMTP_SERVER_KEY]).toBe("server2");
      expect(configForm.form.values[EMAIL_SMTP_SERVER_KEY]().dirty()).toBe(true);
    });

    it("shows the entry of the form", async () => {
      await create({ [EMAIL_SMTP_SERVER_KEY]: "server2" });
      expect((fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect).value).toBe(
        "server2"
      );
    });

    it("clears the entry through the form and marks the field dirty", async () => {
      await create({ [EMAIL_SMTP_SERVER_KEY]: "server1" });

      fixture.debugElement.query(By.css("app-clear-button button")).nativeElement.click();
      await flush();

      expect(configForm.model().values[EMAIL_SMTP_SERVER_KEY]).toBe("");
      expect(configForm.form.values[EMAIL_SMTP_SERVER_KEY]().dirty()).toBe(true);
    });
  });

  describe("when the entries cannot be listed", () => {
    beforeEach(async () => {
      await create({ [EMAIL_SMTP_SERVER_KEY]: "server1" }, false);
    });

    it("should replace the select by a text input naming the missing right", () => {
      const element: HTMLElement = fixture.nativeElement;
      expect(element.querySelector("mat-select")).toBeNull();
      expect(element.querySelector("mat-hint")?.textContent).toContain("smtpserver_read");
    });

    it("should show the configured value and write the typed one to the form", async () => {
      expect(textInput().value).toBe("server1");

      textInput().value = "server9";
      textInput().dispatchEvent(new Event("input"));
      await flush();

      expect(configForm.model().values[EMAIL_SMTP_SERVER_KEY]).toBe("server9");
    });

    it("clears the typed value through the clear button", async () => {
      fixture.debugElement.query(By.css("app-clear-button button")).nativeElement.click();
      await flush();

      expect(textInput().value).toBe("");
      expect(configForm.model().values[EMAIL_SMTP_SERVER_KEY]).toBe("");
    });
  });

  describe("Email validity time input", () => {
    it("shows the value of the form", async () => {
      await create({ [EMAIL_VALIDITY_TIME_KEY]: "450" });
      expect(numberInput().value).toBe("450");
    });

    it("writes the typed number as a string", async () => {
      await create();

      await typeNumber("450");

      expect(configForm.model().values[EMAIL_VALIDITY_TIME_KEY]).toBe("450");
      expect(configForm.form.values[EMAIL_VALIDITY_TIME_KEY]().dirty()).toBe(true);
    });

    it("writes an empty string, not NaN, when the input is cleared", async () => {
      await create({ [EMAIL_VALIDITY_TIME_KEY]: "450" });

      await typeNumber("");

      expect(configForm.model().values[EMAIL_VALIDITY_TIME_KEY]).toBe("");
    });

    it("shows a message for text the number input cannot parse", async () => {
      await create({ [EMAIL_VALIDITY_TIME_KEY]: "450" });
      Object.defineProperty(numberInput(), "validity", { value: { badInput: true } });

      await typeNumber("");
      configForm.form.values[EMAIL_VALIDITY_TIME_KEY]().markAsTouched();
      await flush();

      expect(
        configForm.form.values[EMAIL_VALIDITY_TIME_KEY]()
          .errors()
          .map((error) => error.kind)
      ).toEqual(["parse"]);
      expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("Enter a valid number.");
      expect(configForm.form().valid()).toBe(false);
      expect(fixture.nativeElement.querySelector(".panel-incomplete")?.textContent).toContain("Incomplete");
    });
  });

  it("should handle the entry list input", async () => {
    await create();
    expect(component.smtpServers()).toEqual(mockSmtpServers);
    fixture.componentRef.setInput("smtpServers", []);
    fixture.detectChanges();
    expect(component.smtpServers()).toEqual([]);
  });

  it("should handle expanded input", async () => {
    await create();
    fixture.componentRef.setInput("expanded", true);
    fixture.detectChanges();
    expect(component.expanded()).toBe(true);

    fixture.componentRef.setInput("expanded", false);
    fixture.detectChanges();
    expect(component.expanded()).toBe(false);
  });
});
