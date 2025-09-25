/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import {
  MockAuditService,
  MockAuthService,
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockTableUtilsService
} from "../../../testing/mock-services";

import { ActivatedRoute } from "@angular/router";
import { AuditComponent } from "./audit.component";
import { AuditService } from "../../services/audit/audit.service";
import { AuthService } from "../../services/auth/auth.service";
import { ContentService } from "../../services/content/content.service";
import { MatTableDataSource } from "@angular/material/table";
import { TableUtilsService } from "../../services/table-utils/table-utils.service";
import { of } from "rxjs";
import { provideHttpClient } from "@angular/common/http";
import { FilterValue } from "../../core/models/filter_value";

describe("AuditComponent (unit)", () => {
  let fixture: ComponentFixture<AuditComponent>;
  let component: AuditComponent;
  let mockAuditService: MockAuditService;
  let mockTableUtilsService: MockTableUtilsService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [AuditComponent],
      providers: [
        provideHttpClient(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        { provide: MockAuditService as any, useClass: MockAuditService },
        {
          provide: MockTableUtilsService as any,
          useClass: MockTableUtilsService
        },
        { provide: MockContentService as any, useClass: MockContentService },
        { provide: MockAuthService as any, useClass: MockAuthService },
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
    mockAuditService = TestBed.inject(MockAuditService as any);
    mockTableUtilsService = TestBed.inject(MockTableUtilsService as any);
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
    expect(component.columnKeys.length).toBe(component.columnKeysMap.length);
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

  it("emptyResource mirrors pageSize", () => {
    mockAuditService.pageSize.set(3);
    expect(component.emptyResource().length).toBe(3);
    mockAuditService.pageSize.set(7);
    expect(component.emptyResource().length).toBe(7);
  });

  it("auditDataSource updates when auditResource changes", () => {
    const rows = [{ user: "alice" } as any];
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
          auditdata: rows as any,
          auditcolumns: [],
          current: 0
        },
        status: true
      }
    });
    expect(component.auditDataSource() instanceof MatTableDataSource).toBe(true);
    expect(component.auditDataSource().data).toEqual(rows);
  });

  it("parses filterValueString and resets pageIndex through the effect", async () => {
    mockAuditService.pageIndex.set(3);
    mockAuditService.auditFilter.set(new FilterValue({ value: "user: bob success: true" }));

    await fixture.whenStable();
    await Promise.resolve();
    jest.runOnlyPendingTimers();

    expect(mockAuditService.pageIndex()).toBe(0);
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
