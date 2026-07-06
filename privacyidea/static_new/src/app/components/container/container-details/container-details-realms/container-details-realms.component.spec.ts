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
import { RealmService } from "@services/realm/realm.service";
import { MockAuthService, MockContainerService, MockRealmService } from "@testing/mock-services";
import { ContainerDetailsRealmsComponent } from "./container-details-realms.component";

interface ContainerRealmsFieldInternals {
  toggle(): void;
  commit(): void;
  cancel(): void;
}

describe("ContainerDetailsRealmsComponent", () => {
  let component: ContainerDetailsRealmsComponent;
  let fixture: ComponentFixture<ContainerDetailsRealmsComponent>;
  let containerService: MockContainerService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsRealmsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DetailsEditRegistry,
        { provide: ContainerService, useClass: MockContainerService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsRealmsComponent);
    component = fixture.componentInstance;
    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    fixture.componentRef.setInput("realms", ["realm1"]);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("toggle() seeds the selection from the current realms when entering edit mode", () => {
    (component as unknown as ContainerRealmsFieldInternals).toggle();

    expect(component.isEditing()).toBe(true);
    expect(component.selectedRealms()).toEqual(["realm1"]);

    (component as unknown as ContainerRealmsFieldInternals).toggle();
    expect(component.isEditing()).toBe(false);
  });

  it("commit() persists the selected realms and leaves edit mode", () => {
    component.isEditing.set(true);
    component.selectedRealms.set(["realm2"]);

    (component as unknown as ContainerRealmsFieldInternals).commit();

    expect(containerService.setContainerRealm).toHaveBeenCalledWith(containerService.containerSerial(), ["realm2"]);
    expect(component.isEditing()).toBe(false);
  });

  it("cancel() restores the original realms and leaves edit mode", () => {
    component.isEditing.set(true);
    component.selectedRealms.set(["realm2"]);

    (component as unknown as ContainerRealmsFieldInternals).cancel();

    expect(component.selectedRealms()).toEqual(["realm1"]);
    expect(component.isEditing()).toBe(false);
  });

  it("registers and unregisters its edit handle with the registry", () => {
    const registry = TestBed.inject(DetailsEditRegistry);
    const unregisterSpy = jest.spyOn(registry, "unregister");

    fixture.destroy();

    expect(unregisterSpy).toHaveBeenCalled();
  });
});
