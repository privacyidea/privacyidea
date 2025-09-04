import { ComponentFixture, TestBed } from "@angular/core/testing";
import { TokenDetailsActionsComponent } from "./token-details-actions.component";
import { TokenService } from "../../../../services/token/token.service";
import { ValidateService } from "../../../../services/validate/validate.service";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { MockTokenService } from "../../../../../testing/mock-services";

describe("TokenDetailsActionsComponent", () => {
  let component: TokenDetailsActionsComponent;
  let fixture: ComponentFixture<TokenDetailsActionsComponent>;

  beforeEach(async () => {
    jest.clearAllMocks();
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenDetailsActionsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        ValidateService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsActionsComponent);
    component = fixture.componentInstance;
    component.tokenSerial = signal("Mock serial");
    component.tokenType = signal("Mock type");

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
