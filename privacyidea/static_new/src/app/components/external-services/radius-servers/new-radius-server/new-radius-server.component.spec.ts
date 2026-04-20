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
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";
import { RadiusServerService } from "../../../../services/radius-server/radius-server.service";
import { MockRadiusService } from "../../../../../testing/mock-services/mock-radius-service";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { MockPendingChangesService } from "../../../../../testing/mock-services/mock-pending-changes-service";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { MockDialogService } from "../../../../../testing/mock-services";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";
import { AuthService } from "../../../../services/auth/auth.service";

describe("NewRadiusServerComponent", () => {
  let component: NewRadiusServerComponent;
  let fixture: ComponentFixture<NewRadiusServerComponent>;
  let radiusServiceMock: any;
  let dialogRefMock: any;
  let dialogMock: any;
  let pendingChangesService: MockPendingChangesService;
  let dialogService: MockDialogService;
  let authService: MockAuthService;

  beforeEach(async () => {
    dialogRefMock = {
      disableClose: false,
      backdropClick: jest.fn().mockReturnValue(of()),
      keydownEvents: jest.fn().mockReturnValue(of()),
      close: jest.fn()
    };

    dialogMock = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of(true) })
    };

    await TestBed.configureTestingModule({
      imports: [NewRadiusServerComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: null },
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: RadiusServerService, useClass: MockRadiusService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).overrideComponent(NewRadiusServerComponent, {
      add: {
        providers: [
          { provide: MatDialog, useValue: dialogMock }
        ]
      }
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
    expect(dialogRefMock.close).toHaveBeenCalledWith(true);
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
    // Clear any previous calls to close from setup
    dialogRefMock.close.mockClear();

    const success = await component.save();

    expect(success).toBe(false);
    expect(radiusServiceMock.postRadiusServer).toHaveBeenCalled();
    expect(dialogRefMock.close).not.toHaveBeenCalled();
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
    });

    it("should close directly when there are no changes", () => {
      dialogRefMock.close.mockClear();

      component.onCancel();

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(dialogRefMock.close).toHaveBeenCalled();
    });

    it("should open SaveAndExitDialog when there are changes", () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
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

    it("should close when user selects 'discard' in cancel dialog", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.radiusForm.patchValue({
        identifier: "test",
        server: "1.2.3.4",
        secret: "secret",
        port: 1812
      });
      component.radiusForm.markAsDirty();
      dialogRefMock.close.mockClear();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(dialogRefMock.close).toHaveBeenCalled();
    });

    it("should close when user selects 'save-exit' and save succeeds", async () => {
      component.radiusForm.patchValue({
        identifier: "test",
        server: "1.2.3.4",
        secret: "secret",
        port: 1812
      });
      component.radiusForm.markAsDirty();
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(true));

      dialogRefMock.close.mockClear();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(dialogRefMock.close).toHaveBeenCalled();
    });

    it("should NOT close when user selects 'save-exit' but save fails", async () => {
      component.radiusForm.patchValue({
        identifier: "test",
        server: "1.2.3.4",
        secret: "secret",
        port: 1812
      });
      component.radiusForm.markAsDirty();
      radiusServiceMock.postRadiusServer.mockRejectedValue(new Error("Save failed"));
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(false));

      dialogRefMock.close.mockClear();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });

    it("should do nothing when user selects 'save-exit' but canSave is false", async () => {
      component.radiusForm.patchValue({ identifier: "" });
      component.radiusForm.markAsDirty();
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));

      dialogRefMock.close.mockClear();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.save).not.toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });

    it("should do nothing when user closes dialog without selecting an option", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of(undefined));
      component.radiusForm.patchValue({
        identifier: "test",
        server: "1.2.3.4",
        secret: "secret",
        port: 1812
      });
      component.radiusForm.markAsDirty();

      dialogRefMock.close.mockClear();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });
  });
});
