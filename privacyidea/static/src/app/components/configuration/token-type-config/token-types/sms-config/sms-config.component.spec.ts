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
import { SmsConfigComponent } from "@components/configuration/token-type-config/token-types/sms-config/sms-config.component";
import { SMS_GATEWAY, SMS_PROVIDER_TIMEOUT } from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";

const mockSmsGateways = ["gateway1", "gateway2", "gateway3"];

describe("SmsConfigComponent", () => {
  let fixture: ComponentFixture<SmsConfigComponent>;
  let component: SmsConfigComponent;
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
    fixture = TestBed.createComponent(SmsConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    fixture.componentRef.setInput("smsGateways", mockSmsGateways);
    fixture.componentRef.setInput("smsGatewaysListable", listable);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SmsConfigComponent],
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
      expect(element.textContent).not.toContain("smsgateway_read");
    });

    it("writes the picked entry to the form", async () => {
      await create();
      const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
      select.open();
      await flush();

      (document.querySelectorAll("mat-option")[1] as HTMLElement).click();
      await flush();

      expect(configForm.model().values[SMS_GATEWAY]).toBe("gateway2");
      expect(configForm.form.values[SMS_GATEWAY]().dirty()).toBe(true);
    });

    it("shows the entry of the form", async () => {
      await create({ [SMS_GATEWAY]: "gateway2" });
      expect((fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect).value).toBe(
        "gateway2"
      );
    });

    it("clears the entry through the form and marks the field dirty", async () => {
      await create({ [SMS_GATEWAY]: "gateway1" });

      fixture.debugElement.query(By.css("app-clear-button button")).nativeElement.click();
      await flush();

      expect(configForm.model().values[SMS_GATEWAY]).toBe("");
      expect(configForm.form.values[SMS_GATEWAY]().dirty()).toBe(true);
    });
  });

  describe("when the entries cannot be listed", () => {
    beforeEach(async () => {
      await create({ [SMS_GATEWAY]: "gateway1" }, false);
    });

    it("should replace the select by a text input naming the missing right", () => {
      const element: HTMLElement = fixture.nativeElement;
      expect(element.querySelector("mat-select")).toBeNull();
      expect(element.querySelector("mat-hint")?.textContent).toContain("smsgateway_read");
    });

    it("should show the configured value and write the typed one to the form", async () => {
      expect(textInput().value).toBe("gateway1");

      textInput().value = "gateway9";
      textInput().dispatchEvent(new Event("input"));
      await flush();

      expect(configForm.model().values[SMS_GATEWAY]).toBe("gateway9");
    });

    it("clears the typed value through the clear button", async () => {
      fixture.debugElement.query(By.css("app-clear-button button")).nativeElement.click();
      await flush();

      expect(textInput().value).toBe("");
      expect(configForm.model().values[SMS_GATEWAY]).toBe("");
    });
  });

  describe("SMS validity time input", () => {
    it("shows the value of the form", async () => {
      await create({ [SMS_PROVIDER_TIMEOUT]: "450" });
      expect(numberInput().value).toBe("450");
    });

    it("writes the typed number as a string", async () => {
      await create();

      await typeNumber("450");

      expect(configForm.model().values[SMS_PROVIDER_TIMEOUT]).toBe("450");
      expect(configForm.form.values[SMS_PROVIDER_TIMEOUT]().dirty()).toBe(true);
    });

    it("writes an empty string, not NaN, when the input is cleared", async () => {
      await create({ [SMS_PROVIDER_TIMEOUT]: "450" });

      await typeNumber("");

      expect(configForm.model().values[SMS_PROVIDER_TIMEOUT]).toBe("");
    });

    it("shows a message for text the number input cannot parse", async () => {
      await create({ [SMS_PROVIDER_TIMEOUT]: "450" });
      Object.defineProperty(numberInput(), "validity", { value: { badInput: true } });

      await typeNumber("");
      configForm.form.values[SMS_PROVIDER_TIMEOUT]().markAsTouched();
      await flush();

      expect(
        configForm.form.values[SMS_PROVIDER_TIMEOUT]()
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
    expect(component.smsGateways()).toEqual(mockSmsGateways);
    fixture.componentRef.setInput("smsGateways", []);
    fixture.detectChanges();
    expect(component.smsGateways()).toEqual([]);
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
