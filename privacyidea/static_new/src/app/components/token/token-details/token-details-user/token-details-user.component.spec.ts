import { ComponentFixture, TestBed } from "@angular/core/testing";
import { TokenDetailsUserComponent } from "./token-details-user.component";
import { TokenService } from "../../../../services/token/token.service";
import { AppComponent } from "../../../../app.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { UserService } from "../../../../services/user/user.service";
import { MockUserService } from "../../../../../testing/mock-services";

describe("TokenDetailsUserComponent", () => {
  let component: TokenDetailsUserComponent;
  let fixture: ComponentFixture<TokenDetailsUserComponent>;
  let tokenService: TokenService;
  let userService: MockUserService;

  beforeEach(async () => {
    jest.clearAllMocks();

    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [
        TokenDetailsUserComponent,
        AppComponent,
        BrowserAnimationsModule
      ],
      providers: [
        TokenService,
        { provide: UserService, useClass: MockUserService },
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    }).compileComponents();

    tokenService = TestBed.inject(TokenService);
    userService = TestBed.inject(UserService) as unknown as MockUserService;
    fixture = TestBed.createComponent(TokenDetailsUserComponent);
    component = fixture.componentInstance;

    component.tokenSerial = signal("Mock serial");
    component.isEditingUser = signal(false);
    component.setPinValue = signal("");
    component.repeatPinValue = signal("");

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should assign user", () => {
    userService.selectedUsername.set("testUser");
    userService.selectedUserRealm.set("testRealm");
    component.setPinValue.set("1234");
    component.repeatPinValue.set("1234");

    const assignSpy = jest.spyOn(tokenService, "assignUser");

    component.saveUser();

    expect(assignSpy).toHaveBeenCalledWith({
      pin: "1234",
      realm: "testRealm",
      tokenSerial: "Mock serial",
      username: ""
    });
  });

  it("should not assign user if PINs do not match", () => {
    component.setPinValue.set("1234");
    component.repeatPinValue.set("5678");

    const assignSpy = jest.spyOn(tokenService, "assignUser");

    component.saveUser();

    expect(assignSpy).not.toHaveBeenCalled();
  });
});
