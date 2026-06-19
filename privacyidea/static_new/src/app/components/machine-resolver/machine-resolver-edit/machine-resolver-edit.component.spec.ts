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
import { MachineResolver, MachineResolverService } from "@services/machine-resolver/machine-resolver.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { MockNotificationService } from "@testing/mock-services";
import { MockMachineResolverService } from "@testing/mock-services/mock-machine-resolver-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { BehaviorSubject, of } from "rxjs";
import { MachineResolverEditComponent } from "./machine-resolver-edit.component";

class LocalMockMatDialog {
  result$ = of("save-exit");
  open = jest.fn().mockReturnValue({
    afterClosed: () => this.result$
  });
}

describe("MachineResolverEditComponent", () => {
  let component: MachineResolverEditComponent;
  let fixture: ComponentFixture<MachineResolverEditComponent>;
  let machineResolverServiceMock: MockMachineResolverService;
  let pendingChangesService: MockPendingChangesService;
  let dialog: LocalMockMatDialog;
  let router: Router;
  let paramMap$: BehaviorSubject<ParamMap>;

  async function setup(name: string | null): Promise<void> {
    dialog = new LocalMockMatDialog();
    paramMap$ = new BehaviorSubject<ParamMap>(convertToParamMap(name ? { name } : {}));
    await TestBed.configureTestingModule({
      imports: [MachineResolverEditComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineResolverService, useClass: MockMachineResolverService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: MatDialog, useValue: dialog },
        {
          provide: Router,
          useValue: { navigate: jest.fn(), navigateByUrl: jest.fn(), events: of(), url: "" }
        },
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$.asObservable() } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(MachineResolverEditComponent);
    component = fixture.componentInstance;
    machineResolverServiceMock = TestBed.inject(MachineResolverService) as unknown as MockMachineResolverService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  }

  describe("create mode", () => {
    beforeEach(async () => {
      await setup(null);
    });

    it("should create in new mode with default values", () => {
      expect(component).toBeTruthy();
      expect(component.isEditMode()).toBe(false);
      expect(component.currentMachineResolver().type).toBe("hosts");
    });

    it("should register pending-changes hooks and clear them on destroy", () => {
      expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerSave).toHaveBeenCalled();
      component.ngOnDestroy();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    });

    it("onResolvernameChange keeps data.resolver in sync", () => {
      component.onResolvernameChange("res1");
      expect(component.currentMachineResolver().resolvername).toBe("res1");
      expect(component.currentMachineResolver().data.resolver).toBe("res1");
      expect(component.isEdited()).toBe(true);
    });

    it("nameHasPatternError flags invalid characters", () => {
      component.onResolvernameChange("inv alid");
      expect(component.nameHasPatternError()).toBe(true);
      expect(component.canSaveMachineResolver()).toBe(false);
    });

    it("onMachineResolverTypeChange resets data for the new type", () => {
      component.onResolvernameChange("res1");
      component.onMachineResolverTypeChange("ldap");
      expect(component.currentMachineResolver().type).toBe("ldap");
      expect(component.currentMachineResolver().data).toEqual({ resolver: "res1", type: "ldap" });
    });

    it("saveMachineResolver posts and navigates back on success", async () => {
      component.onResolvernameChange("res1");
      const saved = await component.saveMachineResolver();
      expect(saved).toBe(true);
      expect(machineResolverServiceMock.postTestMachineResolver).toHaveBeenCalled();
      expect(machineResolverServiceMock.postMachineResolver).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER);
    });

    it("onCancel navigates back without dialog when unedited", () => {
      component.onCancel();
      expect(dialog.open).not.toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER);
    });
  });

  describe("edit mode", () => {
    const existing: MachineResolver = {
      resolvername: "hosts1",
      type: "hosts",
      data: { resolver: "hosts1", type: "hosts" }
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

    it("posts an update and navigates back on save", async () => {
      component.onNewData({ resolver: "hosts1", type: "hosts", filename: "/etc/hosts" } as never);
      const saved = await component.saveMachineResolver();
      expect(saved).toBe(true);
      expect(machineResolverServiceMock.postMachineResolver).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER);
    });
  });
});
