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
import { MachineresolverComponent } from "./machineresolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MachineresolverService } from "../../services/machineresolver/machineresolver.service";
import { MockMachineresolverService } from "../../../testing/mock-services/mock-machineresolver-service";
import { Component } from "@angular/core";
import { MatExpansionModule } from "@angular/material/expansion";

@Component({
  standalone: true,
  selector: "app-machineresolver-panel-new",
  template: ""
})
class MockMachineresolverPanelNewComponent {}

@Component({
  standalone: true,
  selector: "app-machineresolver-panel-edit",
  template: ""
})
class MockMachineresolverPanelEditComponent {}

describe("MachineresolverComponent", () => {
  let component: MachineresolverComponent;
  let fixture: ComponentFixture<MachineresolverComponent>;
  let machineresolverServiceMock: MockMachineresolverService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineresolverComponent, NoopAnimationsModule],
      providers: [{ provide: MachineresolverService, useClass: MockMachineresolverService }]
    })
      .overrideComponent(MachineresolverComponent, {
        set: {
          imports: [MockMachineresolverPanelNewComponent, MockMachineresolverPanelEditComponent, MatExpansionModule]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(MachineresolverComponent);
    component = fixture.componentInstance;
    machineresolverServiceMock = TestBed.inject(MachineresolverService) as unknown as MockMachineresolverService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should inject the machineresolver service", () => {
    expect(component.machineresolverService).toBeTruthy();
  });

  it("should show MockMachineresolverPanelNewComponent one time", () => {
    const compiled = fixture.nativeElement as HTMLElement;
    machineresolverServiceMock.machineresolvers.set([{}, {}] as any);
    fixture.detectChanges();
    const newPanels = compiled.querySelectorAll("app-machineresolver-panel-new");
    const editPanels = compiled.querySelectorAll("app-machineresolver-panel-edit");

    expect(newPanels.length).toBe(1);
    expect(editPanels.length).toBe(2);
  });

  describe("should show MockMachineresolverPanelEditComponent as many as there are machineresolvers", () => {
    it("when there are 0 machineresolvers", () => {
      const compiled = fixture.nativeElement as HTMLElement;
      machineresolverServiceMock.machineresolvers.set([]);
      fixture.detectChanges();
      const editPanels = compiled.querySelectorAll("app-machineresolver-panel-edit");

      expect(editPanels.length).toBe(0);
    });

    it("when there is 1 machineresolver", () => {
      const compiled = fixture.nativeElement as HTMLElement;
      machineresolverServiceMock.machineresolvers.set([{}] as any);
      fixture.detectChanges();
      const editPanels = compiled.querySelectorAll("app-machineresolver-panel-edit");

      expect(editPanels.length).toBe(1);
    });

    it("when there are 3 machineresolvers", () => {
      const compiled = fixture.nativeElement as HTMLElement;
      machineresolverServiceMock.machineresolvers.set([{}, {}, {}] as any);
      fixture.detectChanges();
      const editPanels = compiled.querySelectorAll("app-machineresolver-panel-edit");

      expect(editPanels.length).toBe(3);
    });
  });
});
