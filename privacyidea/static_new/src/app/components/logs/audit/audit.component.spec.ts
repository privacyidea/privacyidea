/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatTableDataSource } from "@angular/material/table";
import { ActivatedRoute } from "@angular/router";
import { AuditData, AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import {
  MockAuditService,
  MockContentService,
  MockLocalService,
  MockNotificationService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { expectedLocalDateTimeFromInput } from "@testing/expected-local-date-time";
import { MockTableUtilsService } from "@testing/mock-services/mock-table-utils-service";
import { of } from "rxjs";
import { AuditComponent } from "./audit.component";
import { AuditSelfServiceComponent } from "./audit.self-service.component";

describe("AuditComponent (unit)", () => {
  let fixture: ComponentFixture<AuditComponent>;
  let component: AuditComponent;
  let mockAuditService: MockAuditService;
  let mockTableUtilsService: MockTableUtilsService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    TestBed.overrideComponent(AuditComponent, {
      set: {
        template: "<div></div>",
        animations: []
      }
    });

    TestBed.overrideComponent(AuditSelfServiceComponent, {
      set: {
        template: "<div></div>",
        animations: []
      }
    });

    await TestBed.configureTestingModule({
      imports: [AuditComponent],
      providers: [
        provideHttpClient(),
        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } },
        { provide: MockAuditService, useClass: MockAuditService },
        { provide: MockTableUtilsService, useClass: MockTableUtilsService },
        { provide: MockContentService, useClass: MockContentService },
        { provide: MockAuthService, useClass: MockAuthService },
        { provide: AuditService, useExisting: MockAuditService },
        { provide: TableUtilsService, useExisting: MockTableUtilsService },
        { provide: ContentService, useExisting: MockContentService },
        { provide: AuthService, useExisting: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    jest.useFakeTimers();

    fixture = TestBed.createComponent(AuditComponent);
    component = fixture.componentInstance;
    mockAuditService = TestBed.inject(MockAuditService);
    mockTableUtilsService = TestBed.inject(MockTableUtilsService);
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
    expect(component.columnKeys.length).toBe(component.columnKeysMap.length);
  });

  it("creates self service", () => {
    const selfFixture = TestBed.createComponent(AuditSelfServiceComponent);
    expect(selfFixture.componentInstance).toBeTruthy();
  });

  describe("page‑related derived signals", () => {
    it.each`
      count | expectedOptions
      ${12} | ${[5, 10, 25, 50]}
      ${10} | ${[5, 10, 25, 50]}
      ${60} | ${[5, 10, 25, 50]}
    `("total=$count → pageSizeOptions=$expectedOptions", ({ count, expectedOptions }) => {
      mockAuditService.auditResource.value.set({
        detail: undefined,
        id: 0,
        jsonrpc: "",
        signature: "",
        time: 0,
        version: "",
        versionnumber: "",
        result: {
          value: {
            count,
            auditdata: [],
            auditcolumns: [],
            current: 0
          },
          status: true
        }
      });
      expect(component.totalLength()).toBe(count);
      expect(component.pageSizeOptions()).toEqual(expectedOptions);
    });
  });

  it("pageSizeOptions should add custom page size if not included in default options", () => {
    const defaultOptions = [5, 10, 25, 50];
    mockTableUtilsService.pageSizeOptions.set(defaultOptions);
    expect(component.pageSizeOptions()).toEqual(defaultOptions);

    // Check custom page size is added but does not mutate the options from the service
    const customOptions = [5, 10, 15, 25, 50];
    mockAuditService.pageSize.set(15);
    expect(component.pageSizeOptions()).toEqual(customOptions);
    expect(mockTableUtilsService.pageSizeOptions()).toEqual(defaultOptions);

    // custom page size should still be included if selected pageSize changes
    mockAuditService.pageSize.set(10);
    expect(component.pageSizeOptions()).toEqual(customOptions);
  });

  it("emptyResource mirrors pageSize", () => {
    mockAuditService.pageSize.set(3);
    expect(component.emptyResource().length).toBe(3);
    mockAuditService.pageSize.set(7);
    expect(component.emptyResource().length).toBe(7);
  });

  it("auditDataSource updates when auditResource changes", () => {
    const rows: AuditData[] = [{ user: "alice" } as AuditData];
    mockAuditService.auditResource.value.set({
      detail: undefined,
      id: 0,
      jsonrpc: "",
      signature: "",
      time: 0,
      version: "",
      versionnumber: "",
      result: {
        value: {
          count: 1,
          auditdata: rows,
          auditcolumns: [],
          current: 0
        },
        status: true
      }
    });
    expect(component.auditDataSource() instanceof MatTableDataSource).toBe(true);
    expect(component.auditDataSource().data).toEqual(rows);
  });

  it("onPageEvent mutates pageSize & pageIndex signals", () => {
    component.onPageEvent({
      pageSize: 15,
      pageIndex: 2,
      length: 0,
      previousPageIndex: 1
    });
    expect(mockAuditService.pageSize()).toBe(15);
    expect(mockAuditService.pageIndex()).toBe(2);
  });
});

describe("AuditComponent (template rendering)", () => {
  let fixture: ComponentFixture<AuditComponent>;
  let component: AuditComponent;
  let mockAuditService: MockAuditService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [AuditComponent],
      providers: [
        provideHttpClient(),
        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } },
        { provide: MockAuditService, useClass: MockAuditService },
        { provide: MockTableUtilsService, useClass: MockTableUtilsService },
        { provide: MockContentService, useClass: MockContentService },
        { provide: MockAuthService, useClass: MockAuthService },
        { provide: AuditService, useExisting: MockAuditService },
        { provide: TableUtilsService, useExisting: MockTableUtilsService },
        { provide: ContentService, useExisting: MockContentService },
        { provide: AuthService, useExisting: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AuditComponent);
    component = fixture.componentInstance;
    mockAuditService = TestBed.inject(MockAuditService);
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the startdate column as local date/time, not the raw server string", () => {
    const rows: AuditData[] = [{ startdate: "2026-01-15T10:00:00.123456" } as AuditData];
    mockAuditService.auditResource.value.set({
      detail: undefined,
      id: 0,
      jsonrpc: "",
      signature: "",
      time: 0,
      version: "",
      versionnumber: "",
      result: {
        value: {
          count: 1,
          auditdata: rows,
          auditcolumns: [],
          current: 0
        },
        status: true
      }
    });
    fixture.detectChanges();

    const startdateColumnIndex = component.columnKeysMap.findIndex((c) => c.key === "startdate");
    const cells = fixture.nativeElement.querySelectorAll("tbody td");
    const cellText = cells[startdateColumnIndex].textContent.trim();

    expect(cellText).toBe(expectedLocalDateTimeFromInput("2026-01-15T10:00:00.123456"));
    expect(cellText).not.toContain("2026-01-15T10:00:00");
  });
});
