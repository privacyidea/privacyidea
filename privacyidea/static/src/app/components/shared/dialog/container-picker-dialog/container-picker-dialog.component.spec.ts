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
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { AuthService } from "@services/auth/auth.service";
import { ContainerDetailData, ContainerService } from "@services/container/container.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockAuthService, MockContainerService } from "@testing/mock-services";
import { ContainerPickerDialogComponent } from "./container-picker-dialog.component";

describe("ContainerPickerDialogComponent", () => {
  let component: ContainerPickerDialogComponent;
  let fixture: ComponentFixture<ContainerPickerDialogComponent>;
  let dialogRef: MockMatDialogRef<ContainerPickerDialogComponent, string>;
  let containerServiceMock: MockContainerService;
  let authServiceMock: MockAuthService;

  const setup = async () => {
    TestBed.resetTestingModule();
    dialogRef = new MockMatDialogRef<ContainerPickerDialogComponent, string>();

    await TestBed.configureTestingModule({
      imports: [ContainerPickerDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: {} },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    containerServiceMock = TestBed.inject(ContainerService) as unknown as MockContainerService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authServiceMock.actionAllowed.mockReturnValue(true);
    fixture = TestBed.createComponent(ContainerPickerDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  const addAction = () => component.confirmActions()[0];

  const container = (serial: string, owner?: string): ContainerDetailData =>
    ({
      serial,
      type: "generic",
      realms: [],
      states: [],
      tokens: [],
      users: owner ? [{ user_name: owner, user_realm: "defrealm", user_resolver: "res", user_id: "1" }] : []
    }) as ContainerDetailData;

  const checkbox = (): HTMLElement | null => fixture.nativeElement.querySelector("mat-checkbox");

  const warning = (): HTMLElement | null => fixture.nativeElement.querySelector(".inline-warning");

  /** Lets the backend return `serials`, optionally with details, and types `typed` into the field. */
  const pick = (typed: string, serials: string[], details: ContainerDetailData[] = []) => {
    containerServiceMock.pickableContainerDetails.set(details);
    containerServiceMock.pickableContainers.set(serials);
    component.setContainerSerial(typed);
    fixture.detectChanges();
  };

  it("opens the container list while it lives and closes it again on destroy", async () => {
    await setup();

    expect(containerServiceMock.containerPickerFilter()).toBe("");

    fixture.destroy();

    expect(containerServiceMock.containerPickerFilter()).toBeNull();
  });

  it("hands what was typed to the service so the backend filters the list", async () => {
    await setup();

    component.setContainerSerial("CONT");

    expect(containerServiceMock.containerPickerFilter()).toBe("CONT");
  });

  it.each<{ name: string; typed: string | null }>([
    { name: "a serial that no container has", typed: "Cff" },
    { name: "nothing typed", typed: null }
  ])("keeps Add disabled for $name", async ({ typed }) => {
    await setup();
    containerServiceMock.pickableContainers.set(["CONT0001"]);

    if (typed !== null) component.setContainerSerial(typed);

    expect(addAction().disabled).toBe(true);
  });

  it("enables Add for a serial the backend returned and passes it on trimmed", async () => {
    await setup();
    containerServiceMock.pickableContainers.set(["CONT0001"]);

    component.setContainerSerial("  CONT0001  ");

    expect(addAction().disabled).toBe(false);
    expect(addAction().value.containerSerial).toBe("CONT0001");
  });

  it("offers the containers of the user as shortcut buttons and takes the serial of a clicked one", async () => {
    await setup();
    containerServiceMock.userContainerSerials.set(["CONT0001", "SMPH0002"]);
    fixture.detectChanges();

    const shortcuts = Array.from(
      fixture.nativeElement.querySelectorAll(".container-picker-buttons button")
    ) as HTMLButtonElement[];
    expect(shortcuts.map((button) => button.textContent?.trim())).toEqual(["folder CONT0001", "folder SMPH0002"]);

    shortcuts[0].click();

    expect(component.containerSerial()).toBe("CONT0001");
    expect(containerServiceMock.containerPickerFilter()).toBe("CONT0001");
  });

  it("accepts a container of the user before the filtered list has arrived", async () => {
    await setup();
    containerServiceMock.userContainerSerials.set(["CONT0001"]);
    containerServiceMock.pickableContainers.set([]);

    component.setContainerSerial("CONT0001");

    expect(addAction().disabled).toBe(false);
  });

  it.each<{ name: string; allowed: boolean; checkboxShown: boolean }>([
    { name: "offers to assign a container that has no owner yet, checked by default", allowed: true, checkboxShown: true },
    { name: "hides the assignment when the admin may not assign container users", allowed: false, checkboxShown: false }
  ])("$name", async ({ allowed, checkboxShown }) => {
    await setup();
    authServiceMock.actionAllowed.mockReturnValue(allowed);

    pick("CONT0001", ["CONT0001"], [container("CONT0001")]);

    expect(checkbox() !== null).toBe(checkboxShown);
    if (allowed) expect(component.assignToUser()).toBe(true);
    expect(addAction().value).toEqual({ containerSerial: "CONT0001", assignToUser: allowed, previousOwner: null });
  });

  it("warns about the current owner, offers to move the container and drops the move once unchecked", async () => {
    await setup();
    pick("CONT0001", ["CONT0001"], [container("CONT0001", "otheruser")]);

    expect(warning()?.textContent).toContain("otheruser");
    expect(warning()?.textContent).toContain("will be moved");
    expect(checkbox()).not.toBeNull();
    expect(addAction().value).toEqual({
      containerSerial: "CONT0001",
      assignToUser: true,
      previousOwner: { username: "otheruser", realm: "defrealm" }
    });

    component.assignToUser.set(false);
    fixture.detectChanges();

    expect(warning()?.textContent).not.toContain("will be moved");
    expect(addAction().value.assignToUser).toBe(false);
  });

  it("offers neither warning nor assignment for a container of the user", async () => {
    await setup();
    containerServiceMock.userContainerSerials.set(["CONT0001"]);

    pick("CONT0001", ["CONT0001"], [container("CONT0001", "root")]);

    expect(warning()).toBeNull();
    expect(checkbox()).toBeNull();
  });

  it.each<{ name: string; typed: string; serials: string[]; expected: string[] }>([
    { name: "drops the suggestion that only repeats what is already in the field", typed: "SMPH00004476", serials: ["SMPH00004476"], expected: [] },
    { name: "keeps the suggestions while more than one container matches", typed: "SMPH0", serials: ["SMPH00004476", "SMPH00015931"], expected: ["SMPH00004476", "SMPH00015931"] }
  ])("$name", async ({ typed, serials, expected }) => {
    await setup();

    pick(typed, serials);

    expect(component["suggestions"]()).toEqual(expected);
  });

  it("closes with the chosen serial", async () => {
    await setup();
    containerServiceMock.pickableContainers.set(["CONT0001"]);
    component.setContainerSerial("CONT0001");

    component.onAction(addAction().value);

    expect(dialogRef.close).toHaveBeenCalledWith({
      containerSerial: "CONT0001",
      assignToUser: false,
      previousOwner: null
    });
  });
});
