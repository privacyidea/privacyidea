import { ComponentFixture, TestBed } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { of, Subject } from "rxjs";
import { signal } from "@angular/core";
import { MatTableDataSource } from "@angular/material/table";
import { NavigationEnd, Router } from "@angular/router";

import { ContainerDetailsTokenTableComponent } from "./container-details-token-table.component";
import {
  MockAuthService,
  MockContainerService,
  MockContentService,
  MockNotificationService,
  MockOverflowService,
  MockTableUtilsService,
  MockTokenService,
  MockUserService
} from "../../../../../testing/mock-services";
import { AuthService } from "../../../../services/auth/auth.service";
import { ContainerService } from "../../../../services/container/container.service";
import { TokenService } from "../../../../services/token/token.service";
import { TableUtilsService } from "../../../../services/table-utils/table-utils.service";
import { OverflowService } from "../../../../services/overflow/overflow.service";
import { NotificationService } from "../../../../services/notification/notification.service";
import { MatDialog } from "@angular/material/dialog";
import { UserService } from "../../../../services/user/user.service";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { ContentService } from "../../../../services/content/content.service";

const routerEvents$ = new Subject<NavigationEnd>();
routerEvents$.next(new NavigationEnd(1, "/", "/"));
const routerMock = {
  navigate: jest.fn().mockResolvedValue(true),
  url: "/",
  events: routerEvents$
} as unknown as jest.Mocked<Router>;

function makeDialogResult(result: boolean) {
  return { afterClosed: () => of(result) } as any;
}

const matDialogMock = {
  open: jest.fn().mockReturnValue(makeDialogResult(true))
};

describe("ContainerDetailsTokenTableComponent", () => {
  let fixture: ComponentFixture<ContainerDetailsTokenTableComponent>;
  let component: ContainerDetailsTokenTableComponent;

  const containerServiceMock = new MockContainerService();
  const tokenServiceMock = new MockTokenService();
  const overflowServiceMock = new MockOverflowService();
  const tableUtilsMock = new MockTableUtilsService();
  const authServiceMock = new MockAuthService();
  const notificationServiceMock = new MockNotificationService();

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsTokenTableComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authServiceMock },
        { provide: ContainerService, useValue: containerServiceMock },
        { provide: TokenService, useValue: tokenServiceMock },
        { provide: TableUtilsService, useValue: tableUtilsMock },
        { provide: OverflowService, useValue: overflowServiceMock },
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: Router, useValue: routerMock },
        { provide: MatDialog, useValue: matDialogMock },
        { provide: UserService, useClass: MockUserService },
        { provide: ContentService, useClass: MockContentService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsTokenTableComponent);
    component = fixture.componentInstance;

    component.containerTokenData = signal(
      new MatTableDataSource<any>([
        {
          serial: "Mock serial",
          tokentype: "hotp",
          active: true,
          username: "userA"
        },
        {
          serial: "Another serial",
          tokentype: "totp",
          active: false,
          username: "userB"
        }
      ])
    );

    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("creates the component", () => {
    expect(component).toBeTruthy();
  });

  it("sets paginator and sort on the dataSource", () => {
    const ds = component.containerTokenData();
    expect(ds.paginator).toBe(component.paginator);
    expect(ds.sort).toBe(component.sort);
  });

  it("updates filterValue and MatTableDataSource.filter", () => {
    const mockEvent = { target: { value: " testFilter " } } as unknown as Event;

    component.handleFilterInput(mockEvent);

    expect(component.filterValue).toBe("testFilter");
    expect(component.containerTokenData().filter).toBe("testfilter");
  });

  it("delegates to toggleActive when columnKey === \"active\"", () => {
    const toggleSpy = jest.spyOn(component, "toggleActive");
    const row = { serial: "Mock serial", active: true };

    component.handleColumnClick("active", row as any);

    expect(toggleSpy).toHaveBeenCalledWith(row);
  });

  it("does nothing when columnKey !== \"active\"", () => {
    const toggleSpy = jest.spyOn(component, "toggleActive");

    component.handleColumnClick("username", {} as any);

    expect(toggleSpy).not.toHaveBeenCalled();
  });

  describe("deleteAllTokens()", () => {
    it("opens confirm dialog and deletes on confirm", () => {
      component.deleteAllTokens();

      expect(matDialogMock.open).toHaveBeenCalledWith(
        ConfirmationDialogComponent,
        {
          data: {
            serialList: ["Mock serial", "Another serial"],
            title: "Delete All Tokens",
            type: "token",
            action: "delete",
            numberOfTokens: 2
          }
        }
      );

      expect(containerServiceMock.deleteAllTokens).toHaveBeenCalledWith({
        containerSerial: "CONT-1",
        serialList: "Mock serial,Another serial"
      });
    });

    it("does NOT delete if dialog returns false", () => {
      matDialogMock.open.mockReturnValueOnce(makeDialogResult(false));

      component.deleteAllTokens();

      expect(containerServiceMock.deleteAllTokens).not.toHaveBeenCalled();
    });
  });
});
