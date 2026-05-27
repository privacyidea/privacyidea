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

import { Component, EventEmitter, Input, Output } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { EnrollTokenTypeSwitchComponent } from "@components/shared/enroll-token-type-switch/enroll-token-type-switch.component";
import { TemplateAddedTokenRowComponent } from "./template-added-token-row.component";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import type { enrollmentArgsGetterFn } from "@components/token/token-enrollment/token-enrollment.component";

@Component({
  selector: "app-enroll-token-type-switch",
  standalone: true,
  template: ""
})
class MockEnrollTokenTypeSwitchComponent {
  @Input() tokenTypeKey!: string;
  @Input() enrollmentData: TokenEnrollmentData | null = null;
  @Output() enrollmentArgsGetterChange = new EventEmitter<enrollmentArgsGetterFn>();
}

describe("TemplateAddedTokenRowComponent", () => {
  let component: TemplateAddedTokenRowComponent;
  let fixture: ComponentFixture<TemplateAddedTokenRowComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TemplateAddedTokenRowComponent]
    })
      .overrideComponent(TemplateAddedTokenRowComponent, {
        remove: { imports: [EnrollTokenTypeSwitchComponent] },
        add: { imports: [MockEnrollTokenTypeSwitchComponent] }
      })
      .compileComponents();

    fixture = TestBed.createComponent(TemplateAddedTokenRowComponent);
    component = fixture.componentInstance;

    // Set required inputs before any effect/signal runs
    fixture.componentRef.setInput("tokenEnrollmentPayload", { type: "hotp" });
    fixture.componentRef.setInput("index", 0);
  });

  describe("Core Functionality", () => {
    it("should create", () => {
      fixture.detectChanges();
      expect(component).toBeTruthy();
    });

    it("should render the token type switch with the payload type", () => {
      fixture.detectChanges();

      const switchElement = fixture.debugElement.query(By.css("app-enroll-token-type-switch"));
      expect(switchElement).toBeTruthy();
      expect(switchElement.componentInstance.tokenTypeKey).toBe("hotp");
    });

    it("should keep the expansion panel enabled regardless of token type", () => {
      fixture.detectChanges();

      const panel = fixture.debugElement.query(By.css("mat-expansion-panel"));
      expect(panel.componentInstance.disabled).toBe(false);
    });

    it("should expose the token type description", () => {
      fixture.detectChanges();

      expect(component.tokenTypeDescription()).toContain("HOTP");
    });

    it("should emit onRemoveToken when delete button is clicked", () => {
      fixture.componentRef.setInput("index", 5);
      const spy = jest.spyOn(component.onRemoveToken, "emit");
      fixture.detectChanges();

      const deleteBtn = fixture.debugElement.query(By.css("button[mat-icon-button]"));
      deleteBtn.nativeElement.click();

      expect(spy).toHaveBeenCalledWith(5);
    });

    it("emits onEditToken when the enrollmentArgsGetter is registered and returns args", () => {
      const spy = jest.spyOn(component.onEditToken, "emit");
      fixture.detectChanges();

      component.updateEnrollmentArgsGetter((data) => ({
        data: { ...data, testKey: "updatedValue" } as any,
        mapper: { toApiPayload: (d: any) => d } as any
      }));

      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          testKey: "updatedValue"
        })
      );
    });
  });

  describe("Lifecycle & UI Logic", () => {
    it("should stop propagation on delete button click", () => {
      fixture.detectChanges();

      const deleteBtn = fixture.debugElement.query(By.css("button[mat-icon-button]"));
      const clickEvent = new MouseEvent("click", { bubbles: true, cancelable: true });
      const stopSpy = jest.spyOn(clickEvent, "stopPropagation");

      deleteBtn.nativeElement.dispatchEvent(clickEvent);

      expect(stopSpy).toHaveBeenCalled();
    });

    it("should handle invalid index by not emitting remove event", () => {
      fixture.componentRef.setInput("index", -1);
      const spy = jest.spyOn(component.onRemoveToken, "emit");
      fixture.detectChanges();

      component.removeToken();
      expect(spy).not.toHaveBeenCalled();
    });
  });
});
