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
import { DetailsEditRegistry } from "@components/shared/details-shared/details-edit-registry.service";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { NotificationService } from "@services/notification/notification.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import {
  MockAuthService,
  MockContainerService,
  MockNotificationService,
  MockTableUtilsService
} from "@testing/mock-services";
import { ContainerStatesFieldComponent } from "./container-states-field.component";

interface ContainerStatesFieldInternals {
  toggle(): void;
  onStatesChange(newStates: string[]): void;
  commit(): void;
  cancel(): void;
}

describe("ContainerStatesFieldComponent", () => {
  let component: ContainerStatesFieldComponent;
  let fixture: ComponentFixture<ContainerStatesFieldComponent>;
  let containerService: MockContainerService;
  let notificationService: MockNotificationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerStatesFieldComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DetailsEditRegistry,
        { provide: ContainerService, useClass: MockContainerService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerStatesFieldComponent);
    component = fixture.componentInstance;
    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    fixture.componentRef.setInput("states", ["active"]);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("toggle() seeds the selection from the current states when entering edit mode", () => {
    expect(component.isEditing()).toBe(false);

    (component as unknown as ContainerStatesFieldInternals).toggle();

    expect(component.isEditing()).toBe(true);
    expect(component.selectedStates()).toEqual(["active"]);

    (component as unknown as ContainerStatesFieldInternals).toggle();
    expect(component.isEditing()).toBe(false);
  });

  it("onStatesChange() drops the previously selected mutually-exclusive state", () => {
    component.selectedStates.set(["active"]);
    (component as unknown as ContainerStatesFieldInternals).onStatesChange(["active", "disabled"]);
    // "active" was selected before, so it gets removed in favor of "disabled"
    expect(component.selectedStates()).toEqual(["disabled"]);
  });

  it("onStatesChange() keeps the new states when they are not mutually exclusive", () => {
    (component as unknown as ContainerStatesFieldInternals).onStatesChange(["active", "lost"]);
    expect(component.selectedStates()).toEqual(["active", "lost"]);
  });

  it("commit() rejects an empty selection with an error and does not call the service", () => {
    component.selectedStates.set([]);

    (component as unknown as ContainerStatesFieldInternals).commit();

    expect(notificationService.error).toHaveBeenCalledWith("At least one state must be selected.");
    expect(containerService.setStates).not.toHaveBeenCalled();
  });

  it("commit() persists the selection and leaves edit mode", () => {
    component.isEditing.set(true);
    component.selectedStates.set(["disabled"]);

    (component as unknown as ContainerStatesFieldInternals).commit();

    expect(containerService.setStates).toHaveBeenCalledWith(containerService.containerSerial(), ["disabled"]);
    expect(component.isEditing()).toBe(false);
  });

  it("cancel() restores the original states and leaves edit mode", () => {
    component.isEditing.set(true);
    component.selectedStates.set(["disabled"]);

    (component as unknown as ContainerStatesFieldInternals).cancel();

    expect(component.selectedStates()).toEqual(["active"]);
    expect(component.isEditing()).toBe(false);
  });

  it("registers and unregisters its edit handle with the registry", () => {
    const registry = TestBed.inject(DetailsEditRegistry);
    const unregisterSpy = jest.spyOn(registry, "unregister");

    fixture.destroy();

    expect(unregisterSpy).toHaveBeenCalled();
  });
});
