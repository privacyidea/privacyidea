import { ComponentFixture, TestBed } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

import { UserDetailsContainerTableComponent } from "./user-details-container-table.component";
import {
  MockAuthService,
  MockContainerService,
  MockContentService, MockLoadingService, MockLocalService, MockNotificationService,
  MockTableUtilsService,
  MockUserService
} from "../../../../../testing/mock-services";
import { ContainerService } from "../../../../services/container/container.service";
import { TableUtilsService } from "../../../../services/table-utils/table-utils.service";
import { ContentService } from "../../../../services/content/content.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { UserService } from "../../../../services/user/user.service";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("UserDetailsContainerTableComponent", () => {
  let fixture: ComponentFixture<UserDetailsContainerTableComponent>;
  let component: UserDetailsContainerTableComponent;

  let containerServiceMock: MockContainerService;
  let tableUtilsMock: MockTableUtilsService;
  let userServiceMock: MockUserService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    containerServiceMock = new MockContainerService();
    tableUtilsMock = new MockTableUtilsService();
    userServiceMock = new MockUserService();

    await TestBed.configureTestingModule({
      imports: [UserDetailsContainerTableComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerService, useValue: containerServiceMock },
        { provide: TableUtilsService, useValue: tableUtilsMock },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: UserService, useValue: userServiceMock },
        MockLocalService,
        MockNotificationService,
        MockLoadingService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserDetailsContainerTableComponent);
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
      "type",
      "states",
      "description",
      "realms"
    ]);
  });

  it("exposes pageSizeOptions from TableUtilsService", () => {
    expect(component.pageSizeOptions()).toEqual([5, 10, 25, 50]);
  });

  it("wires paginator and sort in ngAfterViewInit", () => {
    expect(component.dataSource.paginator).toBe(component.paginator);
    expect(component.dataSource.sort).toBe(component.sort);
  });

  it("filterPredicate matches on combined fields", () => {
    const row = {
      serial: "SER-001",
      type: "Box",
      description: "My demo container",
      states: ["active"],
      realms: ["r1", "blue-team"],
      users: [{ user_name: "alice", user_realm: "r1" }]
    } as any;

    const pred = component.dataSource.filterPredicate!;
    expect(pred(row, "active")).toBe(true);
    expect(pred(row, "blue-team")).toBe(true);
    expect(pred(row, "demo")).toBe(true);
    expect(pred(row, "nope")).toBe(false);
  });

  it("handleFilterInput normalises and applies to dataSource.filter", () => {
    const ev = { target: { value: "  MixedCase Text  " } } as unknown as Event;
    component.handleFilterInput(ev);

    expect(component.filterValue).toBe("mixedcase text");
    expect(component.dataSource.filter).toBe("mixedcase text");
  });

  it("onPageSizeChange updates pageSize", () => {
    component.onPageSizeChange(25);
    expect(component.pageSize).toBe(25);
  });

  it("handleStateClick calls toggleActive and reloads", () => {
    const element = { serial: "C-123", states: ["active"] } as any;
    component.handleStateClick(element);
    expect(containerServiceMock.toggleActive).toHaveBeenCalledWith("C-123", ["active"]);
    expect(containerServiceMock.containerResource.reload).toHaveBeenCalledTimes(1);
  });
});
