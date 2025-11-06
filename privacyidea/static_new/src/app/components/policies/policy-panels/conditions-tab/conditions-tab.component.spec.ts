import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ConditionsTabComponent } from "./conditions-tab.component";
import { PolicyService } from "../../../../services/policies/policies.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import "@angular/localize/init";
import { MockPolicyService } from "../../../../../testing/mock-services/mock-policies-service";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("ConditionsTabComponent", () => {
  let component: ConditionsTabComponent;
  let fixture: ComponentFixture<ConditionsTabComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionsTabComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: PolicyService,
          useClass: MockPolicyService
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionsTabComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
