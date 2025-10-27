import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerRegistrationConfigComponent } from "./container-registration-config.component";
import { FormsModule } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatFormField } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { By } from "@angular/platform-browser";

const detectChangesStable = async (fixture: ComponentFixture<any>) => {
  fixture.detectChanges();
  await Promise.resolve();
  fixture.detectChanges();
};

describe("ContainerRegistrationConfigComponent", () => {
  let component: ContainerRegistrationConfigComponent;
  let fixture: ComponentFixture<ContainerRegistrationConfigComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FormsModule, MatCheckbox, MatFormField, MatInput]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerRegistrationConfigComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should clear passphraseResponse and set default prompt when userStorePassphrase is checked", () => {
    component.passphrasePrompt.set("");
    component.passphraseResponse.set("secret");
    component.userStorePassphrase.set(true);
    component.onUserStorePassphraseChange();
    expect(component.passphraseResponse()).toBe("");
    expect(component.passphrasePrompt()).toBe(component.defaultPrompt);
  });

  it("should not overwrite passphrasePrompt if already set when userStorePassphrase is checked", () => {
    component.passphrasePrompt.set("Custom prompt");
    component.userStorePassphrase.set(true);
    component.onUserStorePassphraseChange();
    expect(component.passphrasePrompt()).toBe("Custom prompt");
  });

  it("should not change passphraseResponse or prompt when userStorePassphrase is unchecked", () => {
    component.passphrasePrompt.set("Prompt");
    component.passphraseResponse.set("Response");
    component.userStorePassphrase.set(false);
    component.onUserStorePassphraseChange();
    expect(component.passphrasePrompt()).toBe("Prompt");
    expect(component.passphraseResponse()).toBe("Response");
  });

  it("should disable checkbox if containerHasOwner is false", async () => {
    component.containerHasOwner = false;
    await detectChangesStable(fixture);
    const checkboxDebug = fixture.debugElement.query(By.directive(MatCheckbox));
    expect(checkboxDebug.componentInstance.disabled).toBe(true);
  });

  it("should enable checkbox if containerHasOwner is true", async () => {
    component.containerHasOwner = true;
    await detectChangesStable(fixture);
    const checkboxDebug = fixture.debugElement.query(By.directive(MatCheckbox));
    expect(checkboxDebug.componentInstance.disabled).toBe(false);
  });

  it("should disable passphraseResponse textarea when userStorePassphrase is true", async () => {
    component.userStorePassphrase.set(true);
    await detectChangesStable(fixture);
    const inputs = fixture.nativeElement.querySelectorAll("input");
    const responseInput = inputs[0];
    const repeatResponseInput = inputs[1];
    expect(responseInput.disabled).toBe(true);
    expect(repeatResponseInput.disabled).toBe(true);
    const promptInput = fixture.nativeElement.querySelector("textarea");
    expect(promptInput.disabled).toBe(false);
  });

  it("should enable passphraseResponse textarea when userStorePassphrase is false", async () => {
    component.userStorePassphrase.set(false);
    await detectChangesStable(fixture);
    const inputs = fixture.debugElement.queryAll(By.css('input[matinput]'));
    const responseInput: HTMLInputElement = inputs[0].nativeElement;
    const repeatResponseInput: HTMLInputElement = inputs[1].nativeElement;
    expect(responseInput.disabled).toBe(false);
    expect(repeatResponseInput.disabled).toBe(false);
  });

  describe("input validation", () => {
    beforeEach(() => {
      // Reset signals for each test
      component.userStorePassphrase.set(false);
      component.passphrasePrompt.set("");
      component.passphraseResponse.set("");
      component.repeatPassphraseResponse.set("");
    });

    it("passphraseMismatch is false if both are empty", () => {
      component.passphraseResponse.set("");
      component.repeatPassphraseResponse.set("");
      expect(component.passphraseMismatch).toBe(false);
    });

    it("passphraseMismatch is false if passphrases match", () => {
      component.passphraseResponse.set("foo");
      component.repeatPassphraseResponse.set("foo");
      expect(component.passphraseMismatch).toBe(false);
    });

    it("passphraseMismatch is true if passphrases do not match and both are non-empty", () => {
      component.userStorePassphrase.set(false);
      component.passphrasePrompt.set("Enter passphrase");
      component.passphraseResponse.set("foo");
      component.repeatPassphraseResponse.set("bar");
      expect(component.passphraseMismatch).toBe(true);
    });

    it("validInput is true if userStorePassphrase is true", () => {
      component.userStorePassphrase.set(true);
      expect(component.validInput()).toBe(true);
    });

    it("validInput is false if passphrasePrompt is set but passphraseResponse is empty", () => {
      component.passphrasePrompt.set("Enter passphrase");
      component.passphraseResponse.set("");
      component.repeatPassphraseResponse.set("");
      expect(component.validInput()).toBe(false);

      component.passphraseResponse.set("secret");
      component.repeatPassphraseResponse.set("");
      expect(component.validInput()).toBe(false);

      component.passphraseResponse.set("");
      component.repeatPassphraseResponse.set("secret");
      expect(component.validInput()).toBe(false);
    });

    it("validInput is false if passphraseResponses do match, but passphrasePrompt is empty", () => {
      component.passphrasePrompt.set("");
      component.passphraseResponse.set("foo");
      component.repeatPassphraseResponse.set("foo");
      expect(component.validInput()).toBe(false);
    });

    it("validInput is false if passphrases do not match", () => {
      component.passphrasePrompt.set("Enter passphrase");
      component.passphraseResponse.set("foo");
      component.repeatPassphraseResponse.set("bar");
      expect(component.validInput()).toBe(false);
    });

    it("validInput is true if passphrases are non-empty and match", () => {
      component.passphraseResponse.set("foo");
      component.repeatPassphraseResponse.set("foo");
      expect(component.validInput()).toBe(true);
    });

    it("validInput is true if  no passphrase parameter is set", () => {
      component.passphrasePrompt.set("");
      component.passphraseResponse.set("");
      component.repeatPassphraseResponse.set("");
      expect(component.validInput()).toBe(true);
    });
  });
});
