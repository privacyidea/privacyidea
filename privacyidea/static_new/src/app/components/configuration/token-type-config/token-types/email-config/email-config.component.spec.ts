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
import { EmailConfigComponent } from "@components/configuration/token-type-config/token-types/email-config/email-config.component";
import { provideRouter } from "@angular/router";
import { EMAIL_SMTP_SERVER_KEY } from "../../../../../constants/token.constants";
import { provideAnimations } from "@angular/platform-browser/animations";

const mockSmtpServers = ["server1", "server2", "server3"];

describe("EmailConfigComponent", () => {
  let fixture: ComponentFixture<EmailConfigComponent>;
  let component: EmailConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmailConfigComponent],
      providers: [provideRouter([]), provideAnimations()]
    }).compileComponents();
    fixture = TestBed.createComponent(EmailConfigComponent);
    fixture.componentRef.setInput("formData", {});
    fixture.componentRef.setInput("smtpServers", mockSmtpServers);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "server1";
    component.updateFormData(EMAIL_SMTP_SERVER_KEY, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [EMAIL_SMTP_SERVER_KEY]: newValue });
  });

  it("should call updateFormData with empty value when clearField is called", async () => {
    const initialServer = "server1";
    fixture.componentRef.setInput("formData", { [EMAIL_SMTP_SERVER_KEY]: initialServer });
    fixture.detectChanges();
    expect(component.formData()[EMAIL_SMTP_SERVER_KEY]).toEqual(initialServer);

    jest.spyOn(component, "updateFormData");
    component.clearField(EMAIL_SMTP_SERVER_KEY);
    expect(component.updateFormData).toHaveBeenCalledWith(EMAIL_SMTP_SERVER_KEY, "");
  });
});
