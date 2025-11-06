import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PoliciesComponent } from "./policies.component";
import { PolicyService } from "../../services/policies/policies.service";
import { signal } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { PolicyPanelComponent } from "./policy-panels/policy-panel/policy-panel.component";

describe("PoliciesComponent", () => {
  let component: PoliciesComponent;
  let fixture: ComponentFixture<PoliciesComponent>;
  let policyServiceMock: any;

  beforeEach(async () => {
    policyServiceMock = {
      allPolicies: signal([]),
      isEditMode: signal(false),
      selectedPolicy: signal(null),
      selectedPolicyHasConditions: signal(false),
      selectedPolicyOriginal: signal(null),
      isPolicyEdited: () => false,
      canSaveSelectedPolicy: () => false,
      updateSelectedPolicy: jasmine.createSpy("updateSelectedPolicy"),
      selectPolicyByName: jasmine.createSpy("selectPolicyByName"),
      deselectPolicy: jasmine.createSpy("deselectPolicy"),
      initializeNewPolicy: jasmine.createSpy("initializeNewPolicy"),
      deselectNewPolicy: jasmine.createSpy("deselectNewPolicy"),
      enablePolicy: jasmine.createSpy("enablePolicy"),
      disablePolicy: jasmine.createSpy("disablePolicy"),
      savePolicyEdits: jasmine.createSpy("savePolicyEdits"),
      deletePolicy: jasmine.createSpy("deletePolicy"),
      cancelEditMode: jasmine.createSpy("cancelEditMode"),
      allPoliciesRecource: {
        reload: jasmine.createSpy("reload")
      }
    };

    await TestBed.configureTestingModule({
      imports: [PoliciesComponent, NoopAnimationsModule, PolicyPanelComponent],
      providers: [{ provide: PolicyService, useValue: policyServiceMock }]
    }).compileComponents();

    fixture = TestBed.createComponent(PoliciesComponent);
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display a list of policies", () => {
    const policies = [
      { name: "policy1", scope: "test" },
      { name: "policy2", scope: "test" }
    ];
    policyServiceMock.allPolicies.set(policies);
    fixture.detectChanges();

    const policyElements = fixture.nativeElement.querySelectorAll("app-policy-panel");
    expect(policyElements.length).toBe(policies.length);
  });

  it("should display a new policy panel", () => {
    fixture.detectChanges();
    const newPolicyPanel = fixture.nativeElement.querySelector('app-policy-panel[isNew="true"]');
    expect(newPolicyPanel).toBeTruthy();
  });
});
