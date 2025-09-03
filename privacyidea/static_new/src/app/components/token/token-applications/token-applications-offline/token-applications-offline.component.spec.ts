import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatTableDataSource } from "@angular/material/table";
import { MatTabsModule } from "@angular/material/tabs";
import {
  MockLocalService,
  MockMachineService, MockNotificationService,
  MockTableUtilsService
} from "../../../../../testing/mock-services";
import { MachineService, TokenApplication } from "../../../../services/machine/machine.service";
import { TableUtilsService } from "../../../../services/table-utils/table-utils.service";
import { TokenService } from "../../../../services/token/token.service";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import { KeywordFilterComponent } from "../../../shared/keyword-filter/keyword-filter.component";
import { TokenApplicationsOfflineComponent } from "./token-applications-offline.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("TokenApplicationsOfflineComponent (Jest)", () => {
  let fixture: ComponentFixture<TokenApplicationsOfflineComponent>;
  let component: TokenApplicationsOfflineComponent;
  let machineServiceMock: MockMachineService;
  let mockTokenService: Partial<TokenService> = {};

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [
        TokenApplicationsOfflineComponent,
        MatTabsModule,
        KeywordFilterComponent,
        CopyButtonComponent
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineService, useClass: MockMachineService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: TokenService, useValue: mockTokenService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenApplicationsOfflineComponent);
    machineServiceMock = TestBed.inject(MachineService) as any;
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should have correct displayedColumns", () => {
    expect(component.displayedColumns).toEqual(["serial", "count", "rounds"]);
  });

  it("should return object strings correctly", () => {
    const options = { key1: "value1", key2: "value2" };
    expect(component.getObjectStrings(options)).toEqual([
      "key1: value1",
      "key2: value2"
    ]);
  });

  describe("dataSource computed", () => {
    it("returns a MatTableDataSource when tokenApplications() yields data", () => {
      const fakeApps: TokenApplication[] = [
        {
          id: 1,
          machine_id: "m1",
          options: {},
          resolver: "",
          serial: "",
          type: "",
          application: ""
        }
      ];
      machineServiceMock.tokenApplications.set(fakeApps);

      fixture.detectChanges();

      const ds = component.dataSource();
      expect(ds).toBeInstanceOf(MatTableDataSource);
      expect((ds as MatTableDataSource<TokenApplication>).data).toEqual(
        fakeApps
      );
      expect(component.length()).toBe(1);
    });
  });
});
