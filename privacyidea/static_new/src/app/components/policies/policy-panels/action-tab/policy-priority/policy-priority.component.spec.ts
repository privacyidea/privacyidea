
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PolicyPriorityComponent } from "./policy-priority.component";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { input } from "@angular/core";

describe("PolicyPriorityComponent", () => {
  let component: PolicyPriorityComponent;
  let fixture: ComponentFixture<PolicyPriorityComponent>;
  let policyServiceMock: any;

  beforeEach(async () => {
    policyServiceMock = {
      updateSelectedPolicy: jasmine.createSpy("updateSelectedPolicy"),
    };

    await TestBed.configureTestingModule({
      imports: [PolicyPriorityComponent, NoopAnimationsModule],
      providers: [{ provide: PolicyService, useValue: policyServiceMock }],
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyPriorityComponent);
    component = fixture.componentInstance;
    component.editMode = input(true);
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should update policy priority on input", () => {
    const priority = 10;
    component.updatePolicyPriority(priority);
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ priority });
  });
});
