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
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ApiClientsComponent } from "@components/policies/api-clients/api-clients.component";
import { ApiClientService } from "@services/api-client/api-client.service";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { IntegrationsService } from "@services/integrations/integrations.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { expectsTableStateGating } from "@testing/table-state-gating";
import {
  MockApiClientService,
  MockAuthService,
  MockDialogService,
  MockIntegrationsService,
  MockTableUtilsService
} from "@testing/mock-services";
import { Subject } from "rxjs";

describe("ApiClientsComponent", () => {
  let component: ApiClientsComponent;
  let fixture: ComponentFixture<ApiClientsComponent>;
  let apiClientServiceMock: MockApiClientService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ApiClientsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ApiClientService, useClass: MockApiClientService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: IntegrationsService, useClass: MockIntegrationsService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    apiClientServiceMock = TestBed.inject(ApiClientService) as unknown as MockApiClientService;
    apiClientServiceMock.apiClients.set([
      {
        id: "client1",
        display_name: "Client One",
        client_type: "keycloak",
        key_id: "key1",
        status: "active",
        created_at: "2026-01-01T00:00:00Z",
        last_used_at: null
      },
      {
        id: "client2",
        display_name: "Client Two",
        client_type: "windows_cp",
        key_id: "key2",
        status: "suspended",
        created_at: "2026-01-02T00:00:00Z",
        last_used_at: "2026-01-03T00:00:00Z"
      }
    ]);

    fixture = TestBed.createComponent(ApiClientsComponent);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    confirmClosed = new Subject();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("gates the table on its read right, row count and filter", () => {
    expectsTableStateGating({
      state: component.tableState,
      right: "api_client_list"
    });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display API clients from the service", () => {
    expect(component.apiClientDataSource().data.length).toBe(2);
    expect(component.apiClientDataSource().data[0].display_name).toBe("Client One");
  });

  it("should filter API clients", () => {
    component.onFilterInput("Client One");
    expect(component.apiClientDataSource().filter).toBe("client one");
  });

  it("should keep the active filter when the client list reloads", () => {
    // Regression: every reload built a fresh MatTableDataSource, and the filter lived only
    // on the old instance - a rotate or delete silently showed all rows again while the
    // filter box still held the term.
    component.onFilterInput("Client One");
    expect(component.apiClientDataSource().filteredData.length).toBe(1);

    apiClientServiceMock.apiClients.update((clients) => [...clients]);
    fixture.detectChanges();

    expect(component.filterString()).toBe("Client One");
    expect(component.apiClientDataSource().filter).toBe("client one");
    expect(component.apiClientDataSource().filteredData.length).toBe(1);
  });

  it("should report the filtered row count to the paginator", async () => {
    // The length now comes from the data source's filtered rows alone. Note this does not
    // catch a re-added [length] binding: MatTableDataSource rewrites paginator.length
    // right after the binding runs, so the conflict is only ever a transient flicker.
    const authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["api_client_list"] });
    fixture.detectChanges();

    component.onFilterInput("Client One");
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const dataSource = component.apiClientDataSource();
    expect(dataSource.filteredData.length).toBe(1);
    expect(dataSource.paginator).toBeTruthy();

    const rangeLabel = (fixture.nativeElement as HTMLElement).querySelector(".mat-mdc-paginator-range-label");
    expect(rangeLabel?.textContent?.trim()).toContain("of 1");
  });

  it("should navigate to the edit page when editing a client", () => {
    const client = apiClientServiceMock.apiClients()[0];
    component.onEditApiClient(client);
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_API_CLIENTS_DETAILS + client.id);
  });

  it("should navigate to the create page", () => {
    component.onCreateNewApiClient();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_API_CLIENTS_NEW);
  });

  it("should rotate a client's key after confirmation", () => {
    const client = apiClientServiceMock.apiClients()[0];
    component.rotateKey(client);
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();
    expect(apiClientServiceMock.rotateClient).toHaveBeenCalledWith("client1", "Client One");
  });

  it("should not rotate a client's key when the confirmation is cancelled", () => {
    const client = apiClientServiceMock.apiClients()[0];
    component.rotateKey(client);
    confirmClosed.next(false);
    confirmClosed.complete();
    expect(apiClientServiceMock.rotateClient).not.toHaveBeenCalled();
  });

  it("should delete a client after confirmation", () => {
    const client = apiClientServiceMock.apiClients()[0];
    component.deleteClient(client);
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();
    expect(apiClientServiceMock.deleteClient).toHaveBeenCalledWith("client1");
  });

  it("should delete selected clients after confirmation", () => {
    const client = apiClientServiceMock.apiClients()[0];
    component.selector.selectRow(client);
    component.deleteSelected();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();
    expect(apiClientServiceMock.deleteClient).toHaveBeenCalledWith("client1");
  });

  it("should show the friendly label for a known client type", () => {
    expect(component.clientTypeLabel("privacyidea-cp")).toBe("Windows Credential Provider");
  });

  it("should fall back to the raw value for an unknown client type", () => {
    expect(component.clientTypeLabel("custom_type")).toBe("custom_type");
  });
});
