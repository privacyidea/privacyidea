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
import { HostsMachineResolverData, MachineResolverData } from "@services/machine-resolver/machine-resolver.service";
import { MachineResolverHostsTabComponent } from "./machine-resolver-hosts-tab.component";

describe("MachineResolverHostsTabComponent", () => {
  let component: MachineResolverHostsTabComponent;
  let fixture: ComponentFixture<MachineResolverHostsTabComponent>;
  let emitted: MachineResolverData[];

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const filenameInput = () => fixture.nativeElement.querySelector("input") as HTMLInputElement;
  const type = async (value: string) => {
    filenameInput().value = value;
    filenameInput().dispatchEvent(new Event("input"));
    await flush();
  };
  const setData = async (data: MachineResolverData) => {
    fixture.componentRef.setInput("machineResolverData", data);
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineResolverHostsTabComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(MachineResolverHostsTabComponent);
    component = fixture.componentInstance;
    emitted = [];
    component.newData.subscribe((data) => emitted.push(data));
    fixture.componentRef.setInput("canEdit", true);
    fixture.componentRef.setInput("machineResolverData", { type: "hosts", filename: "testFileName", resolver: "test" });
    await flush();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("shows the filename of the data and emits nothing on init", () => {
    expect(filenameInput().value).toBe("testFileName");
    expect(component.model().filename).toBe("testFileName");
    expect(emitted).toEqual([]);
  });

  it("re-seeds the form when the data changes and still emits nothing", async () => {
    await setData({ type: "hosts", filename: "/etc/other", resolver: "test" } as HostsMachineResolverData);
    expect(filenameInput().value).toBe("/etc/other");
    expect(emitted).toEqual([]);
  });

  describe("validity", () => {
    it("is valid with a filename", () => {
      expect(component.isValid()).toBe(true);
    });

    it.each(["", " ", "  \t"])("is invalid for the filename %p", async (value) => {
      await type(value);
      expect(component.isValid()).toBe(false);
      expect(
        component.hostsForm
          .filename()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["required"]);
    });

    it("is invalid when the data holds no filename", async () => {
      await setData({ type: "hosts", resolver: "test" });
      expect(component.isValid()).toBe(false);
    });

    it("is valid while the form is disabled, even without a filename", async () => {
      fixture.componentRef.setInput("canEdit", false);
      await setData({ type: "hosts", resolver: "test" });
      expect(filenameInput().disabled).toBe(true);
      expect(component.isValid()).toBe(true);
    });

    it("renders the required message only after the field is touched", async () => {
      await type("");
      expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();
      await component.touchAll();
      await flush();
      expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("required");
    });
  });

  describe("emitted data", () => {
    it("emits the typed filename merged into the data of the input", async () => {
      await type("/etc/hosts");
      expect(emitted).toEqual([{ type: "hosts", filename: "/etc/hosts", resolver: "test" }]);
    });

    it("emits an emptied filename that the data held", async () => {
      await type("");
      expect(emitted).toEqual([{ type: "hosts", filename: "", resolver: "test" }]);
    });

    it("keeps the filename absent while the data held none and the field is empty", async () => {
      await setData({ type: "hosts", resolver: "test" });
      await type("a");
      expect(emitted).toEqual([{ type: "hosts", filename: "a", resolver: "test" }]);
      await setData({ type: "hosts", resolver: "test" });
      await type("");
      expect(emitted).toHaveLength(1);
    });

    it("emits once per edit when the parent feeds the emitted data back", async () => {
      await type("/first");
      await setData(emitted[0]);
      expect(emitted).toHaveLength(1);
      await type("/second");
      expect(emitted).toHaveLength(2);
      expect(emitted[1]).toEqual({ type: "hosts", filename: "/second", resolver: "test" });
    });

    it("marks the typed field dirty", async () => {
      await type("/etc/hosts");
      expect(component.hostsForm.filename().dirty()).toBe(true);
    });
  });
});
