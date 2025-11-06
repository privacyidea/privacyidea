import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PolicyPanelComponent } from "./policy-panel.component";
import { PolicyService } from "../../../../services/policies/policies.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatExpansionModule } from "@angular/material/expansion";
import { MockPolicyService } from "../../../../../testing/mock-services/mock-policies-service";

import "@angular/localize/init";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("PolicyPanelComponent", () => {
  let component: PolicyPanelComponent;
  let fixture: ComponentFixture<PolicyPanelComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyPanelComponent, NoopAnimationsModule, MatExpansionModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PolicyService, useClass: MockPolicyService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyPanelComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("existing policy", () => {
    const policyName = "Test Policy";

    beforeEach(() => {
      fixture.componentRef.setInput("policy", { ...policyServiceMock.emptyPolicy, name: policyName });
      fixture.detectChanges();
    });

    it("should display the policy name", () => {
      expect(fixture.nativeElement).toBeTruthy();
      const policyNameElement = fixture.nativeElement.querySelector(".policy-name");
      expect(policyNameElement).toBeTruthy();
      expect(policyNameElement.textContent).toContain(policyName);
    });

    it("should select policy on expansion", () => {
      const panel = fixture.nativeElement.querySelector("mat-expansion-panel");
      panel.dispatchEvent(new Event("opened"));
      fixture.detectChanges();
      expect(policyServiceMock.selectPolicyByName).toHaveBeenCalledWith(policyName);
    });
  });

  describe("new policy", () => {
    beforeEach(() => {
      // component.isNew = input(true);
      fixture.componentRef.setInput("isNew", true);
      fixture.detectChanges();
    });

    it("should initialize new policy on expansion", () => {
      const panel = fixture.nativeElement.querySelector("mat-expansion-panel");
      panel.dispatchEvent(new Event("opened"));
      fixture.detectChanges();
      expect(policyServiceMock.initializeNewPolicy).toHaveBeenCalled();
    });
  });
});
