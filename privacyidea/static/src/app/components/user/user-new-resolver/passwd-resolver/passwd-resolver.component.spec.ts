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
import { PasswdResolverComponent } from "./passwd-resolver.component";

describe("PasswdResolverComponent", () => {
  let component: PasswdResolverComponent;
  let componentRef: ComponentRef<PasswdResolverComponent>;
  let fixture: ComponentFixture<PasswdResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PasswdResolverComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(PasswdResolverComponent);
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
      fileName: "/etc/passwd"
    });

    fixture.detectChanges();

    expect(component.model().fileName).toBe("/etc/passwd");
  });

  it("should also accept all filename variable, but prioritise fileName", () => {
    componentRef.setInput("data", {
      filename: "/etc/filename-passwd"
    });
    fixture.detectChanges();

    expect(component.model().fileName).toBe("/etc/filename-passwd");

    componentRef.setInput("data", {
      filename: "/etc/filename-passwd",
      fileName: "/etc/passwd"
    });
    fixture.detectChanges();

    expect(component.model().fileName).toBe("/etc/passwd");
  });

  describe("edits through the controls", () => {
    const flush = async () => {
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };
    const fileInput = (): HTMLInputElement => fixture.nativeElement.querySelector("input") as HTMLInputElement;

    beforeEach(async () => {
      componentRef.setInput("data", { fileName: "/etc/passwd" });
      await flush();
    });

    it("starts pristine and valid after the data input is applied", () => {
      expect(component.isDirty()).toBe(false);
      expect(component.isValid()).toBe(true);
    });

    it("marks the resolver dirty when the clear button empties the file name", async () => {
      (fixture.nativeElement.querySelector("app-clearable-input button") as HTMLButtonElement).click();
      await flush();

      expect(component.model().fileName).toBe("");
      expect(component.passwdForm.fileName().dirty()).toBe(true);
      expect(component.isDirty()).toBe(true);
      expect(component.isValid()).toBe(false);
    });

    it("shows the required message once the emptied file name is touched", async () => {
      fileInput().value = "";
      fileInput().dispatchEvent(new Event("input"));
      fileInput().dispatchEvent(new Event("blur"));
      await flush();

      expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("required");
    });
  });
});
