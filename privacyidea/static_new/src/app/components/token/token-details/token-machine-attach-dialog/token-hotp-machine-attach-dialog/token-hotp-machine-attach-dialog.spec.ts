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
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { Observable } from "rxjs";

import { TokenHotpMachineAssignDialogComponent } from "./token-hotp-machine-attach-dialog";
import "@angular/localize/init";

class MockMachineService {
  subscribed = false;
  lastArgs: any = null;

  postAssignMachineToToken = jest.fn().mockImplementation((args: any) => {
    this.lastArgs = args;
    return new Observable((observer) => {
      this.subscribed = true;
      observer.next({ ok: true });
      observer.complete();
    });
  });
}

describe("TokenHotpMachineAssignDialogComponent", () => {
  let component: TokenHotpMachineAssignDialogComponent;
  let fixture: ComponentFixture<TokenHotpMachineAssignDialogComponent>;

  let dialogRef: { close: jest.Mock };
  let machineService: MockMachineService;

  beforeEach(async () => {
    dialogRef = { close: jest.fn() };
    machineService = new MockMachineService();

    await TestBed.configureTestingModule({
      imports: [TokenHotpMachineAssignDialogComponent, BrowserAnimationsModule, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: { tokenSerial: "SERIAL-1" } },
        { provide: MatDialogRef, useValue: dialogRef },
        {
          provide: (await import("../../../../../services/machine/machine.service")).MachineService,
          useValue: machineService
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenHotpMachineAssignDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("initializes with injected tokenSerial", () => {
    expect(component.tokenSerial).toBe("SERIAL-1");
  });

  it("form defaults are valid (count=100, rounds=10000)", () => {
    expect(component.countControl.value).toBe(100);
    expect(component.roundsControl.value).toBe(10000);
    expect(component.formGroup.valid).toBe(true);
  });

  it("countControl: min(10) validator works", () => {
    component.countControl.setValue(9);
    expect(component.countControl.invalid).toBe(true);
    expect(component.countControl.hasError("min")).toBe(true);

    component.countControl.setValue(10);
    expect(component.countControl.valid).toBe(true);
  });

  it("roundsControl: min(1000) validator works", () => {
    component.roundsControl.setValue(999);
    expect(component.roundsControl.invalid).toBe(true);
    expect(component.roundsControl.hasError("min")).toBe(true);

    component.roundsControl.setValue(1000);
    expect(component.roundsControl.valid).toBe(true);
  });

  it("onAssign: does nothing when form invalid", () => {
    component.countControl.setValue(0);
    component.roundsControl.setValue(100);

    component.onAssign();

    expect(machineService.postAssignMachineToToken).not.toHaveBeenCalled();
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it("onAssign: posts payload, subscribes to request, and closes dialog with the same Observable", () => {
    component.countControl.setValue(123);
    component.roundsControl.setValue(4567);

    component.onAssign();

    expect(machineService.postAssignMachineToToken).toHaveBeenCalledTimes(1);
    expect(machineService.lastArgs).toEqual({
      application: "offline",
      count: 123,
      machineid: 0,
      resolver: "",
      rounds: 4567,
      serial: "SERIAL-1"
    });

    expect(machineService.subscribed).toBe(true);

    const returned$ = (machineService.postAssignMachineToToken as jest.Mock).mock.results[0].value as Observable<any>;
    expect(dialogRef.close).toHaveBeenCalledWith(returned$);
  });

  it("onCancel: closes with null", () => {
    component.onCancel();
    expect(dialogRef.close).toHaveBeenCalledWith(null);
  });

  describe("machineValidator", () => {
    it("returns {required:true} when value is falsy or string", () => {
      const ctrl1 = { value: null } as any;
      const ctrl2 = { value: "" } as any;
      const ctrl3 = { value: "just-a-string" } as any;

      expect(component.machineValidator(ctrl1)).toEqual({ required: true });
      expect(component.machineValidator(ctrl2)).toEqual({ required: true });
      expect(component.machineValidator(ctrl3)).toEqual({ required: true });
    });

    it("returns {invalidMachine:true} when object is missing required fields", () => {
      const ctrl = { value: { id: 1, hostname: "h", ip: "1.2.3.4" } } as any;
      expect(component.machineValidator(ctrl)).toEqual({ invalidMachine: true });
    });

    it("returns null for a valid machine object", () => {
      const ctrl = {
        value: { id: 42, hostname: "host", ip: "10.0.0.1", resolver_name: "resolverA" }
      } as any;
      expect(component.machineValidator(ctrl)).toBeNull();
    });
  });
});
