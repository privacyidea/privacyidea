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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerTemplateAddTokenComponent } from "./container-template-add-token.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideHttpClient } from "@angular/common/http";
import { By } from "@angular/platform-browser";

describe("ContainerTemplateAddTokenComponent", () => {
  let component: ContainerTemplateAddTokenComponent;
  let fixture: ComponentFixture<ContainerTemplateAddTokenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateAddTokenComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateAddTokenComponent);
    component = fixture.componentInstance;

    // Set required inputs before first detectChanges
    fixture.componentRef.setInput("tokenTypes", ["totp", "hotp", "webauthn"]);

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render a chip for each token type", () => {
    const chips = fixture.debugElement.queryAll(By.css("mat-chip"));
    expect(chips.length).toBe(3);
    expect(chips[0].nativeElement.textContent).toContain("Totp");
    expect(chips[1].nativeElement.textContent).toContain("Hotp");
    expect(chips[2].nativeElement.textContent).toContain("Webauthn");
  });

  it("should emit onAddToken when addToken is called directly", () => {
    const spy = jest.spyOn(component.onAddToken, "emit");
    const tokenType = "totp";

    component.addToken(tokenType);

    expect(spy).toHaveBeenCalledWith(tokenType);
  });

  it("should emit onAddToken when a chip is clicked", () => {
    const spy = jest.spyOn(component.onAddToken, "emit");
    const firstChip = fixture.debugElement.query(By.css("mat-chip")).nativeElement;

    firstChip.click();

    expect(spy).toHaveBeenCalledWith("totp");
  });

  it("should update rendered chips when tokenTypes input changes", () => {
    fixture.componentRef.setInput("tokenTypes", ["yubikey"]);
    fixture.detectChanges();

    const chips = fixture.debugElement.queryAll(By.css("mat-chip"));
    expect(chips.length).toBe(1);
    expect(chips[0].nativeElement.textContent).toContain("Yubikey");
  });
});
