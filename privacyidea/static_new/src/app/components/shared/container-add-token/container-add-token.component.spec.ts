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
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatCheckbox, MatCheckboxChange } from "@angular/material/checkbox";
import { AuthServiceInterface } from "@services/auth/auth.service";
import { By } from "@angular/platform-browser";
import { ContainerAddTokenComponent } from "./container-add-token.component";

describe("ContainerAddTokenComponent", () => {
  let fixture: ComponentFixture<ContainerAddTokenComponent>;
  let component: ContainerAddTokenComponent;
  let actionAllowed: jest.Mock;

  const checkbox = () => fixture.debugElement.query(By.directive(MatCheckbox))?.componentInstance as MatCheckbox;
  const hint = () => fixture.nativeElement.querySelector("mat-hint") as HTMLElement | null;

  beforeEach(async () => {
    actionAllowed = jest.fn().mockReturnValue(true);

    await TestBed.configureTestingModule({
      imports: [ContainerAddTokenComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerAddTokenComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("authService", { actionAllowed } as unknown as AuthServiceInterface);
    fixture.componentRef.setInput("showOnlyTokenInContainer", false);
    fixture.componentRef.setInput("total", 0);
    fixture.componentRef.setInput("pageIndex", 0);
    fixture.componentRef.setInput("pageSize", 5);
    fixture.componentRef.setInput("filterValue", "");
    fixture.componentRef.setInput("filterIsNotEmpty", false);
    fixture.componentRef.setInput("tokenOptions", []);
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("renders the positively-phrased checkbox label", () => {
    expect(fixture.nativeElement.textContent).toContain("Include tokens that are in a container");
  });

  it("reflects showOnlyTokenInContainer in the checkbox checked state", () => {
    expect(checkbox().checked).toBe(false);

    fixture.componentRef.setInput("showOnlyTokenInContainer", true);
    fixture.detectChanges();

    expect(checkbox().checked).toBe(true);
  });

  it("writes the checkbox change back to the showOnlyTokenInContainer model", () => {
    checkbox().change.emit({ source: checkbox(), checked: true } as MatCheckboxChange);
    fixture.detectChanges();
    expect(component.showOnlyTokenInContainer()).toBe(true);

    checkbox().change.emit({ source: checkbox(), checked: false } as MatCheckboxChange);
    fixture.detectChanges();
    expect(component.showOnlyTokenInContainer()).toBe(false);
  });

  it("shows the move-token hint only while tokens in a container are included", () => {
    expect(hint()).toBeNull();

    fixture.componentRef.setInput("showOnlyTokenInContainer", true);
    fixture.detectChanges();

    expect(hint()).not.toBeNull();
    expect(hint()?.textContent).toContain("removes it from its previous container");
  });

  it("does not render the panel when container_add_token is not allowed", () => {
    fixture.componentRef.setInput("authService", { actionAllowed: () => false } as unknown as AuthServiceInterface);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.directive(MatCheckbox))).toBeNull();
  });
});
