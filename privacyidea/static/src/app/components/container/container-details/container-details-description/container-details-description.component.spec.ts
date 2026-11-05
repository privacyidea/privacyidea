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
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { MockAuthService, MockContainerService } from "@testing/mock-services";
import { ContainerDetailsDescriptionComponent } from "./container-details-description.component";

describe("ContainerDetailsDescriptionComponent", () => {
  let component: ContainerDetailsDescriptionComponent;
  let fixture: ComponentFixture<ContainerDetailsDescriptionComponent>;
  let containerService: MockContainerService;
  let registry: DetailsEditRegistry;

  const textarea = (): HTMLTextAreaElement | null => fixture.nativeElement.querySelector("textarea");

  /** Clicks a button of the edit buttons; the parent's `blockEditing` follows the registry like in the details. */
  const clickButton = (label: string): void => {
    fixture.nativeElement.querySelector(`button[aria-label="${label}"]`).click();
    fixture.componentRef.setInput("blockEditing", registry.anyEditing());
    fixture.detectChanges();
  };

  const type = (value: string): void => {
    textarea()!.value = value;
    textarea()!.dispatchEvent(new Event("input"));
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsDescriptionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DetailsEditRegistry,
        { provide: ContainerService, useClass: MockContainerService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    registry = TestBed.inject(DetailsEditRegistry);
    (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["container_description"]
    });
    containerService.containerSerial.set("CONT-1");

    fixture = TestBed.createComponent(ContainerDetailsDescriptionComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("description", "old text");
    fixture.detectChanges();
  });

  it("shows the description, or a dash when there is none", () => {
    expect(fixture.nativeElement.querySelector(".description-text").textContent).toContain("old text");

    fixture.componentRef.setInput("description", "");
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector(".description-text").textContent).toContain("-");
  });

  it("shows no edit button without the right to edit the description", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: []
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("app-edit-buttons button")).toBeNull();
  });

  it("opens a textarea with 3 rows that starts from the current description", () => {
    clickButton("Edit");

    expect(textarea()!.getAttribute("rows")).toBe("3");
    expect(textarea()!.value).toBe("old text");
    expect(registry.anyEditing()).toBe(true);
  });

  it("saves the typed text, reloads the container and leaves edit mode", async () => {
    clickButton("Edit");
    type("new text");

    clickButton("Save");
    await fixture.whenStable();
    fixture.detectChanges();

    expect(containerService.setContainerDescription).toHaveBeenCalledWith("CONT-1", "new text");
    expect(containerService.containerDetailsResource.reload).toHaveBeenCalled();
    expect(textarea()).toBeNull();
  });

  it("accepts any length, since the backend limit differs from the token description", () => {
    clickButton("Edit");
    type("x".repeat(500));

    expect(component["descriptionForm"]().valid()).toBe(true);
    expect(component["field"].valid()).toBe(true);
  });

  it("drops the typed text on cancel and starts from the description again", () => {
    clickButton("Edit");
    type("typed");

    clickButton("Cancel");

    expect(containerService.setContainerDescription).not.toHaveBeenCalled();
    expect(textarea()).toBeNull();
    clickButton("Edit");
    expect(textarea()!.value).toBe("old text");
  });

  it("registers its edit handle so save all reaches it", async () => {
    clickButton("Edit");
    type("via registry");

    await registry.saveAll();

    expect(containerService.setContainerDescription).toHaveBeenCalledWith("CONT-1", "via registry");
    expect(registry.anyEditing()).toBe(false);
  });
});
