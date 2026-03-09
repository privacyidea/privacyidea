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

import { ClientsComponent } from "./clients.component";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { MockAuditService, MockContentService, MockPiResponse } from "../../../../testing/mock-services";
import { ClientsDict } from "../../../services/clients/clients.service";
import { FilterValue } from "../../../core/models/filter_value/filter_value";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";

describe("ClientsComponent", () => {
  let fixture: ComponentFixture<ClientsComponent>;
  let component: ClientsComponent;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [ClientsComponent],
      providers: [
        { provide: "AuditService", useClass: MockAuditService },
        { provide: "AuthService", useClass: MockAuthService },
        { provide: "ContentService", useClass: MockContentService },
        provideHttpClient()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ClientsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("should be created", () => {
    expect(component).toBeTruthy();
  });

  it("should flatten client rows correctly", () => {
    const dict: ClientsDict = {
      "app1/1.0 comment": [
        { hostname: "host1", ip: "1.2.3.4", lastseen: "2024-06-01T12:00:00Z", application: "app1/1.0 comment" },
        { hostname: "host2", ip: "2.3.4.5", lastseen: "2024-06-02T12:00:00Z", application: "app1/1.0 comment" }
      ],
      "app2/2.0": [{ hostname: "host3", ip: "3.4.5.6", lastseen: "2024-06-03T12:00:00Z", application: "app2/2.0" }]
    };
    const rows = component.flattenedClientRowsFromDict(dict);
    expect(rows.length).toBe(3);
    expect(rows[0].isFirst).toBe(true);
    expect(rows[0].rowspan).toBe(2);
    expect(rows[1].isFirst).toBe(false);
    expect(rows[1].rowspan).toBe(1);
    expect(rows[2].isFirst).toBe(true);
    expect(rows[2].rowspan).toBe(1);
    expect(rows[0].application).toBe("app1/1.0 comment");
    expect(rows[2].application).toBe("app2/2.0");
  });

  it("should set filterValue and filter datasource on handleFilterInput", () => {
    const event = { target: { value: "test" } } as any as Event;
    component.handleFilterInput(event);
    expect(component.filterValue).toBe("test");
    expect(component.clientDataSource().filter).toBe("test");
  });

  it("should clear filter", () => {
    component.filterValue = "something";
    component.clientDataSource().filter = "something";
    component.clearFilter();
    expect(component.filterValue).toBe("");
    expect(component.clientDataSource().filter).toBe("");
  });

  it("should set activeSortColumn on sort change", () => {
    component.onSortChange({ active: "hostname" });
    expect(component.activeSortColumn()).toBe("hostname");
    component.onSortChange({ active: "" });
    expect(component.activeSortColumn()).toBeNull();
  });

  it("should split user agent string correctly", () => {
    const result = (component as any)._split_user_agent("privacyIDEA-Keycloak/1.5.1 Keycloak/25.0.1");
    expect(result.userAgent).toBe("privacyIDEA-Keycloak");
    expect(result.version).toBe("1.5.1");
    expect(result.comment).toBe("Keycloak/25.0.1");
  });

  it("should call auditService.auditFilter.set with correct IP filter", () => {
    const spy = jest.spyOn(component.auditService.auditFilter, "set");
    (component as any).showInAuditLog("ip", "1.2.3.4");
    expect(spy).toHaveBeenCalledWith(new FilterValue({ value: "client: 1.2.3.4" }));
  });

  it("should call auditService.auditFilter.set with correct user agent filter", () => {
    const spy = jest.spyOn(component.auditService.auditFilter, "set");
    (component as any).showInAuditLog("application", "privacyIDEA-Keycloak/1.5.1 Keycloak/25.0.1");
    expect(spy).toHaveBeenCalledWith(
      new FilterValue({
        value: "user_agent: privacyIDEA-Keycloak user_agent_version:" + " 1.5.1"
      })
    );
  });

  it("should not set auditFilter for not covered columns", () => {
    const spy = jest.spyOn(component.auditService.auditFilter, "set");
    (component as any).showInAuditLog("hostname", "host");
    expect(spy).not.toHaveBeenCalled();
  });

  it("should create MatTableDataSource with correct sorting accessor for lastseen", () => {
    const dict: ClientsDict = {
      app: [{ hostname: "host", ip: "1.2.3.4", lastseen: "2024-06-01T12:00:00Z", application: "app" }]
    };
    // Set the resource value directly
    component.clientService.clientsResource.value.set(MockPiResponse.fromValue(dict));
    const ds = component.clientDataSource();
    expect(ds).toBeDefined();
    expect(ds.data.length).toBe(1);
    expect(ds.data[0].hostname).toBe("host");
    expect(ds.sortingDataAccessor(ds.data[0], "lastseen")).toBe(new Date("2024-06-01T12:00:00Z").getTime());
  });
});
