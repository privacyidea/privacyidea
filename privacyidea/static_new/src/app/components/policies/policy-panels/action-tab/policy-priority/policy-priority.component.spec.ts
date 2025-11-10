import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PolicyPriorityComponent } from "./policy-priority.component";
import { PolicyDetail, PolicyService } from "../../../../../services/policies/policies.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";
import "@angular/localize/init";

describe("PolicyPriorityComponent", () => {
  let component: PolicyPriorityComponent;
  let fixture: ComponentFixture<PolicyPriorityComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyPriorityComponent, NoopAnimationsModule],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyPriorityComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    component = fixture.componentInstance;
    fixture.componentRef.setInput("editMode", true);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should update policy priority on input", () => {
    const priority = 10;
    component.updatePolicyPriority(priority);
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ priority });
  });

  describe("editMode = false", () => {
    beforeEach(() => {
      fixture.componentRef.setInput("editMode", false);

      const policyDetail: PolicyDetail = {
        action: {
          action1: "value1",
          action2: "value2"
        },
        name: "",
        priority: 10,
        active: false,
        adminrealm: [],
        adminuser: [],
        check_all_resolvers: false,
        client: [],
        conditions: [],
        description: null,
        pinode: [],
        realm: [],
        resolver: [],
        scope: "",
        time: "",
        user: [],
        user_agents: [],
        user_case_insensitive: false
      };
      policyServiceMock.selectedPolicy.set(policyDetail);
      fixture.detectChanges();
    });

    it("should display the priority as text", () => {
      const priorityEl = fixture.nativeElement.querySelector(".description-text");
      expect(priorityEl).toBeTruthy();
      expect(priorityEl.textContent.trim()).toBe("10");
    });
  });

  describe("editMode = true", () => {
    beforeEach(() => {
      fixture.componentRef.setInput("editMode", true);
      const policyDetail: PolicyDetail = {
        action: {
          action1: "value1",
          action2: "value2"
        },
        name: "",
        priority: 10,
        active: false,
        adminrealm: [],
        adminuser: [],
        check_all_resolvers: false,
        client: [],
        conditions: [],
        description: null,
        pinode: [],
        realm: [],
        resolver: [],
        scope: "",
        time: "",
        user: [],
        user_agents: [],
        user_case_insensitive: false
      };

      policyServiceMock.selectedPolicy.set(policyDetail);
      fixture.detectChanges();
    });

    it("should display an input field", () => {
      const inputEl = fixture.nativeElement.querySelector("input");
      expect(inputEl).toBeTruthy();
      expect(inputEl.value).toBe("10");
    });

    it("should call updatePolicyPriority when the input value changes", async () => {
      const spy = jest.spyOn(component, "updatePolicyPriority");
      const inputEl = fixture.nativeElement.querySelector("input");
      inputEl.value = "20";
      inputEl.dispatchEvent(new Event("input"));
      fixture.detectChanges();
      await fixture.whenStable();
      expect(spy).toHaveBeenCalledWith(20);
    });
  });
});
