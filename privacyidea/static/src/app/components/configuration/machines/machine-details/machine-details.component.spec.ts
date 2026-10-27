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
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { ActivatedRoute, convertToParamMap, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ApplicationService } from "@services/application/application.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { MachineService } from "@services/machine/machine.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { TokenService } from "@services/token/token.service";
import {
  MockApplicationService,
  MockContentService,
  MockDialogService,
  MockMachineService,
  MockPendingChangesService,
  MockRouter,
  MockTokenService
} from "@testing/mock-services";
import { of } from "rxjs";
import { MachineDetailsComponent } from "./machine-details.component";

describe("MachineDetailsComponent", () => {
  let component: MachineDetailsComponent;
  let fixture: ComponentFixture<MachineDetailsComponent>;
  let machineServiceMock: MockMachineService;
  let dialogServiceMock: MockDialogService;
  let contentServiceMock: MockContentService;
  let pendingChangesService: MockPendingChangesService;

  const mockMachine = { id: 1, hostname: ["host1"], ip: "1.1.1.1", resolver_name: "res1" };

  beforeEach(async () => {
    // Inject machine data via history state (the way the component reads it)
    window.history.pushState({ machine: mockMachine }, "");

    await TestBed.configureTestingModule({
      imports: [MachineDetailsComponent],
      providers: [
        { provide: MachineService, useClass: MockMachineService },
        { provide: ApplicationService, useClass: MockApplicationService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: ContentService, useClass: MockContentService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: Router, useClass: MockRouter },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: convertToParamMap({ id: "1" }),
              queryParamMap: convertToParamMap({ resolver: "res1" })
            }
          }
        }
      ]
    }).compileComponents();

    machineServiceMock = TestBed.inject(MachineService) as unknown as MockMachineService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

    // Override getMachineTokens to return specific test data
    machineServiceMock.getMachineTokens.mockReturnValue(
      of({
        result: {
          value: [
            {
              id: 10,
              serial: "S1",
              application: "ssh",
              type: "sshkey",
              hostname: "host1",
              options: { user: "alice", service_id: "svc1" }
            }
          ]
        }
      })
    );
    machineServiceMock.machines.set([mockMachine]);
    contentServiceMock.routeUrl.set(ROUTE_PATHS.CONFIGURATION_MACHINES);
    jest.spyOn(machineServiceMock, "postAssignMachineToToken");

    fixture = TestBed.createComponent(MachineDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should load tokens on init", () => {
    expect(machineServiceMock.getMachineTokens).toHaveBeenCalledWith({ machineid: 1, resolver: "res1" });
    expect(component.dataSource.data.length).toBe(1);
    expect(component.dataSource.data[0].serial).toBe("S1");
  });

  it("should detach token after confirmation", async () => {
    const token = component.dataSource.data[0];
    component.detachToken(token);
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({
        component: SimpleConfirmationDialogComponent
      })
    );
    // Simulate user confirming the dialog
    const dialogRef = dialogServiceMock.openDialog.mock.results[0].value;
    dialogRef.close(true);
    await Promise.resolve();
    expect(machineServiceMock.deleteTokenById).toHaveBeenCalledWith("S1", "ssh", "10");
  });

  describe("attach block", () => {
    let tokenServiceMock: MockTokenService;
    let el: HTMLElement;

    const flush = async () => {
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };
    const serialInput = () => el.querySelector<HTMLInputElement>("input[matInput]")!;
    const attachButton = () => el.querySelector<HTMLButtonElement>("button.action-button-primary")!;
    const errorKinds = (field: typeof component.attachForm.serial) =>
      field()
        .errors()
        .map((e) => e.kind);

    beforeEach(() => {
      tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;
      tokenServiceMock.tokenOptions.set(["S1", "S2", "T3"]);
      el = fixture.nativeElement;
    });

    afterEach(() => {
      document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
    });

    it("starts invalid with both fields required and an empty application", () => {
      expect(component.attachModel()).toEqual({ serial: "", application: "" });
      expect(component.attachForm().valid()).toBe(false);
      expect(errorKinds(component.attachForm.serial)).toEqual(["required"]);
      expect(errorKinds(component.attachForm.application)).toEqual(["required"]);
      expect(attachButton().disabled).toBe(true);
    });

    it("enables the button once serial and application are set", async () => {
      component.attachForm.serial().value.set("S2");
      expect(attachButton().disabled).toBe(true);
      component.attachForm.application().value.set("ssh");
      await flush();
      expect(component.attachForm().valid()).toBe(true);
      expect(attachButton().disabled).toBe(false);
    });

    it("writes typed text to the model and mirrors it into selectedToken", async () => {
      await flush();
      const input = serialInput();
      input.value = "S1";
      input.dispatchEvent(new Event("input"));
      await flush();
      expect(component.attachModel().serial).toBe("S1");
      expect(component.attachForm.serial().dirty()).toBe(true);
      expect(tokenServiceMock.selectedToken()).toBe("S1");
    });

    it("mirrors a programmatic serial change into selectedToken", async () => {
      component.attachModel.update((m) => ({ ...m, serial: "T3" }));
      await flush();
      expect(tokenServiceMock.selectedToken()).toBe("T3");
    });

    it("writes the picked autocomplete option to the field", async () => {
      await flush();
      const input = serialInput();
      input.focus();
      input.dispatchEvent(new Event("focusin"));
      input.value = "S";
      input.dispatchEvent(new Event("input"));
      await flush();
      const options = Array.from(document.querySelectorAll<HTMLElement>("mat-option"));
      expect(options.map((o) => o.textContent?.trim())).toEqual(["S1", "S2"]);
      options[1].click();
      await flush();
      expect(component.attachModel().serial).toBe("S2");
      expect(component.attachForm.serial().valid()).toBe(true);
      expect(tokenServiceMock.selectedToken()).toBe("S2");
    });

    it("writes the picked application to the model", async () => {
      await flush();
      const selects = fixture.debugElement.queryAll(By.directive(MatSelect));
      const select = selects[selects.length - 1].componentInstance as MatSelect;
      select.open();
      await flush();
      document.querySelector<HTMLElement>("mat-option")!.click();
      await flush();
      expect(component.attachModel().application).toBe("ssh");
      expect(component.attachForm.application().dirty()).toBe(true);
    });

    it("should attach token", () => {
      component.attachModel.set({ serial: "S2", application: "ssh" });
      component.attachToken();
      expect(machineServiceMock.postAssignMachineToToken).toHaveBeenCalledWith({
        serial: "S2",
        application: "ssh",
        machineid: 1,
        resolver: "res1"
      });
    });

    it("does not attach while the form is invalid", () => {
      component.attachModel.set({ serial: "S2", application: "" });
      component.attachToken();
      component.attachModel.set({ serial: "", application: "ssh" });
      component.attachToken();
      expect(machineServiceMock.postAssignMachineToToken).not.toHaveBeenCalled();
    });

    it("does not attach without machine data", () => {
      component.data.set(undefined);
      component.attachModel.set({ serial: "S2", application: "ssh" });
      component.attachToken();
      expect(machineServiceMock.postAssignMachineToToken).not.toHaveBeenCalled();
    });

    it("resets the form, clears selectedToken and reloads the tokens after attaching", async () => {
      component.attachForm.serial().value.set("S2");
      component.attachForm.application().value.set("ssh");
      component.attachForm.serial().markAsTouched();
      await flush();
      machineServiceMock.getMachineTokens.mockClear();
      component.attachToken();
      await flush();
      expect(component.attachModel()).toEqual({ serial: "", application: "" });
      expect(component.attachForm().touched()).toBe(false);
      expect(component.attachForm().dirty()).toBe(false);
      expect(tokenServiceMock.selectedToken()).toBe("");
      expect(machineServiceMock.getMachineTokens).toHaveBeenCalledTimes(1);
    });
  });

  it("should save edited options", () => {
    const token = component.dataSource.data[0];
    component.startEdit(token);
    component.editedOptions[token.id] = { user: "bob", service_id: "svc2" };
    component.saveOptions(token);
    const machine = component.data();
    expect(machineServiceMock.postTokenOption).toHaveBeenCalledWith(
      token.hostname,
      String(machine!.id),
      machine!.resolver_name,
      token.serial,
      token.application,
      String(token.id),
      { user: "bob", service_id: "svc2" }
    );
  });

  it("should call tokenSelected when token is clicked", () => {
    component.onTokenClick("S1");
    expect(contentServiceMock.tokenSelected).toHaveBeenCalledWith("S1");
  });

  it("should call machineResolverSelected when machine resolver is clicked", () => {
    component.onMachineResolverClick("res1");
    expect(contentServiceMock.machineResolverSelected).toHaveBeenCalledWith("res1");
  });

  it("should register hasChanges based on editingIds in ngOnInit", () => {
    expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
    const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;

    expect(fn()).toBe(false);

    const token = component.dataSource.data[0];
    component.startEdit(token);
    expect(fn()).toBe(true);
  });

  it("ngOnDestroy clears all pending-changes registrations", () => {
    component.ngOnDestroy();
    expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
  });

  it("renders a multi-valued hostname as a comma-joined string", () => {
    component.data.set({ id: 2, hostname: ["a.example", "b.example"], ip: "1.1.1.1", resolver_name: "res1" });
    fixture.detectChanges();
    const title: HTMLElement = fixture.nativeElement.querySelector(".machine-title .h3-color");
    expect(title.textContent?.trim()).toBe("a.example, b.example");
  });
});
