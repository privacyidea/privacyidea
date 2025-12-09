/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { MachineResolverComponent } from "./machineResolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MachineResolverService } from "../../services/machineResolver/machineResolver.service";
import { MockMachineResolverService } from "../../../testing/mock-services/mock-machine-resolver-service";
import { Component } from "@angular/core";
import { MatExpansionModule } from "@angular/material/expansion";

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

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineResolverComponent, NoopAnimationsModule],
      providers: [{ provide: MachineResolverService, useClass: MockMachineResolverService }]
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
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should inject the machineResolver service", () => {
    expect(component.machineResolverService).toBeTruthy();
  });

  it("should show MockMachineResolverPanelNewComponent one time", () => {
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
      const compiled = fixture.nativeElement as HTMLElement;
      machineResolverServiceMock.machineResolvers.set([]);
      fixture.detectChanges();
      const editPanels = compiled.querySelectorAll("app-machine-resolver-panel-edit");

      expect(editPanels.length).toBe(0);
    });

    it("when there is 1 machineResolver", () => {
      const compiled = fixture.nativeElement as HTMLElement;
      machineResolverServiceMock.machineResolvers.set([{}] as any);
      fixture.detectChanges();
      const editPanels = compiled.querySelectorAll("app-machine-resolver-panel-edit");

      expect(editPanels.length).toBe(1);
    });

    it("when there are 3 machineResolvers", () => {
      const compiled = fixture.nativeElement as HTMLElement;
      machineResolverServiceMock.machineResolvers.set([{}, {}, {}] as any);
      fixture.detectChanges();
      const editPanels = compiled.querySelectorAll("app-machine-resolver-panel-edit");

      expect(editPanels.length).toBe(3);
    });
  });
});
