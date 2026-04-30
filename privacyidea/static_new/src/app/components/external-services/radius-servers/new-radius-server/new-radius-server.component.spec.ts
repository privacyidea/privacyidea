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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NewRadiusServerComponent } from "./new-radius-server.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ActivatedRoute, convertToParamMap, ParamMap, Router } from "@angular/router";
import { BehaviorSubject } from "rxjs";
import { RadiusServerService } from "../../../../services/radius-server/radius-server.service";
import { MockRadiusService } from "../../../../../testing/mock-services/mock-radius-service";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { MockPendingChangesService } from "../../../../../testing/mock-services/mock-pending-changes-service";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { MockDialogService } from "../../../../../testing/mock-services";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";
import { AuthService } from "../../../../services/auth/auth.service";
import { ROUTE_PATHS } from "../../../../route_paths";
import { signal } from "@angular/core";

describe("NewRadiusServerComponent", () => {
  let component: NewRadiusServerComponent;
  let fixture: ComponentFixture<NewRadiusServerComponent>;
  let radiusServiceMock: any;
  let pendingChangesService: MockPendingChangesService;
  let dialogService: MockDialogService;
  let authService: MockAuthService;
  let routerMock: { navigateByUrl: jest.Mock };
  let paramMapSubject: BehaviorSubject<ParamMap>;

  beforeEach(async () => {
    paramMapSubject = new BehaviorSubject(convertToParamMap({}));
    routerMock = { navigateByUrl: jest.fn().mockResolvedValue(true) };

    await TestBed.configureTestingModule({
      imports: [NewRadiusServerComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: routerMock },
        { provide: RadiusServerService, useClass: MockRadiusService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ActivatedRoute, useValue: { paramMap: paramMapSubject.asObservable() } }
      ]
    }).compileComponents();

    radiusServiceMock = TestBed.inject(RadiusServerService);
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;

    fixture = TestBed.createComponent(NewRadiusServerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form for create mode", () => {
    expect(component.isEditMode).toBe(false);
    expect(component.radiusForm.get("identifier")?.value).toBe("");
  });

  it("should initialize form for edit mode", () => {
    radiusServiceMock.radiusServers = signal([
      { identifier: "test", server: "1.2.3.4", port: 1812, timeout: 5, retries: 3, secret: "s" }
    ]);

    paramMapSubject.next(convertToParamMap({ identifier: "test" }));

    fixture.destroy();
    fixture = TestBed.createComponent(NewRadiusServerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.isEditMode).toBe(true);
    expect(component.radiusForm.get("identifier")?.value).toBe("test");
    expect(component.radiusForm.get("identifier")?.disabled).toBe(true);
  });

  it("should call save when form is valid", async () => {
    component.radiusForm.patchValue({
      identifier: "test",
      server: "1.2.3.4",
      secret: "secret",
      port: 1812,
      timeout: 5,
      retries: 3
    });

    const success = await component.save();

    expect(success).toBe(true);
    expect(radiusServiceMock.postRadiusServer).toHaveBeenCalled();
    expect(routerMock.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS);
  });

  it("should handle error on save", async () => {
    component.radiusForm.patchValue({
      identifier: "test",
      server: "1.2.3.4",
      secret: "secret",
      port: 1812,
      timeout: 5,
      retries: 3
    });
    radiusServiceMock.postRadiusServer.mockRejectedValue(new Error("Save failed"));

    const success = await component.save();

    expect(success).toBe(false);
    expect(radiusServiceMock.postRadiusServer).toHaveBeenCalled();
  });

  it("should call test when form is valid", async () => {
    component.radiusForm.patchValue({
      identifier: "test",
      server: "1.2.3.4",
      secret: "secret",
      port: 1812,
      timeout: 5,
      retries: 3
    });
    await component.test();
    expect(radiusServiceMock.testRadiusServer).toHaveBeenCalled();
  });

  describe("onCancel", () => {
    let mockSaveExitDialogRef: any;

    beforeEach(() => {
      mockSaveExitDialogRef = {
        afterClosed: jest.fn()
      };
      dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);
      authService.actionAllowed = jest.fn().mockReturnValue(true);
      routerMock.navigateByUrl.mockClear();
    });

    it("should navigate back directly when there are no changes", () => {
      component.onCancel();

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(routerMock.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS);
    });

    it("should open SaveAndExitDialog when there are changes", () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(new BehaviorSubject("discard").asObservable());
      component.radiusForm.patchValue({
        identifier: "test",
        server: "1.2.3.4",
        secret: "secret",
        port: 1812
      });
      component.radiusForm.markAsDirty();

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
      mockSaveExitDialogRef.afterClosed.mockReturnValue(new BehaviorSubject("discard").asObservable());
      component.radiusForm.patchValue({
        identifier: "test",
        server: "1.2.3.4",
        secret: "secret",
        port: 1812
      });
      component.radiusForm.markAsDirty();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(routerMock.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS);
    });

    it("should navigate back when user selects 'save-exit' and save succeeds", async () => {
      component.radiusForm.patchValue({
        identifier: "test",
        server: "1.2.3.4",
        secret: "secret",
        port: 1812
      });
      component.radiusForm.markAsDirty();
      mockSaveExitDialogRef.afterClosed.mockReturnValue(new BehaviorSubject("save-exit").asObservable());
      pendingChangesService.save.mockReturnValue(Promise.resolve(true));

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(routerMock.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS);
    });

    it("should NOT navigate when user selects 'save-exit' but save fails", async () => {
      component.radiusForm.patchValue({
        identifier: "test",
        server: "1.2.3.4",
        secret: "secret",
        port: 1812
      });
      component.radiusForm.markAsDirty();
      radiusServiceMock.postRadiusServer.mockRejectedValue(new Error("Save failed"));
      mockSaveExitDialogRef.afterClosed.mockReturnValue(new BehaviorSubject("save-exit").asObservable());
      pendingChangesService.save.mockReturnValue(Promise.resolve(false));

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(routerMock.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should do nothing when user selects 'save-exit' but canSave is false", async () => {
      component.radiusForm.patchValue({ identifier: "" });
      component.radiusForm.markAsDirty();
      mockSaveExitDialogRef.afterClosed.mockReturnValue(new BehaviorSubject("save-exit").asObservable());

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.save).not.toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(routerMock.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should do nothing when user closes dialog without selecting an option", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(new BehaviorSubject(undefined).asObservable());
      component.radiusForm.patchValue({
        identifier: "test",
        server: "1.2.3.4",
        secret: "secret",
        port: 1812
      });
      component.radiusForm.markAsDirty();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(routerMock.navigateByUrl).not.toHaveBeenCalled();
    });
  });
});
