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
import { provideRouter } from "@angular/router";
import { EmailConfigComponent } from "@components/configuration/token-type-config/token-types/email-config/email-config.component";
import { EMAIL_SMTP_SERVER_KEY } from "@constants/token.constants";

const mockSmtpServers = ["server1", "server2", "server3"];

describe("EmailConfigComponent", () => {
  let fixture: ComponentFixture<EmailConfigComponent>;
  let component: EmailConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmailConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
    fixture = TestBed.createComponent(EmailConfigComponent);
    fixture.componentRef.setInput("formData", {});
    fixture.componentRef.setInput("smtpServers", mockSmtpServers);
    fixture.componentRef.setInput("smtpServersListable", true);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should offer the configured SMTP servers in a select when they can be listed", () => {
    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector("mat-select")).not.toBeNull();
    expect(element.querySelector("mat-hint")?.textContent).toContain("Select a predefined");
    expect(element.textContent).not.toContain("smtpserver_read");
  });

  describe("when the SMTP servers cannot be listed", () => {
    beforeEach(() => {
      fixture.componentRef.setInput("smtpServersListable", false);
      fixture.componentRef.setInput("formData", { [EMAIL_SMTP_SERVER_KEY]: "server1" });
      fixture.detectChanges();
    });

    it("should replace the select by a text input naming the missing right", () => {
      const element: HTMLElement = fixture.nativeElement;
      expect(element.querySelector("mat-select")).toBeNull();
      expect(element.querySelector("mat-hint")?.textContent).toContain("smtpserver_read");
    });

    it("should show the configured value and emit the typed one", () => {
      const hint: HTMLElement = fixture.nativeElement.querySelector("mat-hint.red");
      const input = hint.closest("mat-form-field")!.querySelector("input") as HTMLInputElement;
      expect(input.value).toBe("server1");

      jest.spyOn(component.formDataChange, "emit");
      input.value = "server9";
      input.dispatchEvent(new Event("input"));
      expect(component.formDataChange.emit).toHaveBeenCalledWith({ [EMAIL_SMTP_SERVER_KEY]: "server9" });
    });
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "server1";
    component.updateFormData(EMAIL_SMTP_SERVER_KEY, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [EMAIL_SMTP_SERVER_KEY]: newValue });
  });
});
