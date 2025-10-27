import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerRegistrationInitDialogComponent } from "./container-registration-init-dialog.component";
import { MAT_DIALOG_DATA } from "@angular/material/dialog";
import { By } from "@angular/platform-browser";
import { NO_ERRORS_SCHEMA, signal } from "@angular/core";

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
          { provide: MAT_DIALOG_DATA, useValue: mockData }
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
      const button = fixture.debugElement.query(By.css("button[mat-button]:not([mat-dialog-close])"));
      expect(button.nativeElement.textContent).toContain("Register");
    });

    it("should call registerContainer with correct arguments when onRegister is called", () => {
      // Mock the child component and its properties
      component.registrationConfigComponent = {
        userStorePassphrase: signal(true),
        passphrasePrompt: signal("prompt"),
        passphraseResponse: signal("response")
      } as any;

      component.onRegister();
      expect(mockRegisterContainer).toHaveBeenCalledWith(
        true,
        "prompt",
        "response",
        component.data.rollover
      );
    });

    it("should disable Register button when validInput is false", () => {
      // Simulate invalid input by mocking the getter
      Object.defineProperty(component, "validInput", { get: () => false });
      fixture.detectChanges();
      const button = fixture.debugElement.query(By.css("button[mat-button]:not([mat-dialog-close])"));
      expect(button.nativeElement.disabled).toBe(true);
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
          { provide: MAT_DIALOG_DATA, useValue: mockData }
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
      const title = fixture.nativeElement.querySelector("h2");
      expect(title.textContent).toContain("Container Rollover");
    });

    it("should render Rollover button", async () => {
      const button = fixture.debugElement.query(By.css("button[mat-button]:not([mat-dialog-close])"));
      expect(button.nativeElement.textContent).toContain("Rollover");
    });

    it("should call registerContainer with correct arguments when onRegister is called", () => {
      // Mock the child component and its properties
      component.registrationConfigComponent = {
        userStorePassphrase: signal(true),
        passphrasePrompt: signal("prompt"),
        passphraseResponse: signal("response")
      } as any;

      component.onRegister();
      expect(mockRegisterContainer).toHaveBeenCalledWith(
        true,
        "prompt",
        "response",
        true
      );
    });

    it("should disable Rollover button when validInput is false", () => {
      // Simulate invalid input by mocking the getter
      Object.defineProperty(component, "validInput", { get: () => false });
      fixture.detectChanges();
      const button = fixture.debugElement.query(By.css("button[mat-button]:not([mat-dialog-close])"));
      expect(button.nativeElement.disabled).toBe(true);
    });
  });
});
