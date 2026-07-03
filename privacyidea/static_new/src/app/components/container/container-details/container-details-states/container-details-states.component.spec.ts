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
import { DetailsEditRegistry } from "@components/shared/details-shared/field-editing/details-edit-registry.service";
import { EditableField } from "@components/shared/details-shared/field-editing/editable-field";
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
import { ContainerDetailsStatesComponent } from "./container-details-states.component";

interface ContainerStatesFieldInternals {
  field: EditableField;
  onStatesChange(newStates: string[]): void;
}

describe("ContainerDetailsStatesComponent", () => {
  let component: ContainerDetailsStatesComponent;
  let internals: ContainerStatesFieldInternals;
  let fixture: ComponentFixture<ContainerDetailsStatesComponent>;
  let containerService: MockContainerService;
  let notificationService: MockNotificationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsStatesComponent],
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

    fixture = TestBed.createComponent(ContainerDetailsStatesComponent);
    component = fixture.componentInstance;
    internals = component as unknown as ContainerStatesFieldInternals;
    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    fixture.componentRef.setInput("states", ["active"]);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("toggle() seeds the selection from the current states when entering edit mode", () => {
    expect(internals.field.isEditing()).toBe(false);

    internals.field.toggle();

    expect(internals.field.isEditing()).toBe(true);
    expect(component.selectedStates()).toEqual(["active"]);

    internals.field.toggle();
    expect(internals.field.isEditing()).toBe(false);
  });

  it("onStatesChange() drops the previously selected mutually-exclusive state", () => {
    component.selectedStates.set(["active"]);
    internals.onStatesChange(["active", "disabled"]);
    // "active" was selected before, so it gets removed in favor of "disabled"
    expect(component.selectedStates()).toEqual(["disabled"]);
  });

  it("onStatesChange() keeps the new states when they are not mutually exclusive", () => {
    internals.onStatesChange(["active", "lost"]);
    expect(component.selectedStates()).toEqual(["active", "lost"]);
  });

  it("commit() rejects an empty selection with an error and does not call the service", () => {
    component.selectedStates.set([]);

    internals.field.commit();

    expect(notificationService.error).toHaveBeenCalledWith("At least one state must be selected.");
    expect(containerService.setStates).not.toHaveBeenCalled();
  });

  it("commit() persists the selection and leaves edit mode", () => {
    internals.field.toggle();
    component.selectedStates.set(["disabled"]);

    internals.field.commit();

    expect(containerService.setStates).toHaveBeenCalledWith(containerService.containerSerial(), ["disabled"]);
    expect(internals.field.isEditing()).toBe(false);
  });

  it("cancel() restores the original states and leaves edit mode", () => {
    internals.field.toggle();
    component.selectedStates.set(["disabled"]);

    internals.field.cancel();

    expect(component.selectedStates()).toEqual(["active"]);
    expect(internals.field.isEditing()).toBe(false);
  });

  it("registers and unregisters its edit handle with the registry", () => {
    const registry = TestBed.inject(DetailsEditRegistry);
    const unregisterSpy = jest.spyOn(registry, "unregister");

    fixture.destroy();

    expect(unregisterSpy).toHaveBeenCalled();
  });
});
