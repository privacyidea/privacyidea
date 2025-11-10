import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PolicyDescriptionComponent } from "./policy-description.component";
import { DocumentationService } from "../../../../../services/documentation/documentation.service";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";
import { MockDocumentationService } from "../../../../../../testing/mock-services/mock-documentation-service";
import "@angular/localize/init";

describe("PolicyDescriptionComponent", () => {
  let component: PolicyDescriptionComponent;
  let fixture: ComponentFixture<PolicyDescriptionComponent>;
  let policyServiceMock: MockPolicyService;
  let documentationServiceMock: MockDocumentationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyDescriptionComponent, NoopAnimationsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: DocumentationService, useClass: MockDocumentationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyDescriptionComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    documentationServiceMock = TestBed.inject(DocumentationService) as unknown as MockDocumentationService;
    component = fixture.componentInstance;
    policyServiceMock.isEditMode.set(false);
    policyServiceMock.selectedPolicy.set({
      action: null,
      active: true,
      adminrealm: [],
      adminuser: [],
      check_all_resolvers: false,
      client: [],
      conditions: [],
      description: "test description",
      name: "test-policy",
      pinode: [],
      priority: 1,
      realm: [],
      resolver: [],
      scope: "",
      time: "",
      user: [],
      user_agents: [],
      user_case_insensitive: false
    });
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should update policy description on input", () => {
    const description = "new test description";
    component.updatePolicyDescription(description);
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ description });
  });

  it("should open documentation on button click", () => {
    const page = "test-page";
    component.openDocumentation(page);
    expect(documentationServiceMock.openDocumentation).toHaveBeenCalledWith(page);
  });

  describe("non-edit mode", () => {
    beforeEach(() => {
      policyServiceMock.isEditMode.set(false);
      fixture.detectChanges();
    });

    it("should display the description when available", () => {
      const descriptionEl = fixture.nativeElement.querySelector(".description-text");
      expect(descriptionEl).toBeTruthy();
      expect(descriptionEl.textContent.trim()).toBe("test description");
    });

    it("should not display the description section when description is null", () => {
      policyServiceMock.selectedPolicy.set({
        ...policyServiceMock.selectedPolicy()!,
        description: null
      });
      fixture.detectChanges();
      const descriptionContainer = fixture.nativeElement.querySelector(".action-description-container");
      expect(descriptionContainer).toBeFalsy();
    });
  });

  describe("edit mode", () => {
    beforeEach(() => {
      policyServiceMock.isEditMode.set(true);
      fixture.detectChanges();
    });

    it("should display a textarea", () => {
      const textareaEl = fixture.nativeElement.querySelector("textarea");
      expect(textareaEl).toBeTruthy();
      expect(textareaEl.value).toBe("test description");
    });

    it("should have the correct placeholder", () => {
      const textareaEl = fixture.nativeElement.querySelector("textarea");
      expect(textareaEl.placeholder).toBe("(optional) Enter a description for this policy...");
    });

    it("should call updatePolicyDescription when textarea value changes", async () => {
      const spy = jest.spyOn(component, "updatePolicyDescription");
      const textareaEl = fixture.nativeElement.querySelector("textarea");
      textareaEl.value = "updated description";
      textareaEl.dispatchEvent(new Event("input"));
      fixture.detectChanges();
      await fixture.whenStable();
      expect(spy).toHaveBeenCalledWith("updated description");
    });
  });
});
