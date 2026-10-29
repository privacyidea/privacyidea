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
import { WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { UserService } from "@services/user/user.service";
import { MockUserService } from "@testing/mock-services";
import { CustomAttributeDraft } from "./custom-attribute-draft";
import { UserCustomAttributesComponent } from "./user-custom-attributes.component";

describe("UserCustomAttributesComponent", () => {
  let fixture: ComponentFixture<UserCustomAttributesComponent>;
  let userServiceMock: MockUserService;
  let draft: CustomAttributeDraft;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserCustomAttributesComponent],
      providers: [{ provide: UserService, useClass: MockUserService }]
    }).compileComponents();

    userServiceMock = TestBed.inject(UserService) as unknown as MockUserService;
    draft = TestBed.runInInjectionContext(() => new CustomAttributeDraft());
    fixture = TestBed.createComponent(UserCustomAttributesComponent);
    fixture.componentRef.setInput("draft", draft);
  });

  describe("editing a stored attribute", () => {
    const editButtons = () =>
      fixture.nativeElement.querySelectorAll(
        "button[aria-label='Edit custom attribute']"
      ) as NodeListOf<HTMLButtonElement>;

    beforeEach(() => {
      userServiceMock.userAttributesList.set([
        { key: "department", value: "sales" },
        { key: "legacy-key", value: "1233" }
      ]);
    });

    it("offers editing only for keys the policy allows to set", () => {
      (userServiceMock.attributeSetMap as WritableSignal<Record<string, string[]>>).set({
        department: ["sales", "finance"]
      });
      (userServiceMock.keyOptions as WritableSignal<string[]>).set(["department"]);
      fixture.detectChanges();

      expect(editButtons().length).toBe(1);
    });

    it("edits the value of a fixed key in its own row with the values the policy allows", () => {
      (userServiceMock.attributeSetMap as WritableSignal<Record<string, string[]>>).set({
        department: ["sales", "finance"]
      });
      (userServiceMock.keyOptions as WritableSignal<string[]>).set(["department"]);
      fixture.detectChanges();

      editButtons()[0].click();
      fixture.detectChanges();

      expect(draft.editingKey()).toBe("department");
      expect(draft.editValue()).toBe("sales");
      expect(draft.editValueOptions()).toEqual(["sales", "finance"]);
      expect(draft.addKeyInput()).toBe("");
      expect(draft.selectedKey()).toBeNull();
      expect(editButtons().length).toBe(0);
    });

    it("saves the edited value under the same key and closes the row", async () => {
      (userServiceMock.hasWildcardKey as WritableSignal<boolean>).set(true);
      (userServiceMock.attributeSetMap as WritableSignal<Record<string, string[]>>).set({ "*": ["*"] });
      fixture.detectChanges();

      expect(editButtons().length).toBe(2);
      editButtons()[1].click();
      fixture.detectChanges();

      const rowInput = fixture.nativeElement.querySelector(
        "app-detail-field-row input"
      ) as HTMLInputElement;
      expect(rowInput.value).toBe("1233");
      rowInput.value = "4567";
      rowInput.dispatchEvent(new Event("input"));
      fixture.detectChanges();

      const rowSave = fixture.nativeElement.querySelector(
        "app-detail-field-row button[aria-label='Save']"
      ) as HTMLButtonElement;
      rowSave.click();
      await fixture.whenStable();

      expect(userServiceMock.setUserAttribute).toHaveBeenCalledWith("legacy-key", "4567");
      expect(draft.editingKey()).toBeNull();
    });

    it("cancelling the row edit keeps the stored value", () => {
      (userServiceMock.hasWildcardKey as WritableSignal<boolean>).set(true);
      (userServiceMock.attributeSetMap as WritableSignal<Record<string, string[]>>).set({ "*": ["*"] });
      fixture.detectChanges();
      editButtons()[0].click();
      fixture.detectChanges();

      (
        fixture.nativeElement.querySelector("app-detail-field-row button[aria-label='Cancel']") as HTMLButtonElement
      ).click();
      fixture.detectChanges();

      expect(draft.editingKey()).toBeNull();
      expect(userServiceMock.setUserAttribute).not.toHaveBeenCalled();
      expect(fixture.nativeElement.textContent).toContain("sales");
    });
  });

  it("renders nothing without a settable key and without stored attributes", () => {
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector("app-details-card")).toBeNull();
  });

  const addButton = () =>
    Array.from(fixture.nativeElement.querySelectorAll("button") as NodeListOf<HTMLButtonElement>).find((b) =>
      b.textContent?.includes("Add Attribute")
    );

  it("shows the empty row for a new attribute only after the add button was clicked", () => {
    (userServiceMock.hasWildcardKey as WritableSignal<boolean>).set(true);
    (userServiceMock.attributeSetMap as WritableSignal<Record<string, string[]>>).set({ "*": ["*"] });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector(".new-attribute-row")).toBeNull();

    addButton()!.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector(".new-attribute-row")).not.toBeNull();
    expect(addButton()).toBeUndefined();

    (fixture.nativeElement.querySelector(".new-attribute-row button[aria-label='Cancel']") as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector(".new-attribute-row")).toBeNull();
    expect(addButton()).toBeDefined();
  });

  it("offers no add button without a settable key", () => {
    userServiceMock.userAttributesList.set([{ key: "department", value: "sales" }]);
    fixture.detectChanges();
    expect(addButton()).toBeUndefined();
  });

  it("offers an empty top row with a free-text key and value for a wildcard policy and saves it", async () => {
    (userServiceMock.hasWildcardKey as WritableSignal<boolean>).set(true);
    (userServiceMock.attributeSetMap as WritableSignal<Record<string, string[]>>).set({ "*": ["*"] });
    fixture.detectChanges();
    addButton()!.click();
    fixture.detectChanges();

    const inputs = fixture.nativeElement.querySelectorAll(".new-attribute-row input") as NodeListOf<HTMLInputElement>;
    expect(inputs.length).toBe(2);
    inputs[0].value = "city";
    inputs[0].dispatchEvent(new Event("input"));
    inputs[1].value = "Berlin";
    inputs[1].dispatchEvent(new Event("input"));
    fixture.detectChanges();

    const saveButton = fixture.nativeElement.querySelector(
      ".new-attribute-row button[aria-label='Save']"
    ) as HTMLButtonElement;
    expect(saveButton.disabled).toBe(false);
    saveButton.click();
    await fixture.whenStable();

    expect(userServiceMock.setUserAttribute).toHaveBeenCalledWith("city", "Berlin");
    expect(draft.addKeyInput()).toBe("");
    expect(draft.isAdding()).toBe(false);
  });
});
