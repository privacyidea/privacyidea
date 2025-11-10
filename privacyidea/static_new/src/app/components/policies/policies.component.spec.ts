import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PoliciesComponent } from "./policies.component";
import { PolicyDetail, PolicyService } from "../../services/policies/policies.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { PolicyPanelComponent } from "./policy-panels/policy-panel/policy-panel.component";
import { MockPolicyService } from "../../../testing/mock-services/mock-policies-service";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import "@angular/localize/init";

describe("PoliciesComponent", () => {
  let component: PoliciesComponent;
  let fixture: ComponentFixture<PoliciesComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PoliciesComponent, NoopAnimationsModule, PolicyPanelComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PolicyService, useClass: MockPolicyService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PoliciesComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display a list of policies", () => {
    const policies: PolicyDetail[] = [
      { ...policyServiceMock.emptyPolicy, name: "policy1", scope: "test" },
      { ...policyServiceMock.emptyPolicy, name: "policy2", scope: "test" }
    ];
    policyServiceMock.allPolicies.set(policies);
    fixture.detectChanges();

    const policyElements = fixture.nativeElement.querySelectorAll(".policy-card");
    expect(policyElements.length).toBe(policies.length + 1); // +1 for the "new policy" panel
    expect(policyElements[1].textContent).toContain("policy1");
    expect(policyElements[2].textContent).toContain("policy2");
  });

  it("should display a new policy panel", () => {
    fixture.detectChanges();
    const newPolicyPanel = fixture.nativeElement.querySelector(".policy-card");
    expect(newPolicyPanel).toBeTruthy();
    expect(newPolicyPanel.textContent).toContain("New Policy");
  });
});
