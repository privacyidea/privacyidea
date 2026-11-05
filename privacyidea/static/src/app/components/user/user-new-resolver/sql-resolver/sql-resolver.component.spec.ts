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
import { ComponentRef } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { ResolverService } from "@services/resolver/resolver.service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { SqlResolverComponent } from "./sql-resolver.component";

describe("SqlResolverComponent", () => {
  let component: SqlResolverComponent;
  let componentRef: ComponentRef<SqlResolverComponent>;
  let fixture: ComponentFixture<SqlResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SqlResolverComponent],
      providers: [{ provide: ResolverService, useClass: MockResolverService }]
    }).compileComponents();

    fixture = TestBed.createComponent(SqlResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should expose isValid and getValue", () => {
    expect(typeof component.isValid).toBe("function");
    expect(typeof component.getValue).toBe("function");
  });

  it("should update model when data input changes", () => {
    componentRef.setInput("data", {
      Driver: "mysql",
      Server: "localhost",
      Table: "users",
      Limit: 100,
      Map: "{}"
    });

    fixture.detectChanges();

    expect(component.model().Driver).toBe("mysql");
    expect(component.model().Server).toBe("localhost");
    expect(component.model().Table).toBe("users");
    expect(component.model().Limit).toBe("100");
    expect(component.model().Map).toBe("{}");
  });

  it("should parse boolean and numeric strings from data input", () => {
    componentRef.setInput("data", {
      Editable: "0",
      Port: "3306",
      poolSize: "10"
    });

    fixture.detectChanges();

    expect(component.model().Editable).toBe(false);
    expect(component.model().Port).toBe("3306");
    expect(component.model().poolSize).toBe("10");
  });

  it("should parse '1' and '0' strings as booleans from data input", () => {
    componentRef.setInput("data", {
      Editable: "1"
    });

    fixture.detectChanges();

    expect(component.model().Editable).toBe(true);
  });

  it("should apply SQL presets", () => {
    const preset = component.sqlPresets[0];
    component.applySqlPreset(preset);
    expect(component.model().Table).toBe(preset.table);
    expect(component.model().Map).toBe(preset.map);
    expect(component.model().poolSize).toBe("5");
    expect(component.model().poolTimeout).toBe("10");
    expect(component.model().poolRecycle).toBe("7200");
  });

  describe("password hash type", () => {
    // The keys of hash_type_dict in privacyidea/lib/resolvers/SQLIdResolver.py
    const backendHashTypes = [
      "PHPASS",
      "SHA",
      "SSHA",
      "SSHA256",
      "SSHA512",
      "OTRS",
      "SHA256CRYPT",
      "SHA512CRYPT",
      "MD5CRYPT"
    ];

    const getHashSelect = (): MatSelect => fixture.debugElement.query(By.directive(MatSelect))?.componentInstance;

    beforeEach(() => {
      componentRef.setInput("data", { Editable: "1" });
      fixture.detectChanges();
    });

    it("should not show the hash type select for a resolver that is not editable", () => {
      componentRef.setInput("data", { Editable: "0" });
      fixture.detectChanges();

      expect(getHashSelect()).toBeUndefined();
    });

    it("should offer every hash type the backend supports", () => {
      expect(getHashSelect().options.map((option) => option.value)).toEqual(backendHashTypes);
    });

    it("should store a selected hash type in the model", () => {
      const option = getHashSelect().options.find((o) => o.value === "SHA256CRYPT");
      expect(option).toBeDefined();
      option?.select();
      fixture.detectChanges();

      expect(component.model().Password_Hash_Type).toBe("SHA256CRYPT");
    });

    it("should name every hash type the backend supports in the hint", () => {
      const hint = fixture.debugElement.query(By.css("mat-hint")).nativeElement.textContent;

      for (const hashType of backendHashTypes) {
        expect(hint).toMatch(new RegExp(`\\b${hashType}\\b`));
      }
      // SHA512 alone is no valid hash type, only SSHA512 and SHA512CRYPT are
      expect(hint).not.toMatch(/\bSHA512\b/);
    });
  });

  describe("edits through the controls", () => {
    const flush = async () => {
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };
    const checkboxInput = (): HTMLInputElement =>
      fixture.nativeElement.querySelector("mat-checkbox input") as HTMLInputElement;
    const clearButtonOf = (input: HTMLInputElement) =>
      input.closest("app-clearable-input")!.querySelector("button") as HTMLButtonElement;
    const numberInput = (index: number): HTMLInputElement =>
      fixture.nativeElement.querySelectorAll("input[type='number']")[index];
    const type = async (input: HTMLInputElement, value: string) => {
      input.value = value;
      input.dispatchEvent(new Event("input"));
      input.dispatchEvent(new Event("blur"));
      await flush();
    };
    const filled = { Driver: "mysql", Server: "localhost", Table: "users", Limit: 100, Map: "{}" };

    beforeEach(async () => {
      componentRef.setInput("data", filled);
      await flush();
    });

    it("starts pristine and valid after the data input is applied", () => {
      expect(component.isDirty()).toBe(false);
      expect(component.isValid()).toBe(true);
    });

    it("the Editable checkbox writes the model and marks the resolver dirty", async () => {
      checkboxInput().click();
      await flush();

      expect(component.model().Editable).toBe(true);
      expect(component.sqlForm.Editable().dirty()).toBe(true);
      expect(component.isDirty()).toBe(true);
    });

    it("the hash type select writes the model and marks the resolver dirty", async () => {
      componentRef.setInput("data", { ...filled, Editable: "1" });
      await flush();
      expect(component.isDirty()).toBe(false);

      const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
      select.options.find((o) => o.value === "SSHA")!.select();
      await flush();

      expect(component.model().Password_Hash_Type).toBe("SSHA");
      expect(component.sqlForm.Password_Hash_Type().dirty()).toBe(true);
      expect(component.isDirty()).toBe(true);
    });

    it("shows a model change in the checkbox without marking the resolver dirty", async () => {
      component.model.update((m) => ({ ...m, Editable: true }));
      await flush();

      expect(checkboxInput().checked).toBe(true);
      expect(component.isDirty()).toBe(false);
    });

    it("marks the resolver dirty when a clear button empties a field", async () => {
      const driver = fixture.nativeElement.querySelector("input.mat-mdc-input-element") as HTMLInputElement;

      clearButtonOf(driver).click();
      await flush();

      expect(component.model().Driver).toBe("");
      expect(component.sqlForm.Driver().dirty()).toBe(true);
      expect(component.isDirty()).toBe(true);
      expect(component.isValid()).toBe(false);
    });

    it("marks the resolver dirty when a preset is applied", () => {
      component.applySqlPreset(component.sqlPresets[0]);

      expect(component.isDirty()).toBe(true);
    });

    it("requires the limit and shows the message once it is emptied", async () => {
      await type(numberInput(0), "");

      expect(component.model().Limit).toBe("");
      expect(
        component.sqlForm
          .Limit()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["required"]);
      expect(component.isValid()).toBe(false);
      expect(numberInput(0).closest("mat-form-field")!.querySelector("mat-error")?.textContent).toContain("required");
    });

    it.each([
      [0, "Limit"],
      [1, "poolSize"],
      [2, "poolTimeout"],
      [3, "poolRecycle"]
    ] as const)(
      "number input %s (%s) shows a parse message for text the browser cannot parse",
      async (index, field) => {
        jest.spyOn(numberInput(index), "validity", "get").mockReturnValue({ badInput: true } as ValidityState);
        await type(numberInput(index), "");

        expect(
          component.sqlForm[field]()
            .errors()
            .map((e) => e.kind)
        ).toContain("parse");
        expect(component.isValid()).toBe(false);
        expect(numberInput(index).closest("mat-form-field")!.querySelector("mat-error")?.textContent).toContain(
          "valid number"
        );
      }
    );

    it("accepts an emptied pool size", async () => {
      await type(numberInput(1), "");

      expect(component.model().poolSize).toBe("");
      expect(component.isValid()).toBe(true);
    });
  });
});
