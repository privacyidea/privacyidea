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
import { EditableElement } from "@components/shared/edit-buttons/edit-buttons.component";
import { TokenService } from "@services/token/token.service";
import { MockTokenService } from "@testing/mock-services";
import { TokenDetailsDescriptionComponent } from "./token-details-description.component";

describe("TokenDetailsDescriptionComponent", () => {
  let component: TokenDetailsDescriptionComponent;
  let fixture: ComponentFixture<TokenDetailsDescriptionComponent>;

  const element = (): EditableElement<string> => ({
    keyMap: { key: "description" },
    value: "some description",
    isEditing: signal(false)
  });

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsDescriptionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsDescriptionComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("element", element());
    fixture.componentRef.setInput("editable", true);
    fixture.componentRef.setInput("cancelEdit", () => undefined);
    fixture.componentRef.setInput("saveEdit", () => undefined);
    fixture.componentRef.setInput("toggleEdit", () => undefined);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("renders the admin description editor with 7 rows", () => {
    const el = element();
    el.isEditing.set(true);
    fixture.componentRef.setInput("element", el);
    fixture.detectChanges();

    const textarea = fixture.nativeElement.querySelector(".details-card--description textarea");
    expect(textarea).toBeTruthy();
    expect(textarea.getAttribute("rows")).toBe("7");
  });

  it("renders the self-service description editor with 4 rows", () => {
    const el = element();
    el.isEditing.set(true);
    fixture.componentRef.setInput("element", el);
    fixture.componentRef.setInput("selfService", true);
    fixture.detectChanges();

    const textarea = fixture.nativeElement.querySelector(".details-card--description textarea");
    expect(textarea.getAttribute("rows")).toBe("4");
  });
});
