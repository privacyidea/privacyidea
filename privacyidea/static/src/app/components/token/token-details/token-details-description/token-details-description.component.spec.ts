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
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { DetailsEditRegistry } from "@components/shared/details-shared/field-editing/details-edit-registry.service";
import { EditableElement } from "@components/shared/edit-buttons/edit-buttons.component";
import { TokenService } from "@services/token/token.service";
import { MockTokenService } from "@testing/mock-services";
import { TokenDetailsDescriptionComponent } from "./token-details-description.component";

describe("TokenDetailsDescriptionComponent", () => {
  let component: TokenDetailsDescriptionComponent;
  let fixture: ComponentFixture<TokenDetailsDescriptionComponent>;
  let tokenService: MockTokenService;
  let registry: DetailsEditRegistry;

  const element = (): EditableElement<string> => ({
    keyMap: { key: "description" },
    value: "some description",
    isEditing: signal(false)
  });

  const textarea = (): HTMLTextAreaElement | null =>
    fixture.nativeElement.querySelector(".details-card--description textarea");

  /** Clicks a button of the edit buttons; the parent's `isAnyEditingOrRevoked` follows the registry like in the details. */
  const clickButton = (label: string): void => {
    fixture.nativeElement.querySelector(`button[aria-label="${label}"]`).click();
    fixture.componentRef.setInput("isAnyEditingOrRevoked", registry.anyEditing());
    fixture.detectChanges();
  };

  const type = (value: string): void => {
    const input = textarea()!;
    input.value = value;
    input.dispatchEvent(new Event("input"));
    fixture.detectChanges();
  };

  const create = (selfService: boolean): void => {
    fixture = TestBed.createComponent(TokenDetailsDescriptionComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("element", element());
    fixture.componentRef.setInput("editable", true);
    fixture.componentRef.setInput("selfService", selfService);
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsDescriptionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DetailsEditRegistry,
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    registry = TestBed.inject(DetailsEditRegistry);
    tokenService.tokenSerial.set("Mock serial");
  });

  it("should create", () => {
    create(false);
    expect(component).toBeTruthy();
    expect(textarea()).toBeNull();
  });

  it.each([false, true])("renders the description editor with 3 rows (selfService=%s)", (selfService) => {
    create(selfService);
    clickButton("Edit");

    expect(textarea()).toBeTruthy();
    expect(textarea()!.getAttribute("rows")).toBe("3");
    expect(textarea()!.value).toBe("some description");
  });

  it("shows the number of typed characters", () => {
    create(false);
    clickButton("Edit");
    type("abcd");

    expect(fixture.nativeElement.querySelector("mat-hint").textContent).toContain(
      `4 / ${tokenService.maxDescriptionLength}`
    );
  });

  it("saves the typed text, reloads the token and leaves edit mode", async () => {
    create(false);
    clickButton("Edit");
    type("new description");
    const reload = tokenService.tokenDetailResource.reload as jest.Mock;
    reload.mockClear();

    clickButton("Save");
    await fixture.whenStable();
    fixture.detectChanges();

    expect(tokenService.saveTokenDetail).toHaveBeenCalledWith("Mock serial", "description", "new description");
    expect(reload).toHaveBeenCalled();
    expect(textarea()).toBeNull();
  });

  it("leaves the shown description untouched while typing and after cancelling", () => {
    create(false);
    const el = component.element();
    clickButton("Edit");
    type("typed");

    expect(el.value).toBe("some description");

    clickButton("Cancel");

    expect(el.value).toBe("some description");
    expect(tokenService.saveTokenDetail).not.toHaveBeenCalled();
    clickButton("Edit");
    expect(textarea()!.value).toBe("some description");
  });

  it("starts from an empty text when the token has no description", () => {
    create(false);
    fixture.componentRef.setInput("element", { ...element(), value: undefined });
    clickButton("Edit");

    expect(textarea()!.value).toBe("");
  });

  it.each([false, true])(
    "blocks a text over the limit, shows the error and disables Save (selfService=%s)",
    (selfService) => {
      create(selfService);
      clickButton("Edit");
      type("x".repeat(tokenService.maxDescriptionLength + 1));
      const textareaEl = textarea()!;
      textareaEl.dispatchEvent(new Event("blur"));
      fixture.detectChanges();

      expect(
        component["descriptionForm"]()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["maxLength"]);
      expect(component["field"].valid()).toBe(false);
      expect(fixture.nativeElement.querySelector("mat-error").textContent).toContain(
        `${tokenService.maxDescriptionLength} characters`
      );
      expect((fixture.nativeElement.querySelector('button[aria-label="Save"]') as HTMLButtonElement).disabled).toBe(
        true
      );
      expect(registry.anyInvalid()).toBe(true);
    }
  );

  it("touches the field and does not save when committing an invalid text", async () => {
    create(false);
    clickButton("Edit");
    type("x".repeat(tokenService.maxDescriptionLength + 1));

    await component["field"].commit();

    expect(component["descriptionForm"]().touched()).toBe(true);
    expect(tokenService.saveTokenDetail).not.toHaveBeenCalled();
    expect(component["field"].isEditing()).toBe(true);
  });

  it("accepts a text of exactly the limit", () => {
    create(false);
    clickButton("Edit");
    type("x".repeat(tokenService.maxDescriptionLength));

    expect(component["field"].valid()).toBe(true);
    expect(registry.anyInvalid()).toBe(false);
  });

  it("registers its edit handle so save all and cancel all reach it", async () => {
    create(false);
    clickButton("Edit");
    type("via registry");

    expect(registry.anyEditing()).toBe(true);
    await registry.saveAll();

    expect(tokenService.saveTokenDetail).toHaveBeenCalledWith("Mock serial", "description", "via registry");
    expect(registry.anyEditing()).toBe(false);
  });
});
