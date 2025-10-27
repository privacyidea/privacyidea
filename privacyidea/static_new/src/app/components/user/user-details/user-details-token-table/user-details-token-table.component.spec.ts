import { ComponentFixture, TestBed } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

import { UserDetailsTokenTableComponent } from "./user-details-token-table.component";
import {
  MockAuthService,
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockTableUtilsService,
  MockTokenService,
  MockUserService
} from "../../../../../testing/mock-services";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

import { TableUtilsService } from "../../../../services/table-utils/table-utils.service";
import { OverflowService } from "../../../../services/overflow/overflow.service";
import { ContentService } from "../../../../services/content/content.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { TokenService } from "../../../../services/token/token.service";
import { UserService } from "../../../../services/user/user.service";

describe("UserDetailsTokenTableComponent", () => {
  let fixture: ComponentFixture<UserDetailsTokenTableComponent>;
  let component: UserDetailsTokenTableComponent;

  let tokenServiceMock: MockTokenService;
  let userServiceMock: MockUserService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    tokenServiceMock = new MockTokenService();
    userServiceMock = new MockUserService();

    await TestBed.configureTestingModule({
      imports: [UserDetailsTokenTableComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: OverflowService, useValue: { isWidthOverflowing: () => false, isHeightOverflowing: () => false, getOverflowThreshold: () => 1920 } },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: TokenService, useValue: tokenServiceMock },
        { provide: UserService, useValue: userServiceMock },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserDetailsTokenTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("has the expected displayed columns", () => {
    expect(component.displayedColumns).toEqual([
      "serial",
      "tokentype",
      "active",
      "description",
      "failcount",
      "maxfail",
      "container_serial"
    ]);
  });

  it("exposes pageSizeOptions from TableUtilsService (signal)", () => {
    expect(component.pageSizeOptions()).toEqual([5, 10, 25, 50]);
  });

  it("wires paginator and sort in ngAfterViewInit", () => {
    expect(component.dataSource.paginator).toBe(component.paginator);
    expect(component.dataSource.sort).toBe(component.sort);
  });

  it("populates dataSource from userTokenResource via linkedSignal", () => {
    tokenServiceMock.userTokenResource.value.set({
      detail: {},
      id: 0,
      jsonrpc: "2.0",
      signature: "",
      time: Date.now(),
      version: "1.0",
      versionnumber: "1.0",
      result: {
        status: true,
        value: {
          count: 2,
          current: 2,
          tokens: [
            {
              serial: "T-1",
              tokentype: "hotp",
              active: true,
              revoked: false,
              locked: false,
              description: "alpha",
              failcount: 0,
              maxfail: 10,
              container_serial: "C-1",
              user_realm: "r1",
              username: "alice",
              resolver: ""
            },
            {
              serial: "T-2",
              tokentype: "totp",
              active: false,
              revoked: false,
              locked: false,
              description: "beta",
              failcount: 2,
              maxfail: 10,
              container_serial: "C-2",
              user_realm: "r1",
              username: "alice",
              resolver: ""
            }
          ]
        }
      }
    } as any);

    fixture.detectChanges();

    expect(component.dataSource.data.map((t: any) => t.serial)).toEqual(["T-1", "T-2"]);
  });

  it("keeps previous list when userTokenResource is missing (linkedSignal fallback)", () => {
    tokenServiceMock.userTokenResource.value.set({
      detail: {},
      id: 0,
      jsonrpc: "2.0",
      signature: "",
      time: Date.now(),
      version: "1.0",
      versionnumber: "1.0",
      result: {
        status: true,
        value: {
          count: 1,
          current: 1,
          tokens: [
            {
              serial: "KEEP-ME",
              tokentype: "hotp",
              active: true,
              revoked: false,
              locked: false,
              description: "",
              failcount: 0,
              maxfail: 10,
              container_serial: "C-X",
              user_realm: "r1",
              username: "alice",
              resolver: ""
            }
          ]
        }
      }
    } as any);
    fixture.detectChanges();
    expect(component.dataSource.data.map((t: any) => t.serial)).toEqual(["KEEP-ME"]);

    tokenServiceMock.userTokenResource.value.set(undefined as any);
    fixture.detectChanges();

    expect(component.dataSource.data.map((t: any) => t.serial)).toEqual(["KEEP-ME"]);
  });

  it("handleFilterInput normalises and applies to dataSource and userTokenData", () => {
    const ev = { target: { value: "  MixedCase Text  " } } as unknown as Event;
    component.handleFilterInput(ev);

    expect(component.filterValue).toBe("MixedCase Text");
    expect(component.dataSource.filter).toBe("mixedcase text");
    expect(component.userTokenData().filter).toBe("mixedcase text");
  });

  it("toggleActive calls service and triggers user reload", () => {
    const token = {
      serial: "S-123",
      active: true
    } as any;

    component.toggleActive(token);

    expect(tokenServiceMock.toggleActive).toHaveBeenCalledWith("S-123", true);
    expect(userServiceMock.userResource.reload).toHaveBeenCalledTimes(1);
  });

  it("resetFailCount calls service only when allowed", () => {
    const auth = TestBed.inject(AuthService) as MockAuthService;
    (auth as any).actionAllowed = jest.fn().mockReturnValue(true);

    const token = {
      serial: "X",
      revoked: false,
      locked: false
    } as any;

    component.resetFailCount(token);

    expect(tokenServiceMock.resetFailCount).toHaveBeenCalledWith("X");
    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
  });
});
