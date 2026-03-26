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
import { NewServiceIdComponent } from "./new-service-id.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";
import { ServiceIdService } from "../../../../services/service-id/service-id.service";
import { MockServiceIdService } from "../../../../../testing/mock-services/mock-service-id-service";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { MockPendingChangesService } from "../../../../../testing/mock-services/mock-pending-changes-service";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { MockDialogService } from "../../../../../testing/mock-services";

describe("NewServiceIdComponent", () => {
  let component: NewServiceIdComponent;
  let fixture: ComponentFixture<NewServiceIdComponent>;
  let serviceIdServiceMock: any;
  let dialogRefMock: any;
  let dialogMock: any;
  let pendingChangesService: MockPendingChangesService;
  let dialogService: MockDialogService;

  beforeEach(async () => {
    dialogRefMock = {
      disableClose: false,
      backdropClick: jest.fn().mockReturnValue(of()),
      keydownEvents: jest.fn().mockReturnValue(of()),
      close: jest.fn()
    };

    dialogMock = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of(true) }),
    };

    await TestBed.configureTestingModule({
      imports: [NewServiceIdComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: null },
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: ServiceIdService, useClass: MockServiceIdService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService },
      ]
    }).overrideComponent(NewServiceIdComponent, {
      add: {
        providers: [
          { provide: MatDialog, useValue: dialogMock }
        ]
      }
    }).compileComponents();

    serviceIdServiceMock = TestBed.inject(ServiceIdService);
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;

    fixture = TestBed.createComponent(NewServiceIdComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form for create mode", () => {
    expect(component.isEditMode).toBe(false);
    expect(component.serviceIdForm.get("servicename")?.value).toBe("");
  });

  it("should call save when form is valid", async () => {
    component.serviceIdForm.patchValue({
      servicename: "test",
      description: "desc"
    });

    const success = await component.save();

    expect(success).toBe(true);
    expect(serviceIdServiceMock.postServiceId).toHaveBeenCalled();
    expect(dialogRefMock.close).toHaveBeenCalledWith(true);
  });

  it("should keep dialog open if save fails", async () => {
    component.serviceIdForm.patchValue({
      servicename: "test",
      description: "desc"
    });
    serviceIdServiceMock.postServiceId = jest.fn().mockRejectedValue(new Error("Save failed"));
    // Clear any previous calls to close from setup
    dialogRefMock.close.mockClear();

    const success = await component.save();

    expect(success).toBe(false);
    expect(serviceIdServiceMock.postServiceId).toHaveBeenCalled();
    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  describe("onCancel", () => {
    let mockSaveExitDialogRef: any;

    beforeEach(() => {
      mockSaveExitDialogRef = {
        afterClosed: jest.fn()
      };
      dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);
    });

    it("should close directly when there are no changes", () => {
      dialogRefMock.close.mockClear();

      component.onCancel();

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(dialogRefMock.close).toHaveBeenCalled();
    });

    it("should open SaveAndExitDialog when there are changes", () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.serviceIdForm.patchValue({
        servicename: "test",
        description: "desc"
      });
      component.serviceIdForm.markAsDirty();

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
      component.serviceIdForm.patchValue({
        servicename: "test",
        description: "desc"
      });
      component.serviceIdForm.markAsDirty();
      dialogRefMock.close.mockClear();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(dialogRefMock.close).toHaveBeenCalled();
    });

    it("should close when user selects 'save-exit' and save succeeds", async () => {
      component.serviceIdForm.patchValue({
        servicename: "test",
        description: "desc"
      });
      component.serviceIdForm.markAsDirty();
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(true));

      dialogRefMock.close.mockClear();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(dialogRefMock.close).toHaveBeenCalled();
    });

    it("should NOT close when user selects 'save-exit' but save fails", async () => {
      component.serviceIdForm.patchValue({
        servicename: "test",
        description: "desc"
      });
      component.serviceIdForm.markAsDirty();
      serviceIdServiceMock.postServiceId = jest.fn().mockRejectedValue(new Error("Save failed"));
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(false));

      dialogRefMock.close.mockClear();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });

    it("should do nothing when user selects 'save-exit' but canSave is false", async () => {
      component.serviceIdForm.patchValue({ servicename: "" });
      component.serviceIdForm.markAsDirty();
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
      component.serviceIdForm.patchValue({
        servicename: "test",
        description: "desc"
      });
      component.serviceIdForm.markAsDirty();

      dialogRefMock.close.mockClear();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });
  });
});
