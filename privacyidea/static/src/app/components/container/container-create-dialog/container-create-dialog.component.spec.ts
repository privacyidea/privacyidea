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

import { computed, Signal } from "@angular/core";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService, ContainerType } from "@services/container/container.service";
import { TokenService } from "@services/token/token.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockAuthService, MockContainerService, MockTokenService } from "@testing/mock-services";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { of, throwError } from "rxjs";
import { ContainerCreateDialogComponent, ContainerCreateDialogData } from "./container-create-dialog.component";

describe("ContainerCreateDialogComponent", () => {
  let component: ContainerCreateDialogComponent;
  let fixture: ComponentFixture<ContainerCreateDialogComponent>;
  let containerService: MockContainerService;
  let authService: MockAuthService;
  let dialogRef: MockMatDialogRef<ContainerCreateDialogComponent, string>;

  const typeOptions: ContainerType[] = [
    { containerType: "generic", description: "Generic container", token_types: ["hotp", "totp", "spass"] },
    { containerType: "smartphone", description: "Smartphone", token_types: ["hotp", "totp"] },
    { containerType: "yubikey", description: "Yubikey", token_types: ["certificate"] }
  ];

  const setup = async (data?: ContainerCreateDialogData, configure?: () => void) => {
    await TestBed.configureTestingModule({
      imports: [ContainerCreateDialogComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerService, useClass: MockContainerService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: data }
      ]
    }).compileComponents();

    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    (containerService as unknown as { containerTypeOptions: Signal<ContainerType[]> }).containerTypeOptions = computed(
      () => typeOptions
    );
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    dialogRef = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<ContainerCreateDialogComponent, string>;
    configure?.();

    fixture = TestBed.createComponent(ContainerCreateDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  it("should create", async () => {
    await setup();
    expect(component).toBeTruthy();
  });

  it("selects the default container type initially", async () => {
    await setup();
    // MockAuthService default container type is "generic"
    expect(component.selectedType()?.containerType).toBe("generic");
  });

  it("offers all container types when no token type is relevant", async () => {
    await setup();
    expect(component.typeOptions().map((option) => option.containerType)).toEqual(["generic", "smartphone", "yubikey"]);
  });

  it("only offers container types that support the relevant token type", async () => {
    await setup();
    containerService.compatibleWithSelectedTokenType.set("certificate");
    expect(component.typeOptions().map((option) => option.containerType)).toEqual(["yubikey"]);
    expect(component.selectedType()?.containerType).toBe("yubikey");
  });

  it("disables the create action when no container type is available", async () => {
    await setup();
    containerService.compatibleWithSelectedTokenType.set("unsupported-type");
    expect(component.typeOptions()).toEqual([]);
    expect(component.actions()[0].disabled).toBe(true);
  });

  it("creates a container and closes the dialog with the new serial", async () => {
    await setup();
    containerService.createContainer.mockReturnValue(of(MockPiResponse.fromValue({ container_serial: "CONT-NEW" })));

    component.description.set("my new container");
    component.onAction("create");

    expect(containerService.createContainer).toHaveBeenCalledWith({
      type: "generic",
      description: "my new container"
    });
    expect(dialogRef.close).toHaveBeenCalledWith("CONT-NEW");
  });

  it("stays open and allows retrying when the creation fails", async () => {
    await setup();
    containerService.createContainer.mockReturnValue(throwError(() => new Error("failed")));

    component.onAction("create");

    expect(dialogRef.close).not.toHaveBeenCalled();
    expect(component.isCreating()).toBe(false);
  });

  describe("user assignment", () => {
    const data: ContainerCreateDialogData = { username: "alice", userRealm: "realm1", checkUserAssignment: true };

    it("shows the user assignment if a user is given and the action is allowed", async () => {
      await setup(data, () =>
        authService.actionAllowed.mockImplementation((action: string) => action === "container_assign_user")
      );
      expect(component.showUserAssignment()).toBe(true);
      expect(component.assignUser()).toBe(true);
    });

    it("hides the user assignment if the action is not allowed", async () => {
      await setup(data, () => authService.actionAllowed.mockReturnValue(false));
      expect(component.showUserAssignment()).toBe(false);
    });

    it("assigns the user to the new container when the checkbox is checked", async () => {
      await setup(data, () =>
        authService.actionAllowed.mockImplementation((action: string) => action === "container_assign_user")
      );
      containerService.createContainer.mockReturnValue(of(MockPiResponse.fromValue({ container_serial: "CONT-NEW" })));

      component.onAction("create");

      expect(containerService.createContainer).toHaveBeenCalledWith({
        type: "generic",
        description: "",
        user: "alice",
        realm: "realm1"
      });
    });

    it("does not assign the user when the checkbox is unchecked", async () => {
      await setup(data, () =>
        authService.actionAllowed.mockImplementation((action: string) => action === "container_assign_user")
      );
      containerService.createContainer.mockReturnValue(of(MockPiResponse.fromValue({ container_serial: "CONT-NEW" })));

      component.assignUser.set(false);
      component.onAction("create");

      expect(containerService.createContainer).toHaveBeenCalledWith({
        type: "generic",
        description: ""
      });
    });
  });
});
