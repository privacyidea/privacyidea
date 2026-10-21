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
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { SmtpService } from "@services/smtp/smtp.service";
import { MockDialogService } from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockSmtpService } from "@testing/mock-services/mock-smtp-service";
import { of } from "rxjs";
import { NewSmtpServerComponent } from "./new-smtp-server.component";

const flush = async (fixture: ComponentFixture<unknown>) => {
  fixture.detectChanges();
  await fixture.whenStable();
  fixture.detectChanges();
};

const checkboxInput = (fixture: ComponentFixture<unknown>, label: string): HTMLInputElement => {
  const checkbox = Array.from(fixture.nativeElement.querySelectorAll("mat-checkbox") as NodeListOf<HTMLElement>).find(
    (el) => el.textContent?.includes(label)
  );
  return checkbox!.querySelector("input") as HTMLInputElement;
};

const clickCheckbox = async (fixture: ComponentFixture<unknown>, label: string) => {
  checkboxInput(fixture, label).click();
  await flush(fixture);
};

const inputOf = (fixture: ComponentFixture<unknown>, placeholder: string): HTMLInputElement =>
  fixture.nativeElement.querySelector(`input[placeholder="${placeholder}"]`) as HTMLInputElement;

const typeInto = async (fixture: ComponentFixture<unknown>, input: HTMLInputElement, value: string) => {
  input.value = value;
  input.dispatchEvent(new Event("input"));
  await flush(fixture);
};

describe("NewSmtpServerComponent", () => {
  let smtpServiceMock: MockSmtpService;
  let router: Router;
  let pendingChangesService: MockPendingChangesService;
  let dialogService: MockDialogService;

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe("Common tests", () => {
    let component: NewSmtpServerComponent;
    let fixture: ComponentFixture<NewSmtpServerComponent>;

    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [NewSmtpServerComponent],
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          provideRouter([]),
          { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({})) } },
          { provide: SmtpService, useClass: MockSmtpService },
          { provide: PendingChangesService, useClass: MockPendingChangesService },
          { provide: DialogService, useClass: MockDialogService }
        ]
      }).compileComponents();

      smtpServiceMock = TestBed.inject(SmtpService) as unknown as MockSmtpService;
      pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
      dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
      router = TestBed.inject(Router);
      jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
      fixture = TestBed.createComponent(NewSmtpServerComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();
    });

    it("should create", () => {
      expect(component).toBeTruthy();
    });

    it("should initialize form for create mode", () => {
      expect(component.isEditMode()).toBe(false);
      expect(component.smtpModel().identifier).toBe("");
    });

    it("should initialize form with S/MIME fields", () => {
      expect(component.smtpModel().certificate).toBe("");
      expect(component.smtpModel().private_key).toBe("");
      expect(component.smtpModel().private_key_password).toBe("");
      expect(component.smtpModel().smime).toBe(false);
      expect(component.smtpModel().dont_send_on_error).toBe(false);
    });

    it("should show TLS when server does not start with smtps:", () => {
      component.smtpModel.update((m) => ({ ...m, server: "smtp.example.com" }));
      expect(component.showTLS()).toBe(true);

      component.smtpModel.update((m) => ({ ...m, server: "smtps://smtp.example.com" }));
      expect(component.showTLS()).toBe(false);
    });

    it("should call save when form is valid", async () => {
      component.smtpModel.update((m) => ({
        ...m,
        identifier: "test",
        server: "smtp.test.com",
        port: 25,
        sender: "test@test.com",
        timeout: 5
      }));

      const success = await component.save();

      expect(success).toBe(true);
      expect(smtpServiceMock.postSmtpServer).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
    });

    it("Save should handle error", async () => {
      component.smtpModel.update((m) => ({
        ...m,
        identifier: "test",
        server: "smtp.test.com",
        port: 25,
        sender: "test@test.com",
        timeout: 5
      }));
      smtpServiceMock.postSmtpServer.mockRejectedValue(new Error("Save failed"));

      const success = await component.save();

      expect(success).toBe(false);
      expect(smtpServiceMock.postSmtpServer).toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should not call smtpService.postSmtpServer if the form is invalid", async () => {
      component.smtpModel.update((m) => ({
        ...m,
        identifier: "",
        server: "smtp.test.com",
        port: 25,
        sender: "test@test.com",
        timeout: 5
      }));
      expect(component.smtpForm().valid()).toBe(false);
      await component.save();
      expect(smtpServiceMock.postSmtpServer).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it.each(["send_test_email", ".", ".."])("rejects the reserved identifier %p", (identifier) => {
      component.smtpModel.update((m) => ({ ...m, identifier, server: "smtp.test.com", sender: "test@test.com" }));
      expect(
        component.smtpForm
          .identifier()
          .errors()
          .some((e) => e.kind === "reservedName")
      ).toBe(true);
      expect(component.smtpForm().valid()).toBe(false);
      expect(component.canSave).toBe(false);
    });

    it("should call test when form is valid", async () => {
      component.smtpModel.update((m) => ({
        ...m,
        identifier: "test",
        server: "smtp.test.com",
        port: 25,
        sender: "test@test.com",
        timeout: 5
      }));
      await component.test();
      expect(smtpServiceMock.testSmtpServer).toHaveBeenCalled();
    });

    it("should return true for hasChanges if form is dirty", async () => {
      await clickCheckbox(fixture, "S/MIME signing");
      expect(component.hasChanges).toBe(true);
    });

    it("should return false for hasChanges if form is pristine", () => {
      expect(component.smtpForm().dirty()).toBe(false);
      expect(component.hasChanges).toBe(false);
    });

    describe("onCancel", () => {
      let mockSaveExitDialogRef: { afterClosed: jest.Mock };

      beforeEach(() => {
        mockSaveExitDialogRef = {
          afterClosed: jest.fn()
        };
        dialogService.openDialog.mockReturnValue(
          mockSaveExitDialogRef as unknown as MatDialogRef<SaveAndExitDialogComponent>
        );
      });

      it("should navigate back directly when there are no changes", () => {
        component.onCancel();

        expect(dialogService.openDialog).not.toHaveBeenCalled();
        expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
      });

      it("should open SaveAndExitDialog when there are changes", async () => {
        mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
        await clickCheckbox(fixture, "Send mail from job queue");

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
        component.smtpModel.update((m) => ({
          ...m,
          identifier: "test",
          server: "smtp.test.com",
          port: 25,
          sender: "test@test.com",
          timeout: 5
        }));
        component.smtpForm().markAsDirty();

        component.onCancel();

        await new Promise((resolve) => setTimeout(resolve, 10));

        expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
        expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
      });

      it("should close when user selects 'save-exit' and save succeeds", async () => {
        component.smtpModel.update((m) => ({
          ...m,
          identifier: "test",
          server: "smtp.test.com",
          port: 25,
          sender: "test@test.com",
          timeout: 5
        }));
        component.smtpForm().markAsDirty();
        mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
        pendingChangesService.save.mockReturnValue(Promise.resolve(true));

        component.onCancel();

        await new Promise((resolve) => setTimeout(resolve, 100));

        expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
        expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
      });

      it("should NOT close when user selects 'save-exit' but save fails", async () => {
        component.smtpModel.update((m) => ({
          ...m,
          identifier: "test",
          server: "smtp.test.com",
          port: 25,
          sender: "test@test.com",
          timeout: 5
        }));
        component.smtpForm().markAsDirty();
        smtpServiceMock.postSmtpServer.mockRejectedValue(new Error("Save failed"));
        mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
        pendingChangesService.save.mockReturnValue(Promise.resolve(false));

        component.onCancel();

        await new Promise((resolve) => setTimeout(resolve, 100));

        expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
        expect(router.navigateByUrl).not.toHaveBeenCalled();
      });

      it("should do nothing when user selects 'save-exit' but canSave is false", async () => {
        component.smtpModel.update((m) => ({ ...m, identifier: "" }));
        component.smtpForm().markAsDirty();
        mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));

        component.onCancel();

        await new Promise((resolve) => setTimeout(resolve, 100));

        expect(pendingChangesService.save).not.toHaveBeenCalled();
        expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
        expect(router.navigateByUrl).not.toHaveBeenCalled();
      });

      it("should do nothing when user closes dialog without selecting an option", async () => {
        mockSaveExitDialogRef.afterClosed.mockReturnValue(of(undefined));
        component.smtpModel.update((m) => ({
          ...m,
          identifier: "test",
          server: "smtp.test.com",
          port: 25,
          sender: "test@test.com",
          timeout: 5
        }));
        component.smtpForm().markAsDirty();

        component.onCancel();

        await new Promise((resolve) => setTimeout(resolve, 10));

        expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
        expect(router.navigateByUrl).not.toHaveBeenCalled();
      });
    });

    describe("deleteServer", () => {
      let dialog: MockDialogService;
      let pending: MockPendingChangesService;
      let service: MockSmtpService;
      let navigateSpy: jest.SpyInstance;

      beforeEach(() => {
        dialog = TestBed.inject(DialogService) as unknown as MockDialogService;
        pending = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
        service = TestBed.inject(SmtpService) as unknown as MockSmtpService;
        navigateSpy = jest.spyOn(TestBed.inject(Router), "navigateByUrl").mockResolvedValue(true);
        component["editIdentifier"] = "smtp-server";
      });

      it("does nothing without an identifier", async () => {
        component["editIdentifier"] = null;
        await component.deleteServer();
        expect(dialog.confirmDelete).not.toHaveBeenCalled();
        expect(service.deleteSmtpServer).not.toHaveBeenCalled();
      });

      it("does not delete when the confirmation is cancelled", async () => {
        dialog.confirmDelete.mockResolvedValue(false);
        await component.deleteServer();
        expect(service.deleteSmtpServer).not.toHaveBeenCalled();
        expect(navigateSpy).not.toHaveBeenCalled();
      });

      it("deletes after confirmation and navigates back to the list", async () => {
        await component.deleteServer();
        expect(dialog.confirmDelete).toHaveBeenCalledWith(expect.objectContaining({ items: ["smtp-server"] }));
        expect(service.deleteSmtpServer).toHaveBeenCalledWith("smtp-server");
        expect(pending.clearAllRegistrations).toHaveBeenCalled();
        expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
      });

      it("stays on the page when the deletion fails", async () => {
        service.deleteSmtpServer.mockRejectedValue(new Error("delete failed"));
        await component.deleteServer();
        expect(pending.clearAllRegistrations).not.toHaveBeenCalled();
        expect(navigateSpy).not.toHaveBeenCalled();
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
        imports: [NewSmtpServerComponent],
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          provideRouter([]),
          {
            provide: ActivatedRoute,
            useValue: { paramMap: of(convertToParamMap({ identifier: editData.identifier })) }
          },
          {
            provide: SmtpService,
            useValue: { smtpServers: () => [editData], postSmtpServer: jest.fn(), testSmtpServer: jest.fn() }
          },
          { provide: PendingChangesService, useClass: MockPendingChangesService },
          { provide: DialogService, useClass: MockDialogService }
        ]
      }).compileComponents();

      editFixture = TestBed.createComponent(NewSmtpServerComponent);
      editComponent = editFixture.componentInstance;
      editFixture.detectChanges();
    });

    it("should disable identifier control when data is provided", () => {
      expect(editComponent.isEditMode()).toBe(true);
      expect(editComponent.smtpForm.identifier().disabled()).toBe(true);
      expect(editComponent.smtpModel().identifier).toBe("existing-id");
    });
  });
});

describe("NewSmtpServerComponent bound controls", () => {
  let fixture: ComponentFixture<NewSmtpServerComponent>;
  let component: NewSmtpServerComponent;
  let smtpService: MockSmtpService;

  const existing = {
    identifier: "smtp-1",
    server: "smtp.example.com",
    port: 587,
    timeout: 10,
    sender: "sender@example.com",
    tls: true,
    enqueue_job: false,
    smime: false,
    dont_send_on_error: false
  };

  const setup = async (identifier?: string) => {
    await TestBed.configureTestingModule({
      imports: [NewSmtpServerComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap(identifier ? { identifier } : {})) } },
        { provide: SmtpService, useClass: MockSmtpService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();
    smtpService = TestBed.inject(SmtpService) as unknown as MockSmtpService;
    smtpService.smtpServers.set([existing]);
    fixture = TestBed.createComponent(NewSmtpServerComponent);
    component = fixture.componentInstance;
    await flush(fixture);
  };

  describe("checkboxes", () => {
    beforeEach(async () => setup());

    it.each([
      ["Use StartTLS", "tls", false],
      ["Send mail from job queue", "enqueue_job", true],
      ["S/MIME signing", "smime", true],
      ["Don't send on signing error", "dont_send_on_error", true]
    ] as const)("%s writes %s to the model and marks the form dirty", async (label, field, expected) => {
      expect(component.hasChanges).toBe(false);
      await clickCheckbox(fixture, label);
      expect(component.smtpModel()[field]).toBe(expected);
      expect(component.smtpForm[field]().dirty()).toBe(true);
      expect(component.hasChanges).toBe(true);
    });

    it("shows a model change in the checkbox", async () => {
      component.smtpModel.update((m) => ({ ...m, smime: true }));
      await flush(fixture);
      expect(checkboxInput(fixture, "S/MIME signing").checked).toBe(true);
    });

    it("hides the StartTLS checkbox for an smtps server", async () => {
      component.smtpModel.update((m) => ({ ...m, server: "smtps://smtp.example.com" }));
      await flush(fixture);
      expect(fixture.nativeElement.textContent).not.toContain("Use StartTLS");
    });
  });

  describe("edit mode", () => {
    beforeEach(async () => setup("smtp-1"));

    it("keeps a checkbox edit when the server list is reloaded", async () => {
      await clickCheckbox(fixture, "S/MIME signing");
      expect(component.smtpModel().smime).toBe(true);

      smtpService.smtpServers.set([{ ...existing, smime: false, timeout: 99 }]);
      await flush(fixture);

      expect(component.smtpModel().smime).toBe(true);
      expect(component.smtpModel().timeout).toBe(10);
    });

    it("re-initializes from a reloaded list while the form is pristine", async () => {
      smtpService.smtpServers.set([{ ...existing, timeout: 99 }]);
      await flush(fixture);
      expect(component.smtpModel().timeout).toBe(99);
      expect(component.hasChanges).toBe(false);
    });

    it("marks the form dirty when a clear button empties a field", async () => {
      component.smtpModel.update((m) => ({ ...m, username: "user" }));
      await flush(fixture);
      expect(component.hasChanges).toBe(false);
      const clear = fixture.nativeElement
        .querySelector('input[placeholder="user@example.com"]')
        .closest("app-clearable-input")
        .querySelector("button") as HTMLButtonElement;
      clear.click();
      await flush(fixture);
      expect(component.smtpModel().username).toBe("");
      expect(component.smtpForm.username().dirty()).toBe(true);
      expect(component.hasChanges).toBe(true);
    });
  });

  describe("test recipient", () => {
    beforeEach(async () => {
      await setup();
      component.smtpModel.update((m) => ({ ...m, identifier: "test", server: "smtp.test.com", sender: "a@b.de" }));
      await flush(fixture);
    });

    it("leaves the server form pristine while the recipient is typed", async () => {
      const recipient = fixture.nativeElement.querySelector(
        "mat-form-field input:not([placeholder])"
      ) as HTMLInputElement;
      await typeInto(fixture, recipient, "rcpt@example.com");
      expect(component.recipientModel().recipient).toBe("rcpt@example.com");
      expect(component.smtpForm().dirty()).toBe(false);
      expect(component.hasChanges).toBe(false);
    });

    it("sends the recipient with the server settings and keeps it out of the saved server", async () => {
      component.recipientModel.set({ recipient: "rcpt@example.com" });
      await component.test();
      expect(smtpService.testSmtpServer).toHaveBeenCalledWith(
        expect.objectContaining({ server: "smtp.test.com", recipient: "rcpt@example.com" })
      );
      jest.spyOn(TestBed.inject(Router), "navigateByUrl").mockResolvedValue(true);
      await component.save();
      expect(smtpService.postSmtpServer).toHaveBeenCalledWith(
        expect.not.objectContaining({ recipient: expect.anything() })
      );
    });

    it("disables the test button while the server form is invalid", async () => {
      const button = () =>
        fixture.nativeElement.querySelector("button[mat-icon-button][matSuffix]") as HTMLButtonElement;
      expect(button().disabled).toBe(false);
      component.smtpModel.update((m) => ({ ...m, server: "" }));
      await flush(fixture);
      expect(button().disabled).toBe(true);
    });
  });

  describe("number inputs", () => {
    beforeEach(async () => setup());

    it.each([
      ["25", "port"],
      ["10", "timeout"]
    ] as const)("renders the parse message of the %s field once it is touched", async (placeholder, field) => {
      const input = inputOf(fixture, placeholder);
      jest.spyOn(input, "validity", "get").mockReturnValue({ badInput: true } as ValidityState);
      await typeInto(fixture, input, "");
      expect(
        component.smtpForm[field]()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["parse"]);
      expect(component.smtpForm().valid()).toBe(false);

      input.dispatchEvent(new Event("blur"));
      await flush(fixture);
      expect(fixture.nativeElement.textContent).toContain("Enter a valid number");
    });
  });
});
