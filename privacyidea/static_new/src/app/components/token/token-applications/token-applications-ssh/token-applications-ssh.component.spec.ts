import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatTableDataSource } from "@angular/material/table";
import { MatTabsModule } from "@angular/material/tabs";
import {
  MockLocalService,
  MockMachineService,
  MockNotificationService,
} from "../../../../../testing/mock-services";
import { MachineService, TokenApplication } from "../../../../services/machine/machine.service";
import { TokenService } from "../../../../services/token/token.service";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import { KeywordFilterComponent } from "../../../shared/keyword-filter/keyword-filter.component";
import { TokenApplicationsSshComponent } from "./token-applications-ssh.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("TokenApplicationsSshComponent (Jest)", () => {
  let fixture: ComponentFixture<TokenApplicationsSshComponent>;
  let component: TokenApplicationsSshComponent;

  let mockTokenService: Partial<TokenService> = {};
  let mockKeywordFilterComponent: Partial<KeywordFilterComponent> = {};
  let machineServiceMock: MockMachineService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [
        TokenApplicationsSshComponent,
        MatTabsModule,
        KeywordFilterComponent,
        CopyButtonComponent
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineService, useClass: MockMachineService },
        { provide: TokenService, useValue: mockTokenService },
        {
          provide: KeywordFilterComponent,
          useValue: mockKeywordFilterComponent
        },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenApplicationsSshComponent);
    component = fixture.componentInstance;
    machineServiceMock = TestBed.inject(MachineService) as any;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should have correct displayedColumns", () => {
    expect(component.displayedColumns).toEqual([
      "serial",
      "service_id",
      "user"
    ]);
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
      machineServiceMock.tokenApplications!.set(fakeApps);

      // trigger recompute
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
