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
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { of } from "rxjs";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { MockContainerService, MockLocalService, MockNotificationService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { ContainerDetailsInfoComponent, ContainerInfoDetail } from "./container-details-info.component";

describe("ContainerDetailsInfoComponent", () => {
  let fixture: ComponentFixture<ContainerDetailsInfoComponent>;
  let component: ContainerDetailsInfoComponent;
  let containerService: MockContainerService;

  const makeInfoEl = (value: Record<string, string>): ContainerInfoDetail<Record<string, string>> => ({
    keyMap: { label: "Info", key: "info" },
    isEditing: signal(false),
    value
  });

  const makeOtherEl = (key: string, value: unknown): ContainerInfoDetail => ({
    keyMap: { label: key, key },
    isEditing: signal(false),
    value
  });

  beforeEach(async () => {
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [ContainerDetailsInfoComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerService, useClass: MockContainerService },
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;

    fixture = TestBed.createComponent(ContainerDetailsInfoComponent);
    component = fixture.componentInstance;

    const infoArr: ContainerInfoDetail<Record<string, string>>[] = [makeInfoEl({ a: "1" })];
    const detailArr: ContainerInfoDetail[] = [makeOtherEl("info", {})];

    fixture.componentRef.setInput("infoData", infoArr as unknown as ContainerInfoDetail[]);
    fixture.componentRef.setInput("detailData", detailArr as unknown as ContainerInfoDetail[]);
    fixture.componentRef.setInput("isAnyEditingOrRevoked", false);
    fixture.componentRef.setInput("isEditingInfo", false);
    fixture.componentRef.setInput("isEditingUser", false);

    containerService.containerSerial.set("CONT-7");

    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("saveInfo adds key/value if provided, calls setContainerInfos, resets newInfo, turns off edit, and reloads", () => {
    const el = component.infoData()[0] as ContainerInfoDetail<Record<string, string>>;
    expect(el.value).toEqual({ a: "1" });

    component.isEditingInfo.set(true);
    component.newInfo.set({ key: "b", value: "2" });

    (containerService.setContainerInfos as jest.Mock).mockReturnValue(of({}));

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1", b: "2" });
    expect(containerService.setContainerInfos).toHaveBeenCalledWith("CONT-7", { a: "1", b: "2" });
    expect(component.newInfo()).toEqual({ key: "", value: "" });
    expect(component.isEditingInfo()).toBe(false);
    expect(containerService.containerDetailsResource.reload).toHaveBeenCalledTimes(1);
  });

  it("saveInfo without new pair still calls setContainerInfos and reloads", () => {
    const el = component.infoData()[0] as ContainerInfoDetail<Record<string, string>>;
    component.isEditingInfo.set(true);
    component.newInfo.set({ key: "", value: "" });

    (containerService.setContainerInfos as jest.Mock).mockReturnValue(of({}));

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1" });
    expect(containerService.setContainerInfos).toHaveBeenCalledWith("CONT-7", { a: "1" });
    expect(component.isEditingInfo()).toBe(false);
    expect(containerService.containerDetailsResource.reload).toHaveBeenCalledTimes(1);
  });

  it("deleteInfo calls service, marks info section as editing, and reloads", () => {
    component.isEditingInfo.set(false);

    component.deleteInfo("a");

    expect(containerService.deleteInfo).toHaveBeenCalledWith("CONT-7", "a");
    expect(component.isEditingInfo()).toBe(true);
    expect(containerService.containerDetailsResource.reload).toHaveBeenCalledTimes(1);
  });

  describe("the 'add' row", () => {
    const field = (selector: string): HTMLInputElement =>
      fixture.nativeElement.querySelector(`.info-add-row ${selector}`);

    const type = (selector: string, value: string): void => {
      const el = field(selector);
      el.value = value;
      el.dispatchEvent(new Event("input"));
      fixture.detectChanges();
    };

    const kinds = (name: "key" | "value"): string[] => {
      const field = component["newInfoForm"][name];
      return field()
        .errors()
        .map((error) => error.kind);
    };

    const setRights = (): void => {
      (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
        ...MockAuthService.MOCK_AUTH_DATA,
        rights: ["container_info"]
      });
    };

    const startEditing = (): void => {
      fixture.componentRef.setInput("isEditingInfo", true);
      fixture.detectChanges();
    };

    it("takes typed text into the model", () => {
      startEditing();

      type("input", "b");
      type("textarea", "2");

      expect(component.newInfo()).toEqual({ key: "b", value: "2" });
    });

    it("accepts an empty row", () => {
      startEditing();

      expect(component.canSave()).toBe(true);
    });

    it("requires a value once a key is typed and a key once a value is typed", () => {
      startEditing();

      type("input", "b");
      expect(kinds("value")).toEqual(["required"]);
      expect(component.canSave()).toBe(false);

      type("input", "");
      type("textarea", "2");
      expect(kinds("key")).toEqual(["required"]);
      expect(component.canSave()).toBe(false);
    });

    it("rejects a key the info already holds", () => {
      startEditing();

      type("input", " a ");
      type("textarea", "2");

      expect(kinds("key")).toEqual(["keyExists"]);
      expect(component.canSave()).toBe(false);
    });

    it("shows the errors once the inputs were left", () => {
      startEditing();
      type("input", "a");
      type("textarea", "");
      field("input").dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector(".info-add-row mat-error").textContent).toContain("already exists");

      type("input", "b");
      field("textarea").dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector(".info-add-row mat-error").textContent).toContain("Enter a value");

      type("input", "");
      type("textarea", "2");
      field("input").dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector(".info-add-row mat-error").textContent).toContain("Enter a key");
    });

    it("disables Save while the row is incomplete", () => {
      setRights();
      fixture.componentRef.setInput("isAnyEditingOrRevoked", true);
      startEditing();
      const save = (): HTMLButtonElement => fixture.nativeElement.querySelector('button[aria-label="Save"]');

      expect(save().disabled).toBe(false);

      type("input", "b");
      expect(save().disabled).toBe(true);

      type("textarea", "2");
      expect(save().disabled).toBe(false);
    });

    it("saveInfo sends nothing and touches both inputs while the row is invalid", () => {
      startEditing();
      type("input", "b");
      const el = component.infoData()[0] as ContainerInfoDetail<Record<string, string>>;

      component.saveInfo(el);

      expect(containerService.setContainerInfos).not.toHaveBeenCalled();
      expect(component["newInfoForm"].key().touched()).toBe(true);
      expect(component["newInfoForm"].value().touched()).toBe(true);
      expect(component.isEditingInfo()).toBe(true);
    });

    it("saveInfo stores the key trimmed", () => {
      startEditing();
      type("input", " b ");
      type("textarea", "2");
      const el = component.infoData()[0] as ContainerInfoDetail<Record<string, string>>;
      (containerService.setContainerInfos as jest.Mock).mockReturnValue(of({}));

      component.saveInfo(el);

      expect(containerService.setContainerInfos).toHaveBeenCalledWith("CONT-7", { a: "1", b: "2" });
    });

    it("clears the row when editing is toggled off", () => {
      startEditing();
      type("input", "b");
      type("textarea", "2");

      component.toggleInfoEdit();

      expect(component.newInfo()).toEqual({ key: "", value: "" });
      expect(component["newInfoForm"]().dirty()).toBe(false);
    });

    it("canSave is true outside of editing even if the row holds text", () => {
      component.newInfo.set({ key: "b", value: "" });

      expect(component.canSave()).toBe(true);
    });
  });
});
