
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActionTabComponent } from "./action-tab.component";
import { PolicyService } from "../../../../services/policies/policies.service";
import { signal } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("ActionTabComponent", () => {
  let component: ActionTabComponent;
  let fixture: ComponentFixture<ActionTabComponent>;
  let policyServiceMock: any;

  beforeEach(async () => {
    policyServiceMock = {
      selectedPolicy: signal(null),
      isEditMode: signal(false),
    };

    await TestBed.configureTestingModule({
      imports: [ActionTabComponent, NoopAnimationsModule],
      providers: [{ provide: PolicyService, useValue: policyServiceMock }],
    }).compileComponents();

    fixture = TestBed.createComponent(ActionTabComponent);
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display actions for a selected policy", () => {
    const policy = {
      name: "test-policy",
      scope: "test",
      action: { action1: "value1", action2: "value2" },
    };
    policyServiceMock.selectedPolicy.set(policy);
    fixture.detectChanges();

    const actionElements = fixture.nativeElement.querySelectorAll("app-selected-actions-list");
    expect(actionElements.length).toBe(1);
  });

  it("should not display actions if no policy is selected", () => {
    policyServiceMock.selectedPolicy.set(null);
    fixture.detectChanges();

    const actionElements = fixture.nativeElement.querySelectorAll("app-selected-actions-list");
    expect(actionElements.length).toBe(0);
  });
});
