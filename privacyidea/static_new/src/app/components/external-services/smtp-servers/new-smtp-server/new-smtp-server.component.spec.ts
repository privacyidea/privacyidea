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
import { NewSmtpServerComponent } from "./new-smtp-server.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";
import { SmtpService } from "../../../../services/smtp/smtp.service";
import { MockSmtpService } from "../../../../../testing/mock-services/mock-smtp-service";
import { ContentService } from "../../../../services/content/content.service";
import { ROUTE_PATHS } from "../../../../route_paths";
import { signal } from "@angular/core";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { MockPendingChangesService } from "../../../../../testing/mock-services/mock-pending-changes-service";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { MockDialogService } from "../../../../../testing/mock-services";

describe("NewSmtpServerComponent", () => {
  let smtpServiceMock: any;
  let dialogRefMock: any;
  let dialogMock: any;
  let contentServiceMock: any;
  let pendingChangesService: MockPendingChangesService;
  let dialogService: MockDialogService;

  beforeEach(() => {
    dialogRefMock = {
      disableClose: false,
      backdropClick: jest.fn().mockReturnValue(of()),
      keydownEvents: jest.fn().mockReturnValue(of()),
      close: jest.fn()
    };

    dialogMock = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of(true) })
    };

    contentServiceMock = {
      routeUrl: signal(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP)
    };
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe("Common tests", () => {
    let component: NewSmtpServerComponent;
    let fixture: ComponentFixture<NewSmtpServerComponent>;

    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [NewSmtpServerComponent, NoopAnimationsModule],
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: MAT_DIALOG_DATA, useValue: null },
          { provide: MatDialogRef, useValue: dialogRefMock },
          { provide: SmtpService, useClass: MockSmtpService },
          { provide: ContentService, useValue: contentServiceMock },
          { provide: PendingChangesService, useClass: MockPendingChangesService },
          { provide: DialogService, useClass: MockDialogService },
        ]
      }).overrideComponent(NewSmtpServerComponent, {
        add: {
          providers: [
            { provide: MatDialog, useValue: dialogMock }
          ]
        }
      }).compileComponents();

      smtpServiceMock = TestBed.inject(SmtpService);
      pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
      dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
      fixture = TestBed.createComponent(NewSmtpServerComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();
    });

    it("should create", () => {
      expect(component).toBeTruthy();
    });

    it("should initialize form for create mode", () => {
      expect(component.isEditMode).toBe(false);
      expect(component.smtpForm.get("identifier")?.value).toBe("");
    });

    it("should initialize form with S/MIME fields", () => {
      expect(component.smtpForm.contains("certificate")).toBe(true);
      expect(component.smtpForm.contains("private_key")).toBe(true);
      expect(component.smtpForm.contains("private_key_password")).toBe(true);
      expect(component.smtpForm.contains("smime")).toBe(true);
      expect(component.smtpForm.contains("dont_send_on_error")).toBe(true);

      expect(component.smtpForm.get("smime")?.value).toBe(false);
      expect(component.smtpForm.get("dont_send_on_error")?.value).toBe(false);
    });

    it("should show TLS when server does not start with smtps:", () => {
      component.smtpForm.patchValue({ server: "smtp.example.com" });
      expect(component.showTLS).toBe(true);

      component.smtpForm.patchValue({ server: "smtps://smtp.example.com" });
      expect(component.showTLS).toBe(false);
    });

    it("should call save when form is valid", async () => {
      component.smtpForm.patchValue({
        identifier: "test",
        server: "smtp.test.com",
        port: 25,
        sender: "test@test.com",
        timeout: 5
      });

      const success = await component.save();

      expect(success).toBe(true);
      expect(smtpServiceMock.postSmtpServer).toHaveBeenCalled();
      expect(dialogRefMock.close).toHaveBeenCalledWith(true);
    });

    it("Save should handle error", async () => {
      component.smtpForm.patchValue({
        identifier: "test",
        server: "smtp.test.com",
        port: 25,
        sender: "test@test.com",
        timeout: 5
      });
      smtpServiceMock.postSmtpServer.mockRejectedValue(new Error("Save failed"));
      // Clear any previous calls to close from setup
      dialogRefMock.close.mockClear();

      const success = await component.save();

      expect(success).toBe(false);
      expect(smtpServiceMock.postSmtpServer).toHaveBeenCalled();
      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });

    it("should not call smtpService.postSmtpServer if the form is invalid", async () => {
      component.smtpForm.patchValue({
        identifier: "", // Invalid
        server: "smtp.test.com",
        port: 25,
        sender: "test@test.com",
        timeout: 5
      });
      expect(component.smtpForm.valid).toBe(false);
      await component.save();
      expect(smtpServiceMock.postSmtpServer).not.toHaveBeenCalled();
      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });

    it("should call test when form is valid", async () => {
      component.smtpForm.patchValue({
        identifier: "test",
        server: "smtp.test.com",
        port: 25,
        sender: "test@test.com",
        timeout: 5
      });
      await component.test();
      expect(smtpServiceMock.testSmtpServer).toHaveBeenCalled();
    });

    it("should return true for hasChanges if form is dirty", () => {
      component.smtpForm.get("server")?.markAsDirty();
      expect(component.hasChanges).toBe(true);
    });

    it("should return false for hasChanges if form is pristine", () => {
      expect(component.smtpForm.pristine).toBe(true);
      expect(component.hasChanges).toBe(false);
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
        component.smtpForm.patchValue({
          identifier: "test",
          server: "smtp.test.com",
          port: 25,
          sender: "test@test.com",
          timeout: 5
        });
        component.smtpForm.markAsDirty();

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
        component.smtpForm.patchValue({
          identifier: "test",
          server: "smtp.test.com",
          port: 25,
          sender: "test@test.com",
          timeout: 5
        });
        component.smtpForm.markAsDirty();
        dialogRefMock.close.mockClear();

        component.onCancel();

        await new Promise(resolve => setTimeout(resolve, 10));

        expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
        expect(dialogRefMock.close).toHaveBeenCalled();
      });

      it("should close when user selects 'save-exit' and save succeeds", async () => {
        component.smtpForm.patchValue({
          identifier: "test",
          server: "smtp.test.com",
          port: 25,
          sender: "test@test.com",
          timeout: 5
        });
        component.smtpForm.markAsDirty();
        mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
        pendingChangesService.save.mockReturnValue(Promise.resolve(true));

        dialogRefMock.close.mockClear();

        component.onCancel();

        await new Promise(resolve => setTimeout(resolve, 100));

        expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
        expect(dialogRefMock.close).toHaveBeenCalled();
      });

      it("should NOT close when user selects 'save-exit' but save fails", async () => {
        component.smtpForm.patchValue({
          identifier: "test",
          server: "smtp.test.com",
          port: 25,
          sender: "test@test.com",
          timeout: 5
        });
        component.smtpForm.markAsDirty();
        smtpServiceMock.postSmtpServer.mockRejectedValue(new Error("Save failed"));
        mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
        pendingChangesService.save.mockReturnValue(Promise.resolve(false));

        dialogRefMock.close.mockClear();

        component.onCancel();

        await new Promise(resolve => setTimeout(resolve, 100));

        expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
        expect(dialogRefMock.close).not.toHaveBeenCalled();
      });

      it("should do nothing when user selects 'save-exit' but canSave is false", async () => {
        component.smtpForm.patchValue({ identifier: "" });
        component.smtpForm.markAsDirty();
        mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));

        dialogRefMock.close.mockClear();

        component.onCancel();

        await new Promise(resolve => setTimeout(resolve, 100));

        expect(pendingChangesService.save).not.toHaveBeenCalled();
        expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
        expect(dialogRefMock.close).not.toHaveBeenCalled();
      });

      it("should do nothing when user closes dialog without selecting an option", async () => {
        mockSaveExitDialogRef.afterClosed.mockReturnValue(of(undefined));
        component.smtpForm.patchValue({
          identifier: "test",
          server: "smtp.test.com",
          port: 25,
          sender: "test@test.com",
          timeout: 5
        });
        component.smtpForm.markAsDirty();

        dialogRefMock.close.mockClear();

        component.onCancel();

        await new Promise(resolve => setTimeout(resolve, 10));

        expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
        expect(dialogRefMock.close).not.toHaveBeenCalled();
      });
    });
  });

  describe("Edit mode", () => {
    let editFixture: ComponentFixture<NewSmtpServerComponent>;
    let editComponent: NewSmtpServerComponent;

    beforeEach(async () => {
      const editData = {
        identifier: "existing-id",
        server: "smtp.example.com",
        sender: "sender@example.com",
        tls: true,
        enqueue_job: false
      };

      await TestBed.configureTestingModule({
        imports: [NewSmtpServerComponent, NoopAnimationsModule],
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: MAT_DIALOG_DATA, useValue: editData },
          { provide: MatDialogRef, useValue: dialogRefMock },
          { provide: SmtpService, useClass: MockSmtpService },
          { provide: ContentService, useValue: contentServiceMock }
        ]
      }).overrideComponent(NewSmtpServerComponent, {
        add: {
          providers: [
            { provide: MatDialog, useValue: dialogMock }
          ]
        }
      }).compileComponents();

      editFixture = TestBed.createComponent(NewSmtpServerComponent);
      editComponent = editFixture.componentInstance;
      editFixture.detectChanges();
    });

    it("should disable identifier control when data is provided", () => {
      expect(editComponent.isEditMode).toBe(true);
      expect(editComponent.smtpForm.get("identifier")?.disabled).toBe(true);
      expect(editComponent.smtpForm.get("identifier")?.value).toBe("existing-id");
    });
  });
});
