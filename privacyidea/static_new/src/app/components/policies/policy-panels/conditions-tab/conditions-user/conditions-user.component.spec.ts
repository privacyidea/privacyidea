import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ConditionsUserComponent } from "./conditions-user.component";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { RealmService } from "../../../../../services/realm/realm.service";
import { ResolverService } from "../../../../../services/resolver/resolver.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockRealmService } from "../../../../../../testing/mock-services";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";
import "@angular/localize/init";
import { MockResolverService } from "../../../../../../testing/mock-services/mock-resolver-service";

describe("ConditionsUserComponent", () => {
  let component: ConditionsUserComponent;
  let fixture: ComponentFixture<ConditionsUserComponent>;
  let policyServiceMock: MockPolicyService;
  let realmServiceMock: MockRealmService;
  let resolverServiceMock: MockResolverService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionsUserComponent, NoopAnimationsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: ResolverService, useClass: MockResolverService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionsUserComponent);
    component = fixture.componentInstance;
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    realmServiceMock = TestBed.inject(RealmService) as unknown as MockRealmService;
    resolverServiceMock = TestBed.inject(ResolverService) as unknown as MockResolverService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should select realms", () => {
    component.selectRealm(["realm1"]);
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ realm: ["realm1"] });
  });

  it("should toggle all realms", () => {
    component.toggleAllRealms();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ realm: ["realm1", "realm2"] });

    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.emptyPolicy, realm: ["realm1", "realm2"] });
    fixture.detectChanges();
    component.toggleAllRealms();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ realm: [] });
  });

  it("should select resolvers", () => {
    component.selectResolver(["resolver1"]);
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ resolver: ["resolver1"] });
  });

  it("should toggle all resolvers", () => {
    resolverServiceMock.setResolverOptions(["resolver1", "resolver2"]);
    component.toggleAllResolvers();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ resolver: ["resolver1", "resolver2"] });

    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.emptyPolicy, resolver: ["resolver1", "resolver2"] });
    fixture.detectChanges();
    component.toggleAllResolvers();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ resolver: [] });
  });

  it("should add user", () => {
    component.userFormControl.setValue("testuser");
    component.addUser("testuser");
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ user: ["testuser"] });
  });

  it("should remove user", () => {
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.emptyPolicy, user: ["testuser"] });
    fixture.detectChanges();
    component.removeUser("testuser");
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ user: [] });
  });

  it("should clear users", () => {
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.emptyPolicy, user: ["testuser"] });
    fixture.detectChanges();
    component.clearUsers();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ user: [] });
  });

  it("should toggle user case insensitive", () => {
    component.toggleUserCaseInsensitive();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ user_case_insensitive: true });
  });

  it("should validate user", () => {
    expect(component.userValidator(component.userFormControl)).toBeNull();
    component.userFormControl.setValue("invalid,");
    expect(component.userValidator(component.userFormControl)).toEqual({ includesComma: { value: "invalid," } });
  });
});
