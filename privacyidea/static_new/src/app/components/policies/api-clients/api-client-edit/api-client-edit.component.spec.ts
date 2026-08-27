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
import { MatDialogRef } from "@angular/material/dialog";
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import {
  SaveAndExitDialogComponent,
  SaveAndExitDialogResult
} from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ApiClientService } from "@services/api-client/api-client.service";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { IntegrationsService } from "@services/integrations/integrations.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import {
  MockApiClientService,
  MockAuthService,
  MockContentService,
  MockDialogService,
  MockIntegrationsService
} from "@testing/mock-services";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { of, Subject } from "rxjs";
import { ApiClientEditComponent } from "./api-client-edit.component";

describe("ApiClientEditComponent", () => {
  let component: ApiClientEditComponent;
  let fixture: ComponentFixture<ApiClientEditComponent>;
  let apiClientServiceMock: MockApiClientService;
  let router: Router;
  let pendingChangesService: MockPendingChangesService;
  let dialogService: MockDialogService;

  async function setup(paramMap: Record<string, string> = {}) {
    await TestBed.configureTestingModule({
      imports: [ApiClientEditComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap(paramMap)) }
        },
        { provide: ApiClientService, useClass: MockApiClientService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: IntegrationsService, useClass: MockIntegrationsService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    apiClientServiceMock = TestBed.inject(ApiClientService) as unknown as MockApiClientService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);

    fixture = TestBed.createComponent(ApiClientEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  async function setupEditMode() {
    apiClientServiceMock = new MockApiClientService();
    apiClientServiceMock.apiClients.set([
      {
        id: "abc",
        display_name: "Existing Client",
        client_type: "keycloak",
        key_id: "key1",
        status: "active",
        created_at: "2026-01-01T00:00:00Z",
        last_used_at: null
      }
    ]);

    await TestBed.configureTestingModule({
      imports: [ApiClientEditComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap({ id: "abc" })) }
        },
        { provide: ApiClientService, useValue: apiClientServiceMock },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: IntegrationsService, useClass: MockIntegrationsService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);

    fixture = TestBed.createComponent(ApiClientEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it("should create in create mode and dismiss any issued key", async () => {
    await setup();
    expect(component).toBeTruthy();
    expect(component.isEditMode()).toBe(false);
    expect(component.apiClientModel().display_name).toBe("");
    expect(apiClientServiceMock.dismissIssuedKey).toHaveBeenCalled();
  });

  it("should call createClient when saving a new client", async () => {
    await setup();
    component.apiClientModel.update((m) => ({ ...m, display_name: "My Client", client_type: "keycloak" }));

    const success = await component.save();

    expect(success).toBe(true);
    expect(apiClientServiceMock.createClient).toHaveBeenCalledWith("My Client", "keycloak");
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_API_CLIENTS);
  });

  it("should keep on page if create fails", async () => {
    await setup();
    component.apiClientModel.update((m) => ({ ...m, display_name: "My Client", client_type: "keycloak" }));
    apiClientServiceMock.createClient = jest.fn().mockRejectedValue(new Error("Save failed"));

    const success = await component.save();

    expect(success).toBe(false);
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it("should load the existing client and call updateClient in edit mode", async () => {
    await setupEditMode();

    expect(component.isEditMode()).toBe(true);
    expect(component.apiClientModel().display_name).toBe("Existing Client");

    component.apiClientModel.update((m) => ({ ...m, display_name: "Renamed", status: "suspended" }));
    const success = await component.save();

    expect(success).toBe(true);
    expect(apiClientServiceMock.updateClient).toHaveBeenCalledWith("abc", {
      display_name: "Renamed",
      status: "suspended"
    });
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_API_CLIENTS);
  });

  describe("rotateKey", () => {
    let confirmClosed: Subject<boolean>;

    beforeEach(async () => {
      await setupEditMode();
      confirmClosed = new Subject();
      const dialogRefMock = new MockMatDialogRef();
      dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
      dialogService.openDialog.mockReturnValue(dialogRefMock);
    });

    it("should rotate the key after confirmation", () => {
      component.rotateKey();

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ items: ["Existing Client"] })
        })
      );
      confirmClosed.next(true);
      confirmClosed.complete();

      expect(apiClientServiceMock.rotateClient).toHaveBeenCalledWith("abc", "Existing Client");
    });

    it("should not rotate the key when the confirmation is cancelled", () => {
      component.rotateKey();
      confirmClosed.next(false);
      confirmClosed.complete();

      expect(apiClientServiceMock.rotateClient).not.toHaveBeenCalled();
    });
  });

  describe("onCancel", () => {
    let mockSaveExitDialogRef: Partial<MatDialogRef<SaveAndExitDialogComponent, SaveAndExitDialogResult>> & {
      afterClosed: jest.Mock;
    };

    beforeEach(async () => {
      await setup();
      mockSaveExitDialogRef = {
        afterClosed: jest.fn()
      };
      dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);
    });

    it("should navigate back directly when there are no changes", () => {
      component.onCancel();

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_API_CLIENTS);
    });

    it("should open SaveAndExitDialog when there are changes", () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.apiClientModel.update((m) => ({ ...m, display_name: "test" }));
      component.apiClientForm().markAsDirty();

      component.onCancel();

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          component: SaveAndExitDialogComponent,
          data: expect.objectContaining({
            allowSaveExit: true
          })
        })
      );
    });

    it("should navigate back when user selects 'discard' in cancel dialog", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.apiClientModel.update((m) => ({ ...m, display_name: "test" }));
      component.apiClientForm().markAsDirty();

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_API_CLIENTS);
    });
  });
});
