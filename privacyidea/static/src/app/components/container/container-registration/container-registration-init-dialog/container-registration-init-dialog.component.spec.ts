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
import { NO_ERRORS_SCHEMA } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { By } from "@angular/platform-browser";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { ContainerRegistrationInitDialogComponent } from "./container-registration-init-dialog.component";

describe("ContainerRegistrationInitDialogComponent", () => {
  let component: ContainerRegistrationInitDialogComponent;
  let fixture: ComponentFixture<ContainerRegistrationInitDialogComponent>;
  let mockRegisterContainer: jest.Mock;

  describe("Registration", () => {
    const mockData = {
      rollover: false,
      containerHasOwner: true,
      registerContainer: jest.fn()
    };

    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [ContainerRegistrationInitDialogComponent],
        providers: [
          { provide: MAT_DIALOG_DATA, useValue: mockData },
          { provide: MatDialogRef, useClass: MockMatDialogRef }
        ],
        schemas: [NO_ERRORS_SCHEMA]
      }).compileComponents();

      fixture = TestBed.createComponent(ContainerRegistrationInitDialogComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();
      mockRegisterContainer = mockData.registerContainer;
    });

    it("should create", () => {
      expect(component).toBeDefined();
    });

    it("should render Register button", () => {
      const button = fixture.debugElement.query(By.css(".pi-dialog-footer .action-button-primary"))
        ?.nativeElement as HTMLButtonElement;
      expect(button).toBeDefined();
      expect(button.textContent).toContain("Register");
    });

    it("should call registerContainer with correct arguments when onRegister is called", () => {
      component.registration.set({ prompt: "prompt", response: "response", repeat: "response", store: false });

      component.onRegister();
      expect(mockRegisterContainer).toHaveBeenCalledWith(false, "prompt", "response", component.data.rollover);
    });

    it("should pass the user store flag on", () => {
      component.registration.set({ prompt: "prompt", response: "", repeat: "", store: true });

      component.onRegister();
      expect(mockRegisterContainer).toHaveBeenCalledWith(true, "prompt", "", component.data.rollover);
    });

    it("should enable Register button for an empty registration", () => {
      expect(component.getAction().disabled).toBe(false);
    });

    it("should disable Register button when the passphrases do not match", () => {
      component.registration.set({ prompt: "prompt", response: "foo", repeat: "bar", store: false });
      fixture.detectChanges();
      expect(component.getAction().disabled).toBe(true);
    });

    it("should not register and should touch the fields when the registration is invalid", () => {
      component.registration.set({ prompt: "prompt", response: "foo", repeat: "bar", store: false });

      component.onRegister();

      expect(mockRegisterContainer).not.toHaveBeenCalled();
      expect(component.form.repeat().touched()).toBe(true);
    });

    it("should allow the user store passphrase for a container with an owner", () => {
      expect(component.form.store().disabled()).toBe(false);
    });
  });

  describe("Container without owner", () => {
    it("should not allow the user store passphrase", async () => {
      await TestBed.configureTestingModule({
        imports: [ContainerRegistrationInitDialogComponent],
        providers: [
          {
            provide: MAT_DIALOG_DATA,
            useValue: { rollover: false, containerHasOwner: false, registerContainer: jest.fn() }
          },
          { provide: MatDialogRef, useClass: MockMatDialogRef }
        ],
        schemas: [NO_ERRORS_SCHEMA]
      }).compileComponents();
      fixture = TestBed.createComponent(ContainerRegistrationInitDialogComponent);
      fixture.detectChanges();

      expect(fixture.componentInstance.form.store().disabled()).toBe(true);
    });
  });

  describe("Rollover", () => {
    const mockData = {
      rollover: true,
      containerHasOwner: true,
      registerContainer: jest.fn()
    };

    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [ContainerRegistrationInitDialogComponent],
        providers: [
          { provide: MAT_DIALOG_DATA, useValue: mockData },
          { provide: MatDialogRef, useClass: MockMatDialogRef }
        ],
        schemas: [NO_ERRORS_SCHEMA]
      }).compileComponents();

      fixture = TestBed.createComponent(ContainerRegistrationInitDialogComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();
      mockRegisterContainer = mockData.registerContainer;
    });

    it("should create", () => {
      expect(component).toBeDefined();
    });

    it("should render 'Container Rollover' title", async () => {
      const title = fixture.nativeElement.querySelector("h3");
      expect(title.textContent).toContain("Container Rollover");
    });

    it("should render Rollover button", async () => {
      const button = fixture.debugElement.query(By.css(".pi-dialog-footer .action-button-primary"))
        ?.nativeElement as HTMLButtonElement;
      expect(button).toBeDefined();
      expect(button.textContent).toContain("Rollover");
    });

    it("should call registerContainer with correct arguments when onRegister is called", () => {
      component.registration.set({ prompt: "prompt", response: "response", repeat: "response", store: false });

      component.onRegister();
      expect(mockRegisterContainer).toHaveBeenCalledWith(false, "prompt", "response", true);
    });

    it("should disable Rollover button when the registration is invalid", () => {
      component.registration.set({ prompt: "prompt", response: "", repeat: "", store: false });
      fixture.detectChanges();
      expect(component.getAction().disabled).toBe(true);
    });
  });
});
