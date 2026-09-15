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
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { Observable } from "rxjs";

import { TokenHotpMachineAssignDialogComponent } from "./token-hotp-machine-attach-dialog";

import { PiResponse } from "@app/app.component";
import { MachineService, MachineServiceInterface } from "@services/machine/machine.service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";

type PostAssignArgs = Parameters<MachineServiceInterface["postAssignMachineToToken"]>[0];

class MockMachineService {
  subscribed = false;
  lastArgs: PostAssignArgs | null = null;

  postAssignMachineToToken = jest.fn().mockImplementation((args: PostAssignArgs) => {
    this.lastArgs = args;
    return new Observable<PiResponse<number>>((observer) => {
      this.subscribed = true;
      observer.next(MockPiResponse.fromValue<number>(0) as unknown as PiResponse<number>);
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
      imports: [TokenHotpMachineAssignDialogComponent, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: { tokenSerial: "SERIAL-1" } },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MachineService, useValue: machineService }
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
    expect(component.countValue()).toBe("100");
    expect(component.roundsValue()).toBe("10000");
    expect(component.isFormValid()).toBe(true);
  });

  it("countForm: min(10) validator works", () => {
    component.countValue.set("9");
    expect(component.countForm().valid()).toBe(false);
    expect(
      component
        .countForm()
        .errors()
        .some((e) => e.kind === "min")
    ).toBe(true);

    component.countValue.set("10");
    expect(component.countForm().valid()).toBe(true);
  });

  it("roundsForm: min(1000) validator works", () => {
    component.roundsValue.set("999");
    expect(component.roundsForm().valid()).toBe(false);
    expect(
      component
        .roundsForm()
        .errors()
        .some((e) => e.kind === "min")
    ).toBe(true);

    component.roundsValue.set("1000");
    expect(component.roundsForm().valid()).toBe(true);
  });

  it("onAssign: does nothing when form invalid", () => {
    component.countValue.set("0");
    component.roundsValue.set("100");

    component.onAssign();

    expect(machineService.postAssignMachineToToken).not.toHaveBeenCalled();
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it("onAssign: posts payload, subscribes to request, and closes dialog with the same Observable", () => {
    component.countValue.set("123");
    component.roundsValue.set("4567");

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

    const returned$ = (machineService.postAssignMachineToToken as jest.Mock).mock.results[0]
      .value as Observable<PiResponse<number>>;
    expect(dialogRef.close).toHaveBeenCalledWith(returned$);
  });

  it("close: closes with undefined", () => {
    (component as unknown as { close: (value?: unknown) => void }).close();
    expect(dialogRef.close).toHaveBeenCalledWith(undefined);
  });

  it("close: closes with given value", () => {
    (component as unknown as { close: (value?: unknown) => void }).close("test-value");
    expect(dialogRef.close).toHaveBeenCalledWith("test-value");
  });
});
