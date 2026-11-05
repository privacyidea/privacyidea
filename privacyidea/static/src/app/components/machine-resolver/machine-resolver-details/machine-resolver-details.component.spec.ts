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
import { MatDialog } from "@angular/material/dialog";
import { ActivatedRoute, convertToParamMap, ParamMap, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import {
  MachineResolver,
  MachineResolverData,
  MachineResolverService
} from "@services/machine-resolver/machine-resolver.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { MockNotificationService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockMachineResolverService } from "@testing/mock-services/mock-machine-resolver-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { BehaviorSubject, Observable, of } from "rxjs";
import { MachineResolverDetailsComponent } from "./machine-resolver-details.component";

class LocalMockMatDialog {
  result$: Observable<string | boolean> = of("save-exit");
  open = jest.fn().mockReturnValue({
    afterClosed: () => this.result$
  });
}

describe("MachineResolverDetailsComponent", () => {
  let component: MachineResolverDetailsComponent;
  let fixture: ComponentFixture<MachineResolverDetailsComponent>;
  let machineResolverServiceMock: MockMachineResolverService;
  let pendingChangesService: MockPendingChangesService;
  let dialog: LocalMockMatDialog;
  let router: Router;
  let authServiceMock: MockAuthService;
  let paramMap$: BehaviorSubject<ParamMap>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const inputByPlaceholder = (placeholder: string) =>
    fixture.nativeElement.querySelector(`input[placeholder="${placeholder}"]`) as HTMLInputElement;
  const typeInto = async (el: HTMLInputElement, value: string) => {
    el.value = value;
    el.dispatchEvent(new Event("input"));
    await flush();
  };
  const nameInput = () => fixture.nativeElement.querySelector("app-clearable-input input") as HTMLInputElement;
  const typeName = (value: string) => typeInto(nameInput(), value);
  const typeFilename = (value: string) => typeInto(inputByPlaceholder("/etc/hosts"), value);
  const nameKinds = () =>
    component.nameForm
      .resolvername()
      .errors()
      .map((e) => e.kind);
  const errorTexts = () =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map((e) => (e as HTMLElement).textContent);

  async function setup(name: string | null): Promise<void> {
    dialog = new LocalMockMatDialog();
    paramMap$ = new BehaviorSubject<ParamMap>(convertToParamMap(name ? { name } : {}));
    await TestBed.configureTestingModule({
      imports: [MachineResolverDetailsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineResolverService, useClass: MockMachineResolverService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: MatDialog, useValue: dialog },
        {
          provide: Router,
          useValue: { navigate: jest.fn(), navigateByUrl: jest.fn(), events: of(), url: "" }
        },
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$.asObservable() } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(MachineResolverDetailsComponent);
    component = fixture.componentInstance;
    machineResolverServiceMock = TestBed.inject(MachineResolverService) as unknown as MockMachineResolverService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  }

  describe("create mode", () => {
    beforeEach(async () => {
      await setup(null);
    });

    async function fillValidHostsResolver(): Promise<void> {
      await typeName("res1");
      await typeFilename("/etc/hosts");
    }

    it("should create in new mode with default values", () => {
      expect(component).toBeTruthy();
      expect(component.isEditMode()).toBe(false);
      expect(component.currentMachineResolver().type).toBe("hosts");
    });

    it("cannot delete a machine resolver that does not exist yet", async () => {
      authServiceMock.actionAllowed.mockReturnValue(true);
      expect(component.canDeleteMachineResolver()).toBe(false);
      await component.deleteMachineResolver();
      expect(dialog.open).not.toHaveBeenCalled();
      expect(machineResolverServiceMock.deleteMachineResolver).not.toHaveBeenCalled();
    });

    it("should register pending-changes hooks and clear them on destroy", () => {
      expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerSave).toHaveBeenCalled();
      component.ngOnDestroy();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    });

    it("starts with an empty name that is required and cannot be saved", () => {
      expect(component.nameForm().valid()).toBe(false);
      expect(nameKinds()).toEqual(["required"]);
      expect(component.canSaveMachineResolver()).toBe(false);
      expect(component.isEdited()).toBe(false);
    });

    it("carries the typed name in the resolver to save and in its data", async () => {
      await typeName("res1");
      expect(component.nameForm.resolvername().value()).toBe("res1");
      expect(component.machineResolverToSave().resolvername).toBe("res1");
      expect(component.machineResolverToSave().data.resolver).toBe("res1");
      expect(component.isEdited()).toBe(true);
      expect(component.nameForm.resolvername().dirty()).toBe(true);
    });

    it("clears the name through the clear button and marks it dirty", async () => {
      await typeName("res1");
      component.clearName();
      await flush();
      expect(component.nameForm.resolvername().value()).toBe("");
      expect(nameInput().value).toBe("");
      expect(component.isEdited()).toBe(false);
    });

    it("rejects a name with invalid characters and renders the pattern message once touched", async () => {
      await typeName("inv alid");
      expect(nameKinds()).toEqual(["pattern"]);
      expect(component.canSaveMachineResolver()).toBe(false);
      expect(errorTexts()).toEqual([]);
      component.nameForm.resolvername().markAsTouched();
      await flush();
      expect(errorTexts().join(" ")).toContain("letters, digits and . _ - are allowed");
    });

    it.each(["test", ".", ".."])("rejects the reserved name %p and renders its message", async (name) => {
      await typeName(name);
      expect(nameKinds()).toEqual(["reservedName"]);
      expect(component.canSaveMachineResolver()).toBe(false);
      component.nameForm.resolvername().markAsTouched();
      await flush();
      expect(errorTexts().join(" ")).toContain(`Cannot be named "${name}"`);
    });

    it("renders the required message for an emptied name once touched", async () => {
      await typeName("a");
      await typeName("");
      component.nameForm.resolvername().markAsTouched();
      await flush();
      expect(errorTexts().join(" ")).toContain("Machine resolver name is required");
    });

    it("accepts a valid name but cannot save while the hosts tab has no filename", async () => {
      await typeName("res.1_-a");
      expect(nameKinds()).toEqual([]);
      expect(component.activeTab()).toBe(component.hostsTab());
      expect(component.canSaveMachineResolver()).toBe(false);
    });

    it("can save once the name is valid and the hosts tab has a filename", async () => {
      await typeName("res1");
      await typeFilename("/etc/hosts");
      expect(component.canSaveMachineResolver()).toBe(true);
      const saveButton = fixture.nativeElement.querySelector(".action-button-primary") as HTMLButtonElement;
      expect(saveButton.disabled).toBe(false);
    });

    it("keeps the save button disabled while the tab is invalid", async () => {
      await typeName("res1");
      const saveButton = fixture.nativeElement.querySelector(".action-button-primary") as HTMLButtonElement;
      expect(saveButton.disabled).toBe(true);
    });

    it("feeds the typed filename of the tab into the data to save", async () => {
      await typeName("res1");
      await typeFilename("/etc/hosts");
      expect(component.currentMachineResolver().data).toEqual({ resolver: "", type: "hosts", filename: "/etc/hosts" });
      expect(component.machineResolverToSave()).toEqual({
        resolvername: "res1",
        type: "hosts",
        data: { resolver: "res1", type: "hosts", filename: "/etc/hosts" }
      });
    });

    it("is not edited once the typed filename is cleared again", async () => {
      await typeFilename("/etc/hosts");
      expect(component.isEdited()).toBe(true);

      await typeFilename("");

      expect(component.isEdited()).toBe(false);
    });

    it("reads the validity of the ldap tab once the type is switched", async () => {
      await typeName("res1");
      component.onMachineResolverTypeChange("ldap");
      await flush();
      expect(component.activeTab()).toBe(component.ldapTab());
      expect(component.canSaveMachineResolver()).toBe(false);
      component
        .ldapTab()
        ?.model.update((m) => ({ ...m, LDAPURI: "ldap://x", LDAPBASE: "b", BINDDN: "d", BINDPW: "p" }));
      await flush();
      expect(component.canSaveMachineResolver()).toBe(true);
      expect(component.currentMachineResolver().data).toEqual(
        expect.objectContaining({ type: "ldap", LDAPURI: "ldap://x", LDAPBASE: "b", BINDDN: "d", BINDPW: "p" })
      );
    });

    it("disables the save button when the type is switched from a valid hosts tab to an empty ldap tab", async () => {
      await fillValidHostsResolver();
      const saveButton = fixture.nativeElement.querySelector(".action-button-primary") as HTMLButtonElement;
      expect(saveButton.disabled).toBe(false);
      component.onMachineResolverTypeChange("ldap");
      await flush();
      expect(component.canSaveMachineResolver()).toBe(false);
      expect(saveButton.disabled).toBe(true);
      component.onMachineResolverTypeChange("hosts");
      await flush();
      expect(saveButton.disabled).toBe(true);
      await typeFilename("/etc/hosts");
      expect(saveButton.disabled).toBe(false);
    });

    it("has no active tab and cannot save for an unknown type", async () => {
      component.currentMachineResolver.update((r) => ({ ...r, type: "unknown" }));
      await typeName("res1");
      expect(component.activeTab()).toBeUndefined();
      expect(component.canSaveMachineResolver()).toBe(false);
      expect(fixture.nativeElement.textContent).toContain("Unknown machine resolver type: unknown");
    });

    it("onMachineResolverTypeChange resets data for the new type", async () => {
      await typeName("res1");
      component.onMachineResolverTypeChange("ldap");
      expect(component.currentMachineResolver().type).toBe("ldap");
      expect(component.currentMachineResolver().data).toEqual({ resolver: "res1", type: "ldap" });
    });

    it("selecting a type in the select resets the data", async () => {
      const select = fixture.nativeElement.querySelector("mat-select") as HTMLElement;
      select.click();
      await flush();
      const options = Array.from(document.querySelectorAll("mat-option")) as HTMLElement[];
      options.find((o) => o.textContent?.trim() === "ldap")?.click();
      await flush();
      expect(component.currentMachineResolver().type).toBe("ldap");
    });

    it("saveMachineResolver posts and navigates back on success", async () => {
      await fillValidHostsResolver();
      const saved = await component.saveMachineResolver();
      expect(saved).toBe(true);
      expect(machineResolverServiceMock.postTestMachineResolver).toHaveBeenCalled();
      expect(machineResolverServiceMock.postMachineResolver).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER);
    });

    it("saveMachineResolver posts the name in the resolver and in its data", async () => {
      await fillValidHostsResolver();
      await component.saveMachineResolver();
      const expected = {
        resolvername: "res1",
        type: "hosts",
        data: { resolver: "res1", type: "hosts", filename: "/etc/hosts" }
      };
      expect(machineResolverServiceMock.postTestMachineResolver).toHaveBeenCalledWith(expected);
      expect(machineResolverServiceMock.postMachineResolver).toHaveBeenCalledWith(expected);
    });

    it("saveMachineResolver refuses an invalid form, touches the fields and posts nothing", async () => {
      const saved = await component.saveMachineResolver();
      await flush();
      expect(saved).toBe(false);
      expect(component.nameForm.resolvername().touched()).toBe(true);
      expect(component.hostsTab()?.hostsForm.filename().touched()).toBe(true);
      expect(errorTexts().join(" ")).toContain("Machine resolver name is required");
      expect(errorTexts().join(" ")).toContain("Resolver filename is required");
      expect(machineResolverServiceMock.postTestMachineResolver).not.toHaveBeenCalled();
      expect(machineResolverServiceMock.postMachineResolver).not.toHaveBeenCalled();
    });

    it("saveMachineResolver refuses an invalid form of an unknown type", async () => {
      component.currentMachineResolver.update((r) => ({ ...r, type: "unknown" }));
      await typeName("res1");
      expect(await component.saveMachineResolver()).toBe(false);
      expect(machineResolverServiceMock.postMachineResolver).not.toHaveBeenCalled();
    });

    it("the pending changes hooks read the aggregate validity and the edit state", async () => {
      const valid = pendingChangesService.registerValidChanges.mock.calls[0][0] as () => boolean;
      const changed = pendingChangesService.registerHasChanges.mock.calls[0][0] as () => boolean;
      expect(valid()).toBe(false);
      expect(changed()).toBe(false);
      await fillValidHostsResolver();
      expect(valid()).toBe(true);
      expect(changed()).toBe(true);
    });

    it("onCancel offers save-and-exit only for a valid form", async () => {
      await typeName("res1");
      dialog.result$ = of("cancel");
      await component.onCancel();
      expect(dialog.open).toHaveBeenLastCalledWith(
        expect.anything(),
        expect.objectContaining({
          data: expect.objectContaining({ allowSaveExit: false, saveExitDisabled: true })
        })
      );
      await typeFilename("/etc/hosts");
      await component.onCancel();
      expect(dialog.open).toHaveBeenLastCalledWith(
        expect.anything(),
        expect.objectContaining({
          data: expect.objectContaining({ allowSaveExit: true, saveExitDisabled: false })
        })
      );
    });

    it("onCancel does not save on save-exit while the form is invalid", async () => {
      await typeName("res1");
      dialog.result$ = of("save-exit");
      await component.onCancel();
      expect(machineResolverServiceMock.postMachineResolver).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("onCancel navigates back without dialog when unedited", () => {
      component.onCancel();
      expect(dialog.open).not.toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER);
    });

    it("saveMachineResolver proceeds after confirming a test failure", async () => {
      await fillValidHostsResolver();
      machineResolverServiceMock.postTestMachineResolver.mockRejectedValueOnce(new Error("post-failed"));
      dialog.result$ = of(true);
      const saved = await component.saveMachineResolver();
      expect(saved).toBe(true);
      expect(dialog.open).toHaveBeenCalled();
      expect(machineResolverServiceMock.postMachineResolver).toHaveBeenCalled();
    });

    it("saveMachineResolver aborts when the test-failure dialog is dismissed", async () => {
      await fillValidHostsResolver();
      machineResolverServiceMock.postTestMachineResolver.mockRejectedValueOnce(new Error("post-failed"));
      dialog.result$ = of(false);
      const saved = await component.saveMachineResolver();
      expect(saved).toBe(false);
      expect(machineResolverServiceMock.postMachineResolver).not.toHaveBeenCalled();
    });

    it("saveMachineResolver aborts on a non test-failure error without prompting", async () => {
      await fillValidHostsResolver();
      machineResolverServiceMock.postTestMachineResolver.mockRejectedValueOnce(new Error("boom"));
      const saved = await component.saveMachineResolver();
      expect(saved).toBe(false);
      expect(dialog.open).not.toHaveBeenCalled();
      expect(machineResolverServiceMock.postMachineResolver).not.toHaveBeenCalled();
    });

    it("saveMachineResolver returns false when the update post fails", async () => {
      await fillValidHostsResolver();
      machineResolverServiceMock.postMachineResolver.mockRejectedValueOnce(new Error("boom"));
      const saved = await component.saveMachineResolver();
      expect(saved).toBe(false);
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });
  });

  describe("edit mode", () => {
    const existing: MachineResolver = {
      resolvername: "hosts1",
      type: "hosts",
      data: { resolver: "hosts1", type: "hosts" }
    };

    const allowWrite = async () => {
      authServiceMock.authData.update((data) => ({ ...data!, rights: ["mresolverwrite"] }));
      await flush();
    };

    beforeEach(async () => {
      await setup("hosts1");
      machineResolverServiceMock.machineResolverResource.set({ result: { value: { hosts1: existing } } } as never);
      machineResolverServiceMock.machineResolvers.set([existing]);
      fixture.detectChanges();
    });

    it("loads the selected machine resolver", () => {
      expect(component.isEditMode()).toBe(true);
      expect(component.currentMachineResolver().resolvername).toBe("hosts1");
      expect(component.isEdited()).toBe(false);
    });

    it("fills the name form with the loaded name and shows no name input", async () => {
      expect(component.nameForm.resolvername().value()).toBe("hosts1");
      expect(component.nameForm().valid()).toBe(true);
      expect(component.nameForm().dirty()).toBe(false);
      expect(fixture.nativeElement.querySelector("app-clearable-input")).toBeNull();
      expect(fixture.nativeElement.querySelector(".blue-base")?.textContent).toBe("hosts1");
    });

    it("is edited and can be saved after the filename is typed", async () => {
      await allowWrite();
      expect(component.isEdited()).toBe(false);
      await typeFilename("/etc/hosts");
      expect(component.isEdited()).toBe(true);
      expect(component.canSaveMachineResolver()).toBe(true);
    });

    it("is not edited once the filename is typed back to the loaded value", async () => {
      const withFile: MachineResolver = {
        resolvername: "hosts1",
        type: "hosts",
        data: { resolver: "hosts1", type: "hosts", filename: "/etc/hosts" } as MachineResolverData
      };
      machineResolverServiceMock.machineResolvers.set([withFile]);
      machineResolverServiceMock.machineResolverResource.set({ result: { value: { hosts1: withFile } } } as never);
      await allowWrite();
      expect(component.isEdited()).toBe(false);

      await typeFilename("/etc/other");
      expect(component.isEdited()).toBe(true);
      const saveButton = fixture.nativeElement.querySelector(".action-button-primary") as HTMLButtonElement;
      expect(saveButton.disabled).toBe(false);
      await typeFilename("/etc/hosts");

      expect(component.isEdited()).toBe(false);
      expect(saveButton.disabled).toBe(true);
    });

    it("is not edited once the filename is typed back for a resolver stored as the backend returns it", async () => {
      const stored: MachineResolver = {
        resolvername: "hosts1",
        type: "hosts",
        data: { filename: "/etc/hosts" } as unknown as MachineResolverData
      };
      machineResolverServiceMock.machineResolvers.set([stored]);
      machineResolverServiceMock.machineResolverResource.set({ result: { value: { hosts1: stored } } } as never);
      await allowWrite();
      expect(component.isEdited()).toBe(false);

      await typeFilename("/etc/other");
      expect(component.isEdited()).toBe(true);
      await typeFilename("/etc/hosts");

      expect(component.isEdited()).toBe(false);
      expect((fixture.nativeElement.querySelector(".action-button-primary") as HTMLButtonElement).disabled).toBe(true);
    });

    it("is not edited once a filename typed over an empty one is cleared again", async () => {
      await typeFilename("/etc/hosts");
      expect(component.isEdited()).toBe(true);

      await typeFilename("");

      expect(component.isEdited()).toBe(false);
    });

    it("does not count the name in the data as an edit", () => {
      expect(component.originalMachineResolver().data.resolver).toBe("hosts1");
      expect(component.machineResolverToSave().data.resolver).toBe("hosts1");
      expect(component.isEdited()).toBe(false);
    });

    it("cannot save a loaded resolver whose hosts tab has no filename", async () => {
      await allowWrite();
      expect(component.activeTab()?.isValid()).toBe(false);
      expect(component.canSaveMachineResolver()).toBe(false);
    });

    it("re-syncs the name, the data and the tab when the resource reloads without edits", async () => {
      await allowWrite();
      const reloaded: MachineResolver = {
        resolvername: "hosts1",
        type: "hosts",
        data: { resolver: "hosts1", type: "hosts", filename: "/reloaded" } as never
      };
      machineResolverServiceMock.machineResolvers.set([reloaded]);
      machineResolverServiceMock.machineResolverResource.set({ result: { value: { hosts1: reloaded } } } as never);
      await flush();
      expect(component.currentMachineResolver().data).toEqual(reloaded.data);
      expect(inputByPlaceholder("/etc/hosts").value).toBe("/reloaded");
      expect(component.isEdited()).toBe(false);
    });

    it("keeps unsaved edits when the resource reloads", async () => {
      await allowWrite();
      await typeFilename("/mine");
      const reloaded: MachineResolver = {
        resolvername: "hosts1",
        type: "hosts",
        data: { resolver: "hosts1", type: "hosts", filename: "/reloaded" } as never
      };
      machineResolverServiceMock.machineResolvers.set([reloaded]);
      machineResolverServiceMock.machineResolverResource.set({ result: { value: { hosts1: reloaded } } } as never);
      await flush();
      expect(inputByPlaceholder("/etc/hosts").value).toBe("/mine");
      expect(component.isEdited()).toBe(true);
    });

    it("disables the tab and keeps the form valid without the mresolverwrite right", async () => {
      await allowWrite();
      authServiceMock.authData.update((data) => ({ ...data!, rights: [] }));
      await flush();
      expect(component.canMakeChanges()).toBe(false);
      expect(inputByPlaceholder("/etc/hosts").disabled).toBe(true);
      expect(component.activeTab()?.isValid()).toBe(true);
    });

    it("gates the edit toggle behind the mresolverwrite right", () => {
      authServiceMock.actionAllowed.mockReturnValue(false);
      expect(component.authService.actionAllowed("mresolverwrite")).toBe(false);
      authServiceMock.actionAllowed.mockReturnValue(true);
      expect(component.authService.actionAllowed("mresolverwrite")).toBe(true);
    });

    it("posts an update and navigates back on save", async () => {
      component.onNewData({ resolver: "hosts1", type: "hosts", filename: "/etc/hosts" } as never);
      const saved = await component.saveMachineResolver();
      expect(saved).toBe(true);
      expect(machineResolverServiceMock.postMachineResolver).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER);
    });

    it("onCancel discards changes and navigates back", async () => {
      component.onNewData({ resolver: "hosts1", type: "hosts", filename: "/changed" } as never);
      expect(component.isEdited()).toBe(true);
      jest.mocked(router.navigateByUrl).mockClear();
      pendingChangesService.clearAllRegistrations.mockClear();
      dialog.result$ = of("discard");
      await component.onCancel();
      expect(machineResolverServiceMock.postMachineResolver).not.toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER);
    });

    it("onCancel saves and navigates back on save-exit", async () => {
      component.onNewData({ resolver: "hosts1", type: "hosts", filename: "/changed" } as never);
      dialog.result$ = of("save-exit");
      await component.onCancel();
      expect(machineResolverServiceMock.postMachineResolver).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER);
    });

    it("onCancel logs an error when the dialog rejects", async () => {
      const errorSpy = jest.spyOn(console, "error").mockImplementation(() => undefined);
      component.onNewData({ resolver: "hosts1", type: "hosts", filename: "/changed" } as never);
      dialog.result$ = new Observable((subscriber) => subscriber.error(new Error("dialog boom")));
      await component.onCancel();
      expect(errorSpy).toHaveBeenCalledWith("Error handling unsaved changes dialog:", expect.any(Error));
      errorSpy.mockRestore();
    });

    it("allows deleting only with the mresolverdelete right", () => {
      authServiceMock.authData.update((data) => ({ ...data!, rights: ["mresolverwrite"] }));
      expect(component.canDeleteMachineResolver()).toBe(false);
      authServiceMock.authData.update((data) => ({ ...data!, rights: ["mresolverdelete"] }));
      expect(component.canDeleteMachineResolver()).toBe(true);
    });

    describe("deleteMachineResolver", () => {
      beforeEach(() => {
        jest.mocked(router.navigateByUrl).mockClear();
        pendingChangesService.clearAllRegistrations.mockClear();
      });

      it("deletes after confirmation and navigates back", async () => {
        dialog.result$ = of(true);
        await component.deleteMachineResolver();
        expect(dialog.open).toHaveBeenCalled();
        expect(machineResolverServiceMock.deleteMachineResolver).toHaveBeenCalledWith("hosts1");
        expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
        expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER);
      });

      it("does nothing when the dialog is dismissed", async () => {
        dialog.result$ = of(false);
        await component.deleteMachineResolver();
        expect(machineResolverServiceMock.deleteMachineResolver).not.toHaveBeenCalled();
        expect(router.navigateByUrl).not.toHaveBeenCalled();
      });

      it("stays on the page when the deletion fails", async () => {
        dialog.result$ = of(true);
        machineResolverServiceMock.deleteMachineResolver.mockRejectedValue(new Error("delete failed"));
        await component.deleteMachineResolver();
        expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
        expect(router.navigateByUrl).not.toHaveBeenCalled();
      });
    });
  });

  describe("loading a missing machine resolver", () => {
    it("notifies and navigates back when the resolver does not exist", async () => {
      await setup("missing");
      const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
      machineResolverServiceMock.machineResolverResource.set({ result: { value: {} } } as never);
      machineResolverServiceMock.machineResolvers.set([]);
      fixture.detectChanges();
      expect(notificationService.error).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER);
    });
  });
});
