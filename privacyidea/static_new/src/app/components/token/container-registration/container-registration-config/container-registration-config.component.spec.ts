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
    component.passphrasePrompt = "";
    component.passphraseResponse = "secret";
    component.userStorePassphrase = true;
    component.onUserStorePassphraseChange();
    expect(component.passphraseResponse).toBe("");
    expect(component.passphrasePrompt).toBe(component.defaultPrompt);
  });

  it("should not overwrite passphrasePrompt if already set when userStorePassphrase is checked", () => {
    component.passphrasePrompt = "Custom prompt";
    component.userStorePassphrase = true;
    component.onUserStorePassphraseChange();
    expect(component.passphrasePrompt).toBe("Custom prompt");
  });

  it("should not change passphraseResponse or prompt when userStorePassphrase is unchecked", () => {
    component.passphrasePrompt = "Prompt";
    component.passphraseResponse = "Response";
    component.userStorePassphrase = false;
    component.onUserStorePassphraseChange();
    expect(component.passphrasePrompt).toBe("Prompt");
    expect(component.passphraseResponse).toBe("Response");
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
    component.userStorePassphrase = true;
    await detectChangesStable(fixture);
    const textareas = fixture.nativeElement.querySelectorAll("textarea");
    const promptInput = textareas[0];
    const responseInput = textareas[1];
    expect(promptInput.disabled).toBe(false);
    expect(responseInput.disabled).toBe(true);
  });

  it("should enable passphraseResponse textarea when userStorePassphrase is false", async () => {
    component.userStorePassphrase = false;
    await detectChangesStable(fixture);
    const textarea = fixture.nativeElement.querySelectorAll("textarea")[1];
    expect(textarea.disabled).toBe(false);
  });
});
