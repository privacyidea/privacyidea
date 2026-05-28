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
import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatExpansionModule } from "@angular/material/expansion";
import { AuthService } from "@services/auth/auth.service";
import { MachineResolverService } from "@services/machine-resolver/machine-resolver.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockMachineResolverService } from "@testing/mock-services/mock-machine-resolver-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MachineResolverComponent } from "./machine-resolver.component";

@Component({
  standalone: true,
  selector: "app-machine-resolver-panel-new",
  template: ""
})
class MockMachineResolverPanelNewComponent {}

@Component({
  standalone: true,
  selector: "app-machine-resolver-panel-edit",
  template: ""
})
class MockMachineResolverPanelEditComponent {}

describe("MachineResolverComponent", () => {
  let component: MachineResolverComponent;
  let fixture: ComponentFixture<MachineResolverComponent>;
  let machineResolverServiceMock: MockMachineResolverService;
  let authServiceMock: MockAuthService;
  let pendingChangesService: MockPendingChangesService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineResolverComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineResolverService, useClass: MockMachineResolverService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: PendingChangesService, useClass: MockPendingChangesService }
      ]
    })
      .overrideComponent(MachineResolverComponent, {
        set: {
          imports: [MockMachineResolverPanelNewComponent, MockMachineResolverPanelEditComponent, MatExpansionModule]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(MachineResolverComponent);
    component = fixture.componentInstance;
    machineResolverServiceMock = TestBed.inject(MachineResolverService) as unknown as MockMachineResolverService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should inject the machineResolver service", () => {
    expect(component.machineResolverService).toBeTruthy();
  });

  it("should show MockMachineResolverPanelNewComponent one time", () => {
    authServiceMock.actionAllowed.mockReturnValue(true);
    const compiled = fixture.nativeElement as HTMLElement;
    machineResolverServiceMock.machineResolvers.set([{}, {}] as any);
    fixture.detectChanges();
    const newPanels = compiled.querySelectorAll("app-machine-resolver-panel-new");
    const editPanels = compiled.querySelectorAll("app-machine-resolver-panel-edit");

    expect(newPanels.length).toBe(1);
    expect(editPanels.length).toBe(2);
  });

  describe("should show MockMachineResolverPanelEditComponent as many as there are machineResolvers", () => {
    it("when there are 0 machineResolvers", () => {
      authServiceMock.actionAllowed.mockReturnValue(true);
      const compiled = fixture.nativeElement as HTMLElement;
      machineResolverServiceMock.machineResolvers.set([]);
      fixture.detectChanges();
      const editPanels = compiled.querySelectorAll("app-machine-resolver-panel-edit");

      expect(editPanels.length).toBe(0);
    });

    it("when there is 1 machineResolver", () => {
      authServiceMock.actionAllowed.mockReturnValue(true);
      const compiled = fixture.nativeElement as HTMLElement;
      machineResolverServiceMock.machineResolvers.set([{}] as any);
      fixture.detectChanges();
      const editPanels = compiled.querySelectorAll("app-machine-resolver-panel-edit");

      expect(editPanels.length).toBe(1);
    });

    it("when there are 3 machineResolvers", () => {
      authServiceMock.actionAllowed.mockReturnValue(true);
      const compiled = fixture.nativeElement as HTMLElement;
      machineResolverServiceMock.machineResolvers.set([{}, {}, {}] as any);
      fixture.detectChanges();
      const editPanels = compiled.querySelectorAll("app-machine-resolver-panel-edit");

      expect(editPanels.length).toBe(3);
    });
  });

  it("ngOnDestroy clears all pending-changes registrations", () => {
    component.ngOnDestroy();
    expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
  });
});
