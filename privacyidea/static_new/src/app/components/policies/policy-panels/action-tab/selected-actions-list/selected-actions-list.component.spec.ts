import { ComponentFixture, TestBed } from "@angular/core/testing";
import { SelectedActionsListComponent } from "./selected-actions-list.component";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";

describe("SelectedActionsListComponent", () => {
  let component: SelectedActionsListComponent;
  let fixture: ComponentFixture<SelectedActionsListComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SelectedActionsListComponent, NoopAnimationsModule],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    }).compileComponents();

    fixture = TestBed.createComponent(SelectedActionsListComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    component = fixture.componentInstance;
    fixture.componentRef.setInput("actions", []);
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display a list of actions", () => {
    const actions = [
      { name: "action1", value: "value1" },
      { name: "action2", value: "value2" }
    ];
    fixture.componentRef.setInput("actions", actions);
    fixture.detectChanges();

    const actionElements = fixture.nativeElement.querySelectorAll(".action-card");
    expect(actionElements.length).toBe(actions.length);
  });

  it("should select an action on click", () => {
    const actions = [{ name: "action1", value: "value1" }];
    fixture.componentRef.setInput("actions", actions);
    fixture.detectChanges();

    const actionElement = fixture.nativeElement.querySelector(".action-card");
    actionElement.click();

    const selectedAction = policyServiceMock.selectedAction();
    expect(selectedAction).toBe(actions[0]);
  });
});
